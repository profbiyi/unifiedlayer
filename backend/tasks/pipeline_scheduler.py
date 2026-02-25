"""
Pipeline Scheduler Celery Task.

Periodically checks for scheduled pipelines that are due to run
and submits them to Prefect for execution.

Design:
- Runs every 60 seconds via Celery Beat
- Idempotent: checks for active runs before creating a new PipelineRun
- Per-pipeline exception isolation: one pipeline failure doesn't block others
- Updates next_scheduled_run after triggering each pipeline
- Respects organization-level can_sync_data flag
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from backend.celery_app import celery_app, BaseTask
from backend.database import SessionLocal
from backend.models.pipeline import Pipeline, PipelineRun, PipelineStatus
from backend.utils.cron_utils import calculate_next_run, CronValidationError

logger = logging.getLogger(__name__)

# How far back to look for PENDING/RUNNING runs as the idempotency window
IDEMPOTENCY_WINDOW_MINUTES = 10


class PipelineSchedulerTask(BaseTask):
    """Base task class for the pipeline scheduler."""

    # Don't auto-retry — if the whole check loop errors, wait for the next beat tick
    max_retries = 0
    soft_time_limit = 55  # Must finish before the next 60 s tick
    time_limit = 58


@celery_app.task(
    bind=True,
    base=PipelineSchedulerTask,
    name="backend.tasks.pipeline_scheduler.check_and_run_scheduled_pipelines",
)
def check_and_run_scheduled_pipelines(self) -> Dict[str, Any]:
    """
    Check all active scheduled pipelines and trigger runs for any that are due.

    Called by Celery Beat every 60 seconds.

    Returns:
        Summary dict with counts of pipelines checked, triggered, and skipped.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        logger.info("Pipeline scheduler: checking for due pipelines at %s", now.isoformat())

        results: Dict[str, Any] = {
            "checked_at": now.isoformat(),
            "pipelines_checked": 0,
            "pipelines_triggered": 0,
            "pipelines_skipped": 0,
            "errors": [],
        }

        # Find all active, schedule-enabled pipelines whose next run is overdue
        # We look up to 1 minute into the future to catch pipelines scheduled
        # for the current minute that might fire slightly before the exact second.
        due_pipelines = (
            db.query(Pipeline)
            .filter(
                Pipeline.is_active.is_(True),
                Pipeline.schedule_enabled.is_(True),
                Pipeline.schedule.isnot(None),
                Pipeline.next_scheduled_run <= now + timedelta(minutes=1),
            )
            .all()
        )

        if not due_pipelines:
            logger.debug("Pipeline scheduler: no due pipelines found")
            return results

        logger.info("Pipeline scheduler: found %d due pipeline(s)", len(due_pipelines))

        for pipeline in due_pipelines:
            results["pipelines_checked"] += 1
            try:
                triggered = _maybe_trigger_pipeline(db, pipeline, now)
                if triggered:
                    results["pipelines_triggered"] += 1
                else:
                    results["pipelines_skipped"] += 1
            except Exception as exc:
                # Isolate: log the error for this pipeline, continue with others
                error_msg = f"Pipeline {pipeline.id} ({pipeline.name}): {exc}"
                logger.error(
                    "Pipeline scheduler: error processing pipeline %d (%s): %s",
                    pipeline.id, pipeline.name, exc,
                    exc_info=True,
                )
                results["errors"].append(error_msg)

        logger.info(
            "Pipeline scheduler: done — checked=%d triggered=%d skipped=%d errors=%d",
            results["pipelines_checked"],
            results["pipelines_triggered"],
            results["pipelines_skipped"],
            len(results["errors"]),
        )
        return results

    finally:
        db.close()


def _maybe_trigger_pipeline(db, pipeline: Pipeline, now: datetime) -> bool:
    """
    Evaluate one pipeline and trigger a run if safe to do so.

    Args:
        db: Open SQLAlchemy session.
        pipeline: Pipeline ORM instance.
        now: Current UTC datetime.

    Returns:
        True if a run was created and submitted, False if skipped.
    """
    # --- Guard 1: organization sync flag ---
    if pipeline.organization and not pipeline.organization.can_sync_data:
        logger.warning(
            "Skipping pipeline %d (%s): organization '%s' has can_sync_data=False",
            pipeline.id, pipeline.name,
            pipeline.organization.name if pipeline.organization else "unknown",
        )
        _advance_next_run(db, pipeline, now)
        return False

    # --- Guard 2: idempotency — no active run in the last IDEMPOTENCY_WINDOW_MINUTES ---
    window_start = now - timedelta(minutes=IDEMPOTENCY_WINDOW_MINUTES)
    active_run = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.pipeline_id == pipeline.id,
            PipelineRun.status.in_([PipelineStatus.PENDING, PipelineStatus.RUNNING]),
            PipelineRun.created_at >= window_start,
        )
        .first()
    )
    if active_run:
        logger.info(
            "Skipping pipeline %d (%s): active run %d exists (status=%s, created=%s)",
            pipeline.id, pipeline.name,
            active_run.id, active_run.status.value,
            active_run.created_at.isoformat() if active_run.created_at else "unknown",
        )
        return False

    # --- Create PipelineRun record ---
    run = PipelineRun(
        pipeline_id=pipeline.id,
        status=PipelineStatus.PENDING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info(
        "Pipeline scheduler: created run %d for pipeline %d (%s)",
        run.id, pipeline.id, pipeline.name,
    )

    # --- Submit to Prefect ---
    _submit_to_prefect(db, pipeline, run, now)

    # --- Advance the next scheduled run ---
    _advance_next_run(db, pipeline, now)

    return True


def _submit_to_prefect(db, pipeline: Pipeline, run: PipelineRun, now: datetime) -> None:
    """
    Submit the pipeline flow to Prefect and handle failures.

    Mirrors the logic in routes/pipelines.py::_submit_flow_to_prefect but
    runs synchronously inside the Celery worker (Celery already provides
    the async context via its own worker process).

    Args:
        db: Open SQLAlchemy session (used only to mark run FAILED on error).
        pipeline: Pipeline ORM instance.
        run: Newly created PipelineRun instance.
        now: Current UTC timestamp (unused here, kept for symmetry).
    """
    from backend.prefect_flows.pipeline_flow import execute_pipeline_flow

    try:
        execute_pipeline_flow(pipeline.id, run.id)
        logger.info(
            "Pipeline scheduler: Prefect flow submitted for pipeline %d, run %d",
            pipeline.id, run.id,
        )
    except Exception as exc:
        error_msg = str(exc)
        logger.error(
            "Pipeline scheduler: Prefect submission failed for pipeline %d, run %d: %s",
            pipeline.id, run.id, error_msg,
            exc_info=True,
        )
        # Mark run FAILED so it doesn't stay as PENDING forever
        try:
            run.status = PipelineStatus.FAILED
            run.error_message = f"Scheduler failed to submit to Prefect: {error_msg[:500]}"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as db_exc:
            logger.error(
                "Pipeline scheduler: could not mark run %d as FAILED after submission error: %s",
                run.id, db_exc,
            )
        # Re-raise so the caller can record this as an error in the summary
        raise


def _advance_next_run(db, pipeline: Pipeline, now: datetime) -> None:
    """
    Update last_scheduled_run and compute the next_scheduled_run timestamp.

    If the cron expression is invalid, disables scheduling for the pipeline
    rather than crashing the whole task.

    Args:
        db: Open SQLAlchemy session.
        pipeline: Pipeline ORM instance.
        now: Current UTC datetime to use as the 'from' time.
    """
    try:
        pipeline.last_scheduled_run = now
        timezone_str = pipeline.schedule_timezone or "UTC"
        next_run = calculate_next_run(
            pipeline.schedule,
            from_time=now,
            timezone_str=timezone_str,
        )
        pipeline.next_scheduled_run = next_run
        db.commit()
        logger.info(
            "Pipeline scheduler: pipeline %d (%s) next run scheduled for %s (%s)",
            pipeline.id, pipeline.name,
            next_run.isoformat(), timezone_str,
        )
    except CronValidationError as exc:
        logger.error(
            "Pipeline scheduler: invalid cron expression '%s' for pipeline %d (%s) — "
            "disabling schedule: %s",
            pipeline.schedule, pipeline.id, pipeline.name, exc,
        )
        pipeline.schedule_enabled = False
        db.commit()
    except Exception as exc:
        logger.error(
            "Pipeline scheduler: failed to advance next run for pipeline %d (%s): %s",
            pipeline.id, pipeline.name, exc,
            exc_info=True,
        )
