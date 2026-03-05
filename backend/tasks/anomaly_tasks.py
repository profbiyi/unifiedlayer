"""
Anomaly Detection Celery Tasks.

Runs anomaly detection across all active pipelines on a 15-minute
cadence.  When anomalies are found, alerts are dispatched via:
    - Email (if SMTP is configured)
    - WhatsApp (if Twilio credentials are configured)

Beat schedule registration
--------------------------
The Celery beat_schedule dict in ``backend/celery_app.py`` is managed by
another module and MUST NOT be modified here.  Instead, we use the
``on_after_configure`` signal to register the periodic task at worker
startup.  This is functionally equivalent to declaring it in beat_schedule.

Deduplication
-------------
A module-level dictionary ``_sent_alerts`` tracks the last time each
(pipeline_id, alert_type) pair triggered a notification.  An alert is
only re-fired after ``DEDUP_TTL_HOURS`` (default: 4) hours have passed,
preventing alert floods for persistent issues.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from backend.celery_app import celery_app, BaseTask
from backend.database import SessionLocal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deduplication store
# ---------------------------------------------------------------------------

# key  → f"{pipeline_id}:{alert_type}"
# value → datetime (UTC) of when the alert was last fired
_sent_alerts: Dict[str, datetime] = {}

# How long (in hours) before the same (pipeline, alert_type) is re-alerted.
DEDUP_TTL_HOURS: int = 4


def _is_duplicate(dedup_key: str) -> bool:
    """Return True if this alert was already sent within DEDUP_TTL_HOURS."""
    last_sent = _sent_alerts.get(dedup_key)
    if last_sent is None:
        return False
    return datetime.now(timezone.utc) - last_sent < timedelta(hours=DEDUP_TTL_HOURS)


def _mark_sent(dedup_key: str) -> None:
    """Record the current timestamp for this alert key."""
    _sent_alerts[dedup_key] = datetime.now(timezone.utc)


def _prune_dedup_store() -> None:
    """
    Remove stale entries from the in-memory dedup store.

    Keeps the dict from growing unboundedly in long-running workers.
    Entries older than 2× TTL are safe to evict.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=DEDUP_TTL_HOURS * 2)
    stale_keys = [k for k, v in _sent_alerts.items() if v < cutoff]
    for k in stale_keys:
        del _sent_alerts[k]


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

class AnomalyTask(BaseTask):
    """Task base class for anomaly detection jobs."""

    abstract = True
    max_retries = 2
    retry_backoff = True
    retry_backoff_max = 120  # seconds
    soft_time_limit = 300    # 5-minute soft limit
    time_limit = 360         # 6-minute hard limit


@celery_app.task(
    bind=True,
    base=AnomalyTask,
    name="backend.tasks.anomaly_tasks.detect_anomalies",
)
def detect_anomalies(self) -> Dict[str, Any]:
    """
    Run anomaly detection across all active pipelines.

    Steps
    -----
    1. Open a database session.
    2. Instantiate AnomalyDetector and call check_all_pipelines().
    3. For each detected anomaly:
       a. Skip if a duplicate alert was sent within the last 4 hours.
       b. Dispatch via email and WhatsApp.
       c. Update the dedup store.
    4. Prune stale dedup entries.
    5. Return a summary dict (stored in the Celery result backend).

    Returns:
        dict with keys: started_at, pipelines_checked (estimated),
        anomalies_found, alerts_fired, alerts_skipped_dedup.
    """
    started_at = datetime.now(timezone.utc)
    logger.info("Anomaly detection task started.")

    results: Dict[str, Any] = {
        "started_at": started_at.isoformat(),
        "anomalies_found": 0,
        "alerts_fired": 0,
        "alerts_skipped_dedup": 0,
        "errors": [],
    }

    db = SessionLocal()
    try:
        # Lazy import to avoid circular dependencies at module load time.
        from backend.services.anomaly_service import AnomalyDetector, AnomalyAlert

        detector = AnomalyDetector(db)
        anomalies: List[AnomalyAlert] = detector.check_all_pipelines()

        results["anomalies_found"] = len(anomalies)

        for anomaly in anomalies:
            dedup_key = anomaly.dedup_key

            if _is_duplicate(dedup_key):
                logger.debug(
                    "Suppressing duplicate alert %s (last sent < %dh ago)",
                    dedup_key,
                    DEDUP_TTL_HOURS,
                )
                results["alerts_skipped_dedup"] += 1
                continue

            # Fire the alert.
            fired = _dispatch_alert(anomaly)
            if fired:
                _mark_sent(dedup_key)
                results["alerts_fired"] += 1

    except Exception as exc:
        logger.exception("Anomaly detection task encountered a fatal error: %s", exc)
        results["errors"].append(str(exc))
        # Re-raise so Celery can apply retry logic from AnomalyTask base class.
        raise
    finally:
        db.close()
        _prune_dedup_store()

    logger.info(
        "Anomaly detection complete: %d found, %d fired, %d suppressed.",
        results["anomalies_found"],
        results["alerts_fired"],
        results["alerts_skipped_dedup"],
    )
    return results


# ---------------------------------------------------------------------------
# Alert dispatch helpers
# ---------------------------------------------------------------------------

def _dispatch_alert(anomaly) -> bool:
    """
    Send an anomaly alert via all configured channels.

    Args:
        anomaly: AnomalyAlert dataclass instance.

    Returns:
        True if at least one channel delivered the alert successfully.
    """
    any_sent = False

    # -- Email --
    try:
        from backend.notifications import email_notifier
        from backend.config import settings

        if settings.SMTP_HOST or settings.SENDGRID_API_KEY:
            subject = f"[{anomaly.severity.upper()}] {anomaly.message[:80]}"
            body = _build_email_body(anomaly)
            # Attempt to find org admin emails from the database.
            # We keep this best-effort: if it fails we still try WhatsApp.
            recipients = _get_org_admin_emails(anomaly.org_id)
            if recipients:
                email_notifier.send(
                    to_emails=recipients,
                    subject=subject,
                    body=body,
                    html=False,
                )
                logger.info(
                    "Anomaly alert emailed to %d recipient(s) for pipeline %s.",
                    len(recipients),
                    anomaly.pipeline_name,
                )
                any_sent = True
            else:
                logger.debug(
                    "No org admin email recipients found for org_id=%s.",
                    anomaly.org_id,
                )
    except Exception as exc:
        logger.warning("Email alert dispatch failed: %s", exc)

    # -- WhatsApp --
    try:
        from backend.notifications import send_whatsapp_notification
        from backend.config import settings

        whatsapp_numbers = _get_org_whatsapp_numbers(anomaly.org_id)
        if whatsapp_numbers:
            title = f"Pipeline Alert ({anomaly.severity.capitalize()})"
            details_summary = ", ".join(
                f"{k}={v}" for k, v in list(anomaly.details.items())[:3]
            )
            wa_message = f"{anomaly.message}\n\nDetails: {details_summary}"
            for number in whatsapp_numbers:
                sent = send_whatsapp_notification(
                    to_number=number,
                    title=title,
                    message=wa_message,
                )
                if sent:
                    logger.info(
                        "Anomaly WhatsApp alert sent to %s for pipeline %s.",
                        number,
                        anomaly.pipeline_name,
                    )
                    any_sent = True
    except Exception as exc:
        logger.warning("WhatsApp alert dispatch failed: %s", exc)

    if not any_sent:
        # Log at INFO — having no channels configured is not an error.
        logger.info(
            "Anomaly detected but no notification channels are configured "
            "(pipeline: %s, type: %s). Configure SMTP or Twilio to receive alerts.",
            anomaly.pipeline_name,
            anomaly.alert_type,
        )

    return any_sent


def _build_email_body(anomaly) -> str:
    """Compose a plain-text email body from an AnomalyAlert."""
    lines = [
        f"Pipeline: {anomaly.pipeline_name}",
        f"Anomaly Type: {anomaly.alert_type}",
        f"Severity: {anomaly.severity.upper()}",
        "",
        anomaly.message,
        "",
        "Details:",
    ]
    for key, value in anomaly.details.items():
        lines.append(f"  {key}: {value}")

    lines += [
        "",
        "This alert is managed by UnifiedLayer Anomaly Detection.",
        "Alerts repeat every 4 hours while the issue persists.",
    ]
    return "\n".join(lines)


def _get_org_admin_emails(org_id: int) -> List[str]:
    """
    Return email addresses of active org-admin users for the given org.

    Falls back to an empty list on any error so callers stay resilient.
    """
    try:
        from backend.database import SessionLocal
        from backend.models.pipeline import User
        from backend.models.rbac import UserRole, Role

        db = SessionLocal()
        try:
            # Find users who have the 'org_admin' role in this organisation.
            admins = (
                db.query(User)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .filter(
                    User.organization_id == org_id,
                    User.is_active.is_(True),
                    Role.slug.in_(["org_admin", "super_admin"]),
                )
                .all()
            )
            return [u.email for u in admins if u.email]
        finally:
            db.close()
    except Exception as exc:
        logger.debug("Could not fetch org admin emails for org_id=%s: %s", org_id, exc)
        return []


def _get_org_whatsapp_numbers(org_id: int) -> List[str]:
    """
    Return WhatsApp-enabled phone numbers for the organisation.

    Current implementation: reads ANOMALY_WHATSAPP_NUMBERS from the
    application config (comma-separated list of E.164 numbers).  This is
    intentionally simple — a future iteration can store per-org numbers
    in the database.

    Returns an empty list when no numbers are configured.
    """
    try:
        from backend.config import settings

        raw: str = getattr(settings, "ANOMALY_WHATSAPP_NUMBERS", None) or ""
        numbers = [n.strip() for n in raw.split(",") if n.strip()]
        return numbers
    except Exception as exc:
        logger.debug("Could not read ANOMALY_WHATSAPP_NUMBERS: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Celery beat schedule — registered via signal (celery_app.py is read-only)
# ---------------------------------------------------------------------------

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Register the anomaly detection periodic task with Celery Beat.

    Runs every 15 minutes (900 seconds).  Using the ``on_after_configure``
    signal avoids modifying ``backend/celery_app.py``.
    """
    sender.add_periodic_task(
        900.0,  # 15 minutes
        detect_anomalies.s(),
        name="detect-pipeline-anomalies",
        queue="default",
    )
    logger.info("Registered periodic task: detect-pipeline-anomalies (every 900s)")
