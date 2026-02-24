"""
Pipeline Scheduler Service.

Background service that checks for scheduled pipelines and triggers them
when their schedule indicates they should run.

Usage:
    python -m backend.services.scheduler
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
import signal
import sys

from sqlalchemy.orm import Session

from backend.database import get_db_session
from backend.models.pipeline import Pipeline, PipelineRun
from backend.utils.cron_utils import calculate_next_run, CronValidationError
from backend.prefect_flows.pipeline_flow import execute_pipeline_flow

logger = logging.getLogger(__name__)


class PipelineScheduler:
    """
    Pipeline scheduler that runs scheduled pipelines.

    Features:
    - Checks for due pipelines every minute
    - Triggers pipeline runs via Prefect
    - Updates next run times
    - Handles timezone conversions
    - Graceful shutdown support
    """

    def __init__(self, check_interval_seconds: int = 60):
        """
        Initialize scheduler.

        Args:
            check_interval_seconds: How often to check for due pipelines (default: 60)
        """
        self.check_interval = check_interval_seconds
        self.running = False
        self.db: Optional[Session] = None

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)

    def start(self):
        """Start the scheduler."""
        logger.info("Starting pipeline scheduler...")
        logger.info(f"Check interval: {self.check_interval} seconds")

        self.running = True
        self.db = get_db_session()

        try:
            while self.running:
                try:
                    self._check_and_run_due_pipelines()
                except Exception as e:
                    logger.error(f"Error in scheduler loop: {str(e)}", exc_info=True)

                # Sleep for the check interval
                time.sleep(self.check_interval)

        finally:
            if self.db:
                self.db.close()
                logger.info("Database connection closed")

    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping pipeline scheduler...")
        self.running = False

    def _check_and_run_due_pipelines(self):
        """Check for pipelines that are due to run and trigger them."""
        logger.debug("Checking for due pipelines...")

        # Get current time
        now = datetime.now(timezone.utc)

        # Find pipelines that are:
        # 1. Active
        # 2. Have scheduling enabled
        # 3. Have a valid schedule
        # 4. Next run time is in the past or within the next minute
        try:
            due_pipelines = (
                self.db.query(Pipeline)
                .filter(
                    Pipeline.is_active,
                    Pipeline.schedule_enabled,
                    Pipeline.schedule.isnot(None),
                    Pipeline.next_scheduled_run <= now + timedelta(minutes=1)
                )
                .all()
            )

            if due_pipelines:
                logger.info(f"Found {len(due_pipelines)} due pipeline(s)")

                for pipeline in due_pipelines:
                    try:
                        self._run_pipeline(pipeline, now)
                    except Exception as e:
                        logger.error(
                            f"Failed to run pipeline {pipeline.id} ({pipeline.name}): {str(e)}",
                            exc_info=True
                        )

            else:
                logger.debug("No due pipelines found")

        except Exception as e:
            logger.error(f"Error querying for due pipelines: {str(e)}", exc_info=True)

    def _run_pipeline(self, pipeline: Pipeline, current_time: datetime):
        """
        Run a scheduled pipeline.

        Args:
            pipeline: Pipeline to run
            current_time: Current time (UTC)
        """
        logger.info(f"Running scheduled pipeline: {pipeline.name} (ID: {pipeline.id})")

        # Check if organization can sync data
        if pipeline.organization and not pipeline.organization.can_sync_data:
            logger.warning(
                f"Skipping pipeline {pipeline.id} - organization {pipeline.organization.name} "
                f"is not allowed to sync data"
            )
            # Still update next run time
            self._update_next_run_time(pipeline, current_time)
            return

        # Create a pipeline run
        run = PipelineRun(
            pipeline_id=pipeline.id,
            status="pending",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        logger.info(f"Created run {run.id} for pipeline {pipeline.id}")

        # Trigger pipeline execution via Prefect (async)
        try:
            # Import here to avoid circular dependencies

            # Note: In production, you would use Prefect's deployment system
            # For now, we'll call execute_pipeline_flow directly
            execute_pipeline_flow(pipeline.id, run.id)

            logger.info(f"Successfully triggered pipeline {pipeline.id}, run {run.id}")

        except Exception as e:
            logger.error(f"Failed to trigger pipeline {pipeline.id}: {str(e)}", exc_info=True)
            # Mark run as failed
            run.status = "failed"
            run.error_message = f"Failed to trigger: {str(e)}"
            self.db.commit()

        # Update last run time and calculate next run
        self._update_next_run_time(pipeline, current_time)

    def _update_next_run_time(self, pipeline: Pipeline, current_time: datetime):
        """
        Update pipeline's last and next run times.

        Args:
            pipeline: Pipeline to update
            current_time: Current time (UTC)
        """
        try:
            # Update last scheduled run
            pipeline.last_scheduled_run = current_time

            # Calculate next run time
            if pipeline.schedule:
                timezone_str = pipeline.schedule_timezone or 'UTC'

                next_run = calculate_next_run(
                    pipeline.schedule,
                    from_time=current_time,
                    timezone_str=timezone_str
                )

                pipeline.next_scheduled_run = next_run

                logger.info(
                    f"Updated pipeline {pipeline.id} schedule: "
                    f"last={current_time.isoformat()}, "
                    f"next={next_run.isoformat()} ({timezone_str})"
                )

            self.db.commit()

        except CronValidationError as e:
            logger.error(
                f"Invalid cron expression for pipeline {pipeline.id}: {str(e)}"
            )
            # Disable scheduling for this pipeline
            pipeline.schedule_enabled = False
            self.db.commit()

        except Exception as e:
            logger.error(
                f"Failed to update next run time for pipeline {pipeline.id}: {str(e)}",
                exc_info=True
            )

    def update_all_next_run_times(self):
        """
        Update next run times for all scheduled pipelines.

        Useful for initializing the scheduler or fixing schedules after downtime.
        """
        logger.info("Updating next run times for all scheduled pipelines...")

        try:
            pipelines = (
                self.db.query(Pipeline)
                .filter(
                    Pipeline.is_active,
                    Pipeline.schedule_enabled,
                    Pipeline.schedule.isnot(None)
                )
                .all()
            )

            logger.info(f"Found {len(pipelines)} scheduled pipelines")

            for pipeline in pipelines:
                try:
                    timezone_str = pipeline.schedule_timezone or 'UTC'
                    next_run = calculate_next_run(
                        pipeline.schedule,
                        timezone_str=timezone_str
                    )

                    pipeline.next_scheduled_run = next_run
                    logger.info(
                        f"Updated pipeline {pipeline.id} ({pipeline.name}): "
                        f"next run at {next_run.isoformat()}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to update pipeline {pipeline.id}: {str(e)}",
                        exc_info=True
                    )

            self.db.commit()
            logger.info("Finished updating next run times")

        except Exception as e:
            logger.error(f"Error updating next run times: {str(e)}", exc_info=True)


def main():
    """Main entry point for the scheduler."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("=== Pipeline Scheduler Starting ===")

    # Create and start scheduler
    scheduler = PipelineScheduler(check_interval_seconds=60)

    # Update all next run times on startup
    scheduler.db = get_db_session()
    try:
        scheduler.update_all_next_run_times()
    finally:
        if scheduler.db:
            scheduler.db.close()
            scheduler.db = None

    # Start the scheduler
    scheduler.start()


if __name__ == "__main__":
    main()
