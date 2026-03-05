"""
Business Summary Celery Tasks.

Scheduled tasks that email AI-powered (or template-based) business summaries
to organization admins on a daily and weekly cadence.

The beat schedule is registered via the on_after_configure signal so that
this module does NOT need to modify celery_app.py (another agent owns it).

Queue routing: "summaries" queue (add to celery_app task_routes if needed).

To include this module in the Celery worker, add
    "backend.tasks.summary_tasks"
to the `include` list in backend/celery_app.py.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from celery.schedules import crontab

from backend.celery_app import celery_app, BaseTask
from backend.database import SessionLocal
from backend.models.pipeline import Organization

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Beat schedule registration (signal-based — does not touch celery_app.py)
# ---------------------------------------------------------------------------

@celery_app.on_after_configure.connect
def setup_summary_tasks(sender, **kwargs):
    """
    Register periodic summary tasks with Celery Beat.

    This is called automatically after Celery is configured so we can add
    our beat entries without modifying celery_app.py.
    """
    sender.add_periodic_task(
        crontab(hour=8, minute=0, day_of_week=1),  # Mondays 08:00 UTC
        send_weekly_summaries.s(),
        name="weekly-business-summaries",
    )
    sender.add_periodic_task(
        crontab(hour=7, minute=0),  # Every day 07:00 UTC
        send_daily_summaries.s(),
        name="daily-business-summaries",
    )
    logger.info("Summary beat tasks registered: weekly (Mon 08:00 UTC) + daily (07:00 UTC)")


# ---------------------------------------------------------------------------
# Task base class (inherits retry / limit config from BaseTask)
# ---------------------------------------------------------------------------

class SummaryTask(BaseTask):
    """Base class for summary tasks with conservative retry settings."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600    # 10 minutes max between retries
    max_retries = 2
    soft_time_limit = 300      # 5 minutes soft limit per task
    time_limit = 360           # 6 minutes hard limit


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    base=SummaryTask,
    name="backend.tasks.summary_tasks.send_weekly_summaries",
)
def send_weekly_summaries(self) -> Dict[str, Any]:
    """
    Send weekly business summaries to all active organizations.

    Scheduled: Mondays at 08:00 UTC.

    Returns a dict with per-org send results for monitoring / beat result inspection.
    """
    db = SessionLocal()
    try:
        start = datetime.now(timezone.utc)
        logger.info("Starting weekly business summary task")

        results: Dict[str, Any] = {
            "started_at": start.isoformat(),
            "frequency": "weekly",
            "orgs_attempted": 0,
            "orgs_succeeded": 0,
            "orgs_failed": 0,
            "details": [],
        }

        # Import inside function to avoid circular imports at module load time
        from backend.services.summary_service import BusinessSummaryService

        orgs = (
            db.query(Organization)
            .filter(Organization.is_active.is_(True))
            .all()
        )

        for org in orgs:
            results["orgs_attempted"] += 1
            try:
                service = BusinessSummaryService(db)
                sent = service.send_summary_email(org_id=org.id, frequency="weekly")
                if sent:
                    results["orgs_succeeded"] += 1
                    results["details"].append({"org_id": org.id, "org_name": org.name, "sent": True})
                else:
                    # Not a failure — may simply have no admin emails configured
                    results["details"].append({
                        "org_id": org.id,
                        "org_name": org.name,
                        "sent": False,
                        "reason": "No admin emails or email not configured",
                    })
            except Exception as exc:
                results["orgs_failed"] += 1
                logger.error("Weekly summary failed for org %d (%s): %s", org.id, org.name, exc)
                results["details"].append({
                    "org_id": org.id,
                    "org_name": org.name,
                    "sent": False,
                    "error": str(exc),
                })

        end = datetime.now(timezone.utc)
        results["completed_at"] = end.isoformat()
        results["duration_seconds"] = (end - start).total_seconds()

        logger.info(
            "Weekly summaries done: %d sent, %d failed, %d orgs total",
            results["orgs_succeeded"],
            results["orgs_failed"],
            results["orgs_attempted"],
        )
        return results

    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=SummaryTask,
    name="backend.tasks.summary_tasks.send_daily_summaries",
)
def send_daily_summaries(self) -> Dict[str, Any]:
    """
    Send daily digest emails to all active organizations.

    Scheduled: Every day at 07:00 UTC.

    NOTE: In a future iteration this should respect a per-org opt-in flag
    so that only organizations that have requested daily summaries receive them.
    For now all active orgs are included.

    Returns a dict with per-org send results.
    """
    db = SessionLocal()
    try:
        start = datetime.now(timezone.utc)
        logger.info("Starting daily business summary task")

        results: Dict[str, Any] = {
            "started_at": start.isoformat(),
            "frequency": "daily",
            "orgs_attempted": 0,
            "orgs_succeeded": 0,
            "orgs_failed": 0,
            "details": [],
        }

        from backend.services.summary_service import BusinessSummaryService

        orgs = (
            db.query(Organization)
            .filter(Organization.is_active.is_(True))
            .all()
        )

        for org in orgs:
            results["orgs_attempted"] += 1
            try:
                service = BusinessSummaryService(db)
                sent = service.send_summary_email(org_id=org.id, frequency="daily")
                if sent:
                    results["orgs_succeeded"] += 1
                    results["details"].append({"org_id": org.id, "org_name": org.name, "sent": True})
                else:
                    results["details"].append({
                        "org_id": org.id,
                        "org_name": org.name,
                        "sent": False,
                        "reason": "No admin emails or email not configured",
                    })
            except Exception as exc:
                results["orgs_failed"] += 1
                logger.error("Daily summary failed for org %d (%s): %s", org.id, org.name, exc)
                results["details"].append({
                    "org_id": org.id,
                    "org_name": org.name,
                    "sent": False,
                    "error": str(exc),
                })

        end = datetime.now(timezone.utc)
        results["completed_at"] = end.isoformat()
        results["duration_seconds"] = (end - start).total_seconds()

        logger.info(
            "Daily summaries done: %d sent, %d failed, %d orgs total",
            results["orgs_succeeded"],
            results["orgs_failed"],
            results["orgs_attempted"],
        )
        return results

    finally:
        db.close()


# ---------------------------------------------------------------------------
# On-demand per-org tasks (can be triggered manually from the API)
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    base=SummaryTask,
    name="backend.tasks.summary_tasks.send_org_summary",
)
def send_org_summary(self, org_id: int, frequency: str = "weekly") -> Dict[str, Any]:
    """
    Send a summary for a single organization on demand.

    This task is dispatched by the POST /summaries/generate endpoint when
    send_email=True so that the HTTP response is not delayed by email sending.

    Args:
        org_id:    Target organization ID.
        frequency: "weekly" or "daily".

    Returns:
        Dict with success flag and generated summary text.
    """
    db = SessionLocal()
    try:
        from backend.services.summary_service import BusinessSummaryService

        service = BusinessSummaryService(db)

        if frequency == "daily":
            summary_text = service.generate_daily_summary(org_id)
        else:
            summary_text = service.generate_weekly_summary(org_id)

        sent = service.send_summary_email(org_id=org_id, frequency=frequency)

        logger.info(
            "On-demand %s summary for org %d: %s",
            frequency,
            org_id,
            "sent" if sent else "not sent (email config missing)",
        )

        return {
            "org_id": org_id,
            "frequency": frequency,
            "email_sent": sent,
            "summary_preview": summary_text[:300] + "..." if len(summary_text) > 300 else summary_text,
        }

    finally:
        db.close()
