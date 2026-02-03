"""
Pipeline Retry Handler Service.

Handles automatic retries for failed pipeline runs.
"""

import logging
import time
from typing import Optional
from datetime import datetime, timezone

from backend.database import get_db_session
from backend.models import Pipeline, PipelineRun
from backend.models.pipeline import PipelineStatus

logger = logging.getLogger(__name__)


def calculate_retry_delay(
    base_delay: int,
    retry_count: int,
    exponential_backoff: bool = False,
    max_delay: int = 3600,
) -> int:
    """
    Calculate retry delay in seconds.

    Args:
        base_delay: Base delay in seconds
        retry_count: Current retry attempt (0-indexed)
        exponential_backoff: Whether to use exponential backoff
        max_delay: Maximum delay in seconds (default: 1 hour)

    Returns:
        Delay in seconds
    """
    if not exponential_backoff:
        return base_delay

    # Exponential backoff: delay = base_delay * (2 ** retry_count)
    delay = base_delay * (2 ** retry_count)

    # Cap at max_delay
    return min(delay, max_delay)


def should_retry_pipeline(pipeline: Pipeline, run: PipelineRun) -> bool:
    """
    Determine if a failed pipeline run should be retried.

    Args:
        pipeline: Pipeline configuration
        run: Failed pipeline run

    Returns:
        True if should retry, False otherwise
    """
    # Check if retries are configured
    if pipeline.max_retries <= 0:
        logger.info(f"No retries configured for pipeline {pipeline.id}")
        return False

    # Check if we've exhausted retry attempts
    if run.retry_count >= pipeline.max_retries:
        logger.info(
            f"Max retries ({pipeline.max_retries}) reached for pipeline {pipeline.id}, "
            f"run {run.id} (retry_count={run.retry_count})"
        )
        return False

    # Only retry if pipeline is active
    if not pipeline.is_active:
        logger.info(f"Pipeline {pipeline.id} is not active, skipping retry")
        return False

    logger.info(
        f"Pipeline {pipeline.id} run {run.id} will be retried "
        f"(attempt {run.retry_count + 1}/{pipeline.max_retries})"
    )
    return True


def schedule_pipeline_retry(
    pipeline_id: int,
    failed_run_id: int,
    retry_immediately: bool = False,
) -> Optional[int]:
    """
    Schedule a retry for a failed pipeline run.

    Args:
        pipeline_id: Pipeline ID
        failed_run_id: ID of the failed run
        retry_immediately: If True, trigger retry immediately (for testing)

    Returns:
        ID of the new retry run, or None if retry not scheduled
    """
    db = get_db_session()
    try:
        # Get pipeline and failed run
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline:
            logger.error(f"Pipeline {pipeline_id} not found")
            return None

        failed_run = db.query(PipelineRun).filter(PipelineRun.id == failed_run_id).first()
        if not failed_run:
            logger.error(f"Pipeline run {failed_run_id} not found")
            return None

        # Check if should retry
        if not should_retry_pipeline(pipeline, failed_run):
            return None

        # Calculate retry delay
        retry_count = failed_run.retry_count + 1
        delay_seconds = calculate_retry_delay(
            base_delay=pipeline.retry_delay_seconds,
            retry_count=retry_count,
            exponential_backoff=pipeline.exponential_backoff_enabled,
        )

        logger.info(
            f"Scheduling retry for pipeline {pipeline_id} after {delay_seconds} seconds "
            f"(retry {retry_count}/{pipeline.max_retries})"
        )

        # Get original run ID (if this is already a retry, use its original_run_id)
        original_run_id = failed_run.original_run_id if failed_run.is_retry else failed_run.id

        # Create new retry run
        retry_run = PipelineRun(
            pipeline_id=pipeline_id,
            status=PipelineStatus.PENDING,
            retry_count=retry_count,
            is_retry=True,
            original_run_id=original_run_id,
            run_metadata={
                "retry_reason": "automatic_retry",
                "failed_run_id": failed_run_id,
                "retry_delay_seconds": delay_seconds,
                "scheduled_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        db.add(retry_run)
        db.commit()
        db.refresh(retry_run)

        logger.info(f"Created retry run {retry_run.id} for pipeline {pipeline_id}")

        # If not immediate retry, wait for the delay
        if not retry_immediately and delay_seconds > 0:
            logger.info(f"Waiting {delay_seconds} seconds before triggering retry...")
            time.sleep(delay_seconds)

        # Trigger the retry run
        try:
            from backend.prefect_flows.pipeline_flow import execute_pipeline_flow

            logger.info(f"Triggering retry run {retry_run.id}")
            execute_pipeline_flow.delay(pipeline_id=pipeline_id, run_id=retry_run.id)

            logger.info(f"Successfully scheduled retry run {retry_run.id}")
            return retry_run.id

        except Exception as e:
            logger.error(f"Failed to trigger retry run {retry_run.id}: {str(e)}", exc_info=True)

            # Update retry run status to failed
            retry_run.status = PipelineStatus.FAILED
            retry_run.error_message = f"Failed to trigger retry: {str(e)}"
            db.commit()

            return None

    except Exception as e:
        logger.error(f"Failed to schedule pipeline retry: {str(e)}", exc_info=True)
        db.rollback()
        return None
    finally:
        db.close()


def handle_pipeline_failure(
    pipeline_id: int,
    run_id: int,
    error_message: str,
    retry_immediately: bool = False,
) -> Optional[int]:
    """
    Handle a pipeline failure and potentially schedule a retry.

    This is the main entry point for retry logic after a pipeline fails.

    Args:
        pipeline_id: Pipeline ID
        run_id: Failed run ID
        error_message: Error message from failure
        retry_immediately: If True, trigger retry immediately (for testing)

    Returns:
        ID of retry run if scheduled, None otherwise
    """
    logger.info(
        f"Handling pipeline failure: pipeline_id={pipeline_id}, "
        f"run_id={run_id}, error={error_message}"
    )

    return schedule_pipeline_retry(
        pipeline_id=pipeline_id,
        failed_run_id=run_id,
        retry_immediately=retry_immediately,
    )
