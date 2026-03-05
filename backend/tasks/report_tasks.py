"""
Scheduled Report Celery Tasks.

Sends PDF reports to configured recipients on a regular cadence.
The task runs hourly and checks for any ScheduledReport whose
next_send_at is in the past and is_active=True.

IMPORTANT: To register this task with Celery Worker, add it to the
include list in backend/celery_app.py:
    "backend.tasks.report_tasks",

Do NOT modify celery_app.py unless authorised — instead, add the
import to the Celery worker startup or the FastAPI startup event.

The beat_schedule entry is appended at module load time (same pattern as
health_checks.py) so it will be picked up by celery beat on next reload.
"""
import logging
from datetime import datetime, timedelta, timezone

from backend.celery_app import celery_app, BaseTask
from backend.database import SessionLocal
from backend.models.scheduled_report import ReportFrequency, ScheduledReport
from backend.services.pdf_service import PDFReportService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper — compute next send time
# ---------------------------------------------------------------------------

def _next_send_at(report: ScheduledReport) -> datetime:
    """Return the next scheduled send time based on frequency."""
    now = datetime.now(timezone.utc)
    if report.frequency == ReportFrequency.DAILY:
        return now + timedelta(days=1)
    if report.frequency == ReportFrequency.WEEKLY:
        return now + timedelta(weeks=1)
    # monthly
    return now + timedelta(days=30)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    base=BaseTask,
    name="backend.tasks.report_tasks.send_scheduled_reports",
    max_retries=2,
    default_retry_delay=60,
)
def send_scheduled_reports(self) -> dict:
    """
    Check for due scheduled reports and email them.

    Runs hourly (registered via beat_schedule below).
    Returns a summary dict with counts of sent/skipped/failed reports.
    """
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    sent = 0
    skipped = 0
    failed = 0

    try:
        # Find all active reports whose next_send_at has passed
        due_reports = (
            db.query(ScheduledReport)
            .filter(
                ScheduledReport.is_active.is_(True),
                ScheduledReport.next_send_at <= now,
            )
            .all()
        )

        logger.info("Found %d due scheduled reports", len(due_reports))

        for report in due_reports:
            try:
                _send_report(db, report, now)
                sent += 1
            except Exception as exc:
                logger.error(
                    "Failed to send scheduled report %d: %s",
                    report.id,
                    exc,
                    exc_info=True,
                )
                failed += 1
                # Advance next_send_at so we don't get stuck retrying the same window
                report.next_send_at = _next_send_at(report)
                db.commit()

        logger.info(
            "Scheduled report run complete: sent=%d skipped=%d failed=%d",
            sent,
            skipped,
            failed,
        )
        return {"sent": sent, "skipped": skipped, "failed": failed}

    except Exception as exc:
        logger.exception("Unexpected error in send_scheduled_reports: %s", exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


def _send_report(db, report: ScheduledReport, now: datetime) -> None:
    """Generate the HTML/PDF report and email it to all recipients."""
    from backend.notifications import email_notifier

    recipients = report.get_recipients_list()
    if not recipients:
        logger.warning("Report %d has no recipients — skipping", report.id)
        return

    period_label = {1: "Daily", 7: "Weekly", 30: "Monthly"}.get(
        report.period_days, f"{report.period_days}-Day"
    )

    # Generate HTML report (always available; PDF if WeasyPrint is installed)
    service = PDFReportService(db)
    # Always generate the HTML version for the email body
    data = service._gather_report_data(report.organization_id, report.period_days)
    html_body = service._render_html(data, report.name)

    subject = f"UnifiedLayer {period_label} Report — {report.name}"

    # Wrap in a brief intro note
    email_html = (
        f"<p>Your <strong>{period_label}</strong> pipeline activity report "
        f"<em>{report.name}</em> is below.</p>"
        f"<p>This covers the last {report.period_days} day(s) for your organisation.</p>"
        f"<hr/>"
        f"{html_body}"
    )

    try:
        email_notifier.send(
            to_emails=recipients,
            subject=subject,
            body=email_html,
            html=True,
        )
        logger.info("Sent report '%s' to %s", report.name, recipients)
    except Exception as exc:
        logger.error(
            "Failed to email report '%s': %s",
            report.name,
            exc,
        )
        raise

    # Update timestamps after successful send
    report.last_sent_at = now
    report.next_send_at = _next_send_at(report)
    db.commit()
    logger.info(
        "Report %d sent; next scheduled at %s", report.id, report.next_send_at
    )


# ---------------------------------------------------------------------------
# Beat schedule registration (same pattern as health_checks.py)
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule["send-scheduled-reports-hourly"] = {
    "task": "backend.tasks.report_tasks.send_scheduled_reports",
    "schedule": 3600.0,  # Every hour
    "options": {"queue": "default"},
}

# Route report tasks to the default queue
celery_app.conf.task_routes.update({
    "backend.tasks.report_tasks.*": {"queue": "default"},
})
