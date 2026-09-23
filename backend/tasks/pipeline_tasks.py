"""
Celery tasks for executing pipeline syncs off the web process.

Manual triggers (``routes/pipelines.py``) and the scheduler
(``pipeline_scheduler.py``) both enqueue ``run_pipeline``, so the actual sync
runs in a Celery worker instead of the FastAPI web process. This keeps the API
responsive under load and means a web restart no longer orphans a running sync
(``task_acks_late`` + ``task_reject_on_worker_lost`` requeue it).

``reconcile_stuck_runs`` is a periodic backstop that fails runs left in
PENDING/RUNNING beyond a cutoff (e.g. a worker was OOM-killed).
"""
import logging
from datetime import datetime, timedelta, timezone

from backend.celery_app import celery_app

logger = logging.getLogger(__name__)

# A single run should never legitimately exceed the flow/load time limits
# (flow timeout 1800s, load task time_limit 3900s). Give generous headroom.
DEFAULT_STUCK_RUN_HOURS = 2


def _mark_run_failed(run_id: int, message: str) -> None:
    """Best-effort: mark a run FAILED if it is still PENDING/RUNNING."""
    from backend.database import get_db_session
    from backend.models.pipeline import PipelineRun, PipelineStatus

    try:
        db = get_db_session()
        try:
            run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
            if run and run.status in (PipelineStatus.PENDING, PipelineStatus.RUNNING):
                run.status = PipelineStatus.FAILED
                run.error_message = message
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                logger.info("Marked run %s FAILED: %s", run_id, message)
        finally:
            db.close()
    except Exception as db_err:  # noqa: BLE001 — never let cleanup raise
        logger.error("Failed to mark run %s FAILED: %s", run_id, db_err)


@celery_app.task(
    bind=True,
    name="backend.tasks.pipeline_tasks.run_pipeline",
    soft_time_limit=3600,
    time_limit=3900,
)
def run_pipeline(self, pipeline_id: int, run_id: int):
    """Execute one pipeline run in a worker. Marks the run FAILED on error.

    Enqueued via ``run_pipeline.delay(pipeline_id, run_id)`` by the trigger
    endpoint and the scheduler. Imports the flow lazily so importing this module
    (which Celery does at worker start) stays cheap.
    """
    from backend.prefect_flows.pipeline_flow import execute_pipeline_flow

    logger.info("run_pipeline: executing pipeline=%s run=%s", pipeline_id, run_id)
    try:
        return execute_pipeline_flow(pipeline_id, run_id)
    except Exception as exc:  # noqa: BLE001 — surface as a failed run, then re-raise
        logger.error(
            "run_pipeline failed pipeline=%s run=%s: %s",
            pipeline_id, run_id, exc, exc_info=True,
        )
        _mark_run_failed(run_id, f"Pipeline execution failed: {str(exc)[:500]}")
        raise


@celery_app.task(name="backend.tasks.pipeline_tasks.reconcile_stuck_runs")
def reconcile_stuck_runs(max_age_hours: int = DEFAULT_STUCK_RUN_HOURS):
    """Fail runs stuck in PENDING/RUNNING past the cutoff (orphaned by a crash)."""
    from backend.database import get_db_session
    from backend.models.pipeline import PipelineRun, PipelineStatus

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    db = get_db_session()
    failed = 0
    try:
        stuck = (
            db.query(PipelineRun)
            .filter(
                PipelineRun.status.in_([PipelineStatus.PENDING, PipelineStatus.RUNNING]),
                PipelineRun.created_at < cutoff,
            )
            .all()
        )
        for run in stuck:
            run.status = PipelineStatus.FAILED
            run.error_message = (
                f"Run exceeded {max_age_hours}h without completing (orphaned); "
                "failed by the reconciler."
            )
            run.completed_at = datetime.now(timezone.utc)
            failed += 1
        if failed:
            db.commit()
    finally:
        db.close()
    if failed:
        logger.warning("reconcile_stuck_runs: failed %d orphaned run(s)", failed)
    return {"failed": failed}
