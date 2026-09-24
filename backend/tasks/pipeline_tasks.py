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
import os
from datetime import datetime, timedelta, timezone

from backend.celery_app import celery_app

logger = logging.getLogger(__name__)

# A single run should never legitimately exceed the flow/load time limits
# (flow timeout 1800s, load task time_limit 3900s). Give generous headroom.
DEFAULT_STUCK_RUN_HOURS = 2

# Task time limits are env-configurable so a large single-table load (or a
# backfill chunk over a wide window) can be given more room without a code
# change. Defaults are unchanged from before. Once chunked backfill lands, each
# chunk is small and these defaults are plenty; this is the escape hatch for a
# one-shot big load in the meantime.
_TASK_SOFT_TIME_LIMIT = int(os.getenv("PIPELINE_TASK_SOFT_TIME_LIMIT", "3600"))
_TASK_HARD_TIME_LIMIT = int(os.getenv("PIPELINE_TASK_TIME_LIMIT", "3900"))

# Work-conserving per-org fairness.
#
# MAX_ORG_CONCURRENT_SYNCS is a GUARANTEED share, not a hard cap: an org may
# always run up to this many syncs. ABOVE that share, an org may keep bursting
# into idle capacity — UNLESS another org has work waiting, in which case the
# bursting org's extra run is deferred so the waiting tenant gets the slot.
#
# So: platform quiet → one company can run 10+ at once (uses the idle workers);
# another company queues work → the burster is throttled back to its fair share
# and the newcomer runs. No org is ever starved by another. 0 disables fairness.
_MAX_ORG_CONCURRENCY = int(os.getenv("MAX_ORG_CONCURRENT_SYNCS", "3"))
_ORG_DEFER_SECONDS = int(os.getenv("ORG_DEFER_SECONDS", "15"))


def _should_defer_for_fairness(pipeline_id: int, run_id: int) -> bool:
    """Defer this run only if the org is OVER its fair share AND another org is
    waiting. Within the fair share, or when no one else is waiting, allow it."""
    if _MAX_ORG_CONCURRENCY <= 0:
        return False
    from backend.database import get_db_session
    from backend.models.pipeline import Pipeline, PipelineRun, PipelineStatus

    db = get_db_session()
    try:
        pipe = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipe:
            return False
        org_id = pipe.organization_id

        org_running = (
            db.query(PipelineRun)
            .join(Pipeline, PipelineRun.pipeline_id == Pipeline.id)
            .filter(
                Pipeline.organization_id == org_id,
                PipelineRun.status == PipelineStatus.RUNNING,
                PipelineRun.id != run_id,
            )
            .count()
        )
        # Within the guaranteed share → always allow.
        if org_running < _MAX_ORG_CONCURRENCY:
            return False

        # Over the share → only yield if ANOTHER org has a run waiting to start.
        others_waiting = (
            db.query(PipelineRun)
            .join(Pipeline, PipelineRun.pipeline_id == Pipeline.id)
            .filter(
                Pipeline.organization_id != org_id,
                PipelineRun.status == PipelineStatus.PENDING,
                PipelineRun.id != run_id,
            )
            .count()
        )
        return others_waiting > 0
    except Exception as exc:  # noqa: BLE001 — fairness check must never block a run
        logger.warning("fairness check failed (%s); allowing run", exc)
        return False
    finally:
        db.close()


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
    soft_time_limit=_TASK_SOFT_TIME_LIMIT,
    time_limit=_TASK_HARD_TIME_LIMIT,
)
def run_pipeline(self, pipeline_id: int, run_id: int):
    """Execute one pipeline run in a worker. Marks the run FAILED on error.

    Enqueued via ``run_pipeline.delay(pipeline_id, run_id)`` by the trigger
    endpoint and the scheduler. Imports the flow lazily so importing this module
    (which Celery does at worker start) stays cheap.
    """
    from backend.prefect_flows.pipeline_flow import execute_pipeline_flow

    # Work-conserving per-org fairness: defer this run only if the org is over its
    # fair share AND another tenant is waiting for a slot. An org can still burst
    # into idle capacity; it just yields the moment someone else needs to run.
    if _should_defer_for_fairness(pipeline_id, run_id):
        logger.info(
            "run_pipeline: deferring run=%s (pipeline=%s) — org over fair share and another tenant waiting",
            run_id, pipeline_id,
        )
        raise self.retry(countdown=_ORG_DEFER_SECONDS, max_retries=None)

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
