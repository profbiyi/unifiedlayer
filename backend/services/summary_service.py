"""
AI Business Summary Service.

Generates plain-English business summaries from pipeline activity and data,
then delivers them via email. Summaries cover pipeline health, rows synced,
and top-level operational KPIs.

If OpenAI is unavailable the service falls back to a deterministic
template-based summary that contains the same underlying numbers.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from backend.config import settings
from backend.services.openai_helper import chat_completion
from backend.models.pipeline import (
    Organization,
    Pipeline,
    PipelineRun,
    PipelineStatus,
    User,
)
from backend.notifications import EmailNotifier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _percent_change(current: float, previous: float) -> Optional[float]:
    """Return percentage change between two values, or None if previous is 0."""
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _format_rows(n: int) -> str:
    """Human-friendly row count string (e.g. '12,847')."""
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Main service class
# ---------------------------------------------------------------------------

class BusinessSummaryService:
    """
    Service that generates and emails AI-powered (or template-based) business
    summaries for a given organization.

    Usage
    -----
    service = BusinessSummaryService(db)
    text    = service.generate_weekly_summary(org_id=42)
    sent    = service.send_summary_email(org_id=42, frequency="weekly")
    """

    def __init__(self, db: Session) -> None:
        self.db = db

        # Initialise OpenAI client (gracefully degrade if key missing)
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if api_key:
            self.openai_client: Optional[OpenAI] = OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            logger.warning(
                "OPENAI_API_KEY not set — AI summaries will use template fallback"
            )

        self.openai_model: str = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        self._email_notifier = EmailNotifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_weekly_summary(self, org_id: int) -> str:
        """
        Generate a plain-English weekly summary for an organization.

        Gathers pipeline statistics for the past 7 days and compares them
        to the 7 days prior (for trend context).

        Returns a 1-3 paragraph string ready to be emailed or displayed in-app.
        """
        org = self._get_org(org_id)
        if org is None:
            return "Organization not found."

        stats = self._gather_pipeline_stats(org_id, days=7)
        prompt = self._build_prompt(org.name, stats, period="last week")
        return self._call_openai(prompt) or self._template_summary(org.name, stats, period="last week")

    def generate_daily_summary(self, org_id: int) -> str:
        """
        Generate a shorter plain-English daily digest for an organization.

        Covers the past 24 hours vs. the previous 24-hour window.
        """
        org = self._get_org(org_id)
        if org is None:
            return "Organization not found."

        stats = self._gather_pipeline_stats(org_id, days=1)
        prompt = self._build_prompt(org.name, stats, period="today")
        return self._call_openai(prompt) or self._template_summary(org.name, stats, period="today")

    def send_summary_email(self, org_id: int, frequency: str = "weekly") -> bool:
        """
        Generate a summary and email it to all active org admins.

        Args:
            org_id:    Target organization ID.
            frequency: "weekly" or "daily".

        Returns:
            True if at least one email was dispatched successfully.
        """
        org = self._get_org(org_id)
        if org is None:
            logger.error(f"Cannot send summary email — org {org_id} not found")
            return False

        if frequency == "daily":
            summary_text = self.generate_daily_summary(org_id)
            subject_prefix = "Daily"
        else:
            summary_text = self.generate_weekly_summary(org_id)
            subject_prefix = "Weekly"

        # Gather admin email addresses
        admin_emails = self._get_admin_emails(org_id)
        if not admin_emails:
            logger.warning(f"No admin emails found for org {org_id} — skipping summary email")
            return False

        subject = f"[UnifiedLayer] Your {subject_prefix} Business Summary — {org.name}"
        html_body = self._build_email_html(
            org_name=org.name,
            summary_text=summary_text,
            frequency=subject_prefix,
            primary_color=org.brand_primary_color or "#6366f1",
            secondary_color=org.brand_secondary_color or "#8b5cf6",
            logo_url=org.logo_url,
        )

        try:
            success = self._email_notifier.send(
                to_emails=admin_emails,
                subject=subject,
                body=html_body,
                html=True,
            )
            if success:
                logger.info(
                    f"{subject_prefix} summary emailed to {len(admin_emails)} admin(s) "
                    f"for org {org_id} ({org.name})"
                )
            return bool(success)
        except Exception as exc:
            logger.error(f"Failed to send summary email for org {org_id}: {exc}")
            return False

    # ------------------------------------------------------------------
    # Data gathering
    # ------------------------------------------------------------------

    def _gather_pipeline_stats(self, org_id: int, days: int) -> Dict[str, Any]:
        """
        Gather pipeline execution statistics for the given window.

        Returns a dict with:
          - period_days          int
          - pipeline_count       int
          - total_runs           int
          - successful_runs      int
          - failed_runs          int
          - success_rate_pct     float (0-100)
          - total_rows_synced    int
          - prev_rows_synced     int
          - row_change_pct       Optional[float]
          - avg_duration_seconds float
          - failure_details      List[dict] — up to 5 most recent failures
          - busiest_day          Optional[str] — weekday with most failures
          - active_pipelines     List[str] — pipeline names
          - source_types         List[str] — unique source connector types
        """
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=days)
        prev_period_start = period_start - timedelta(days=days)

        # All pipelines for the org
        pipelines = (
            self.db.query(Pipeline)
            .filter(
                Pipeline.organization_id == org_id,
                Pipeline.is_active == True,  # noqa: E712
            )
            .all()
        )
        pipeline_ids = [p.id for p in pipelines]
        pipeline_names = [p.name for p in pipelines]

        if not pipeline_ids:
            return self._empty_stats(days)

        # Current period runs
        current_runs = (
            self.db.query(PipelineRun)
            .filter(
                PipelineRun.pipeline_id.in_(pipeline_ids),
                PipelineRun.created_at >= period_start,
            )
            .all()
        )

        # Previous period runs (for trend)
        prev_runs = (
            self.db.query(PipelineRun)
            .filter(
                PipelineRun.pipeline_id.in_(pipeline_ids),
                PipelineRun.created_at >= prev_period_start,
                PipelineRun.created_at < period_start,
            )
            .all()
        )

        # Aggregate current period
        successful = [r for r in current_runs if r.status == PipelineStatus.COMPLETED]
        failed = [r for r in current_runs if r.status == PipelineStatus.FAILED]

        total_runs = len(current_runs)
        successful_count = len(successful)
        failed_count = len(failed)
        success_rate = (successful_count / total_runs * 100) if total_runs else 0.0

        total_rows = sum(r.rows_written or 0 for r in current_runs)
        prev_rows = sum(r.rows_written or 0 for r in prev_runs)
        row_change_pct = _percent_change(total_rows, prev_rows)

        durations = [r.duration_seconds for r in current_runs if r.duration_seconds is not None]
        avg_duration = (sum(durations) / len(durations)) if durations else 0.0

        # Recent failure details (up to 5)
        failure_details = []
        for run in sorted(failed, key=lambda r: r.created_at, reverse=True)[:5]:
            # Resolve pipeline name
            pipeline = next((p for p in pipelines if p.id == run.pipeline_id), None)
            failure_details.append({
                "pipeline_name": pipeline.name if pipeline else f"Pipeline #{run.pipeline_id}",
                "failed_at": run.created_at.strftime("%A %b %d at %H:%M UTC") if run.created_at else "unknown",
                "error": (run.error_message or "Unknown error")[:200],
            })

        # Detect busiest failure day
        busiest_day: Optional[str] = None
        if failed:
            day_counts: Dict[str, int] = {}
            for run in failed:
                if run.created_at:
                    day_name = run.created_at.strftime("%A")
                    day_counts[day_name] = day_counts.get(day_name, 0) + 1
            if day_counts:
                busiest_day = max(day_counts, key=lambda d: day_counts[d])

        # Unique source types
        source_type_set: set = set()
        for p in pipelines:
            if p.source and p.source.source_type:
                source_type_set.add(str(p.source.source_type.value).replace("_", " ").title())

        return {
            "period_days": days,
            "pipeline_count": len(pipelines),
            "active_pipelines": pipeline_names,
            "source_types": sorted(source_type_set),
            "total_runs": total_runs,
            "successful_runs": successful_count,
            "failed_runs": failed_count,
            "success_rate_pct": round(success_rate, 1),
            "total_rows_synced": total_rows,
            "prev_rows_synced": prev_rows,
            "row_change_pct": row_change_pct,
            "avg_duration_seconds": round(avg_duration, 1),
            "failure_details": failure_details,
            "busiest_failure_day": busiest_day,
        }

    @staticmethod
    def _empty_stats(days: int) -> Dict[str, Any]:
        return {
            "period_days": days,
            "pipeline_count": 0,
            "active_pipelines": [],
            "source_types": [],
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "success_rate_pct": 0.0,
            "total_rows_synced": 0,
            "prev_rows_synced": 0,
            "row_change_pct": None,
            "avg_duration_seconds": 0.0,
            "failure_details": [],
            "busiest_failure_day": None,
        }

    # ------------------------------------------------------------------
    # OpenAI integration
    # ------------------------------------------------------------------

    def _build_prompt(self, org_name: str, stats: Dict[str, Any], period: str) -> str:
        """
        Build a concise but information-rich prompt for the LLM.

        The prompt instructs the model to produce 1-3 plain-English paragraphs
        suitable for a non-technical business owner.
        """
        rows_synced = _format_rows(stats["total_rows_synced"])
        source_list = ", ".join(stats["source_types"]) if stats["source_types"] else "various sources"
        row_trend = (
            f"up {stats['row_change_pct']}% from the previous period"
            if stats.get("row_change_pct") and stats["row_change_pct"] > 0
            else (
                f"down {abs(stats['row_change_pct'])}% from the previous period"
                if stats.get("row_change_pct") and stats["row_change_pct"] < 0
                else "roughly the same as the previous period"
            )
        )

        failure_block = ""
        if stats["failure_details"]:
            failure_lines = "\n".join(
                f"  - {d['pipeline_name']} failed on {d['failed_at']}: {d['error']}"
                for d in stats["failure_details"]
            )
            failure_block = f"\nRecent failures:\n{failure_lines}"
            if stats["busiest_failure_day"]:
                failure_block += f"\nMost failures occurred on {stats['busiest_failure_day']}s."

        prompt = f"""You are writing a friendly, plain-English business summary email for the CEO of {org_name}.

Here are the data platform stats for {period}:
- Active pipelines: {stats['pipeline_count']} ({', '.join(stats['active_pipelines'][:5]) or 'none'})
- Data sources: {source_list}
- Total pipeline runs: {stats['total_runs']}
- Successful runs: {stats['successful_runs']} ({stats['success_rate_pct']}% success rate)
- Failed runs: {stats['failed_runs']}
- Total rows synced: {rows_synced} ({row_trend})
- Average pipeline duration: {stats['avg_duration_seconds']}s
{failure_block}

Write a clear, friendly summary in 1-3 short paragraphs. Avoid jargon. Highlight:
1. Overall health (good/concerning/needs attention).
2. Key stats in natural language (mention the row count and success rate).
3. Any pipeline failures — what went wrong and when.
4. One actionable suggestion if there were failures or low sync volume.

Do not include greetings, sign-offs, or markdown. Plain text only."""
        return prompt

    def _call_openai(self, prompt: str) -> Optional[str]:
        """
        Call the OpenAI chat completions API and return the assistant's reply.

        Returns None if OpenAI is unavailable or the call fails so the caller
        can fall back to the template-based summary.
        """
        if not self.openai_client:
            return None

        try:
            response = chat_completion(self.openai_client,
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a concise, plain-English business analyst writing "
                            "email summaries for SME owners. Be warm, clear, and helpful."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,  # balanced: readable but not hallucinating numbers
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.warning(f"OpenAI summary generation failed (falling back to template): {exc}")
            return None

    # ------------------------------------------------------------------
    # Template fallback (no OpenAI)
    # ------------------------------------------------------------------

    def _template_summary(
        self, org_name: str, stats: Dict[str, Any], period: str
    ) -> str:
        """
        Deterministic template-based summary used when OpenAI is unavailable.

        Produces a 2-3 paragraph plain-English text using only the raw stats.
        """
        rows = _format_rows(stats["total_rows_synced"])
        total = stats["total_runs"]
        succeeded = stats["successful_runs"]
        failed = stats["failed_runs"]
        rate = stats["success_rate_pct"]
        pipelines = stats["pipeline_count"]
        sources = (
            ", ".join(stats["source_types"]) if stats["source_types"] else "your connected sources"
        )

        # Overall health phrase
        if rate >= 95:
            health = "running smoothly"
        elif rate >= 80:
            health = "performing well with a few hiccups"
        elif rate >= 60:
            health = "showing some reliability issues that need attention"
        else:
            health = "experiencing significant problems that require immediate attention"

        para1 = (
            f"{period.capitalize()}, your {pipelines} active pipeline(s) on UnifiedLayer "
            f"were {health}. They completed {total} run(s) in total — "
            f"{succeeded} succeeded and {failed} failed — giving a {rate}% success rate."
        )

        row_trend = ""
        if stats.get("row_change_pct") is not None:
            direction = "up" if stats["row_change_pct"] >= 0 else "down"
            row_trend = f", {direction} {abs(stats['row_change_pct'])}% versus the previous period"

        para2 = (
            f"Your pipelines synced {rows} rows from {sources}{row_trend}. "
            f"Average pipeline run time was {stats['avg_duration_seconds']}s."
        )

        paras = [para1, para2]

        if stats["failure_details"]:
            names = list({d["pipeline_name"] for d in stats["failure_details"]})
            pipeline_list = ", ".join(f'"{n}"' for n in names[:3])
            para3 = (
                f"The following pipeline(s) had failures: {pipeline_list}. "
                "Please log in to UnifiedLayer to review the error logs and re-trigger "
                "any affected runs."
            )
            if stats["busiest_failure_day"]:
                para3 += f" Most failures happened on {stats['busiest_failure_day']}s."
            paras.append(para3)

        return "\n\n".join(paras)

    # ------------------------------------------------------------------
    # Email HTML builder
    # ------------------------------------------------------------------

    def _build_email_html(
        self,
        org_name: str,
        summary_text: str,
        frequency: str,
        primary_color: str = "#6366f1",
        secondary_color: str = "#8b5cf6",
        logo_url: Optional[str] = None,
        organization_name: Optional[str] = None,
    ) -> str:
        """
        Wrap the plain-text summary in a branded HTML email using
        EmailNotifier.get_branded_template().
        """
        # Convert plain-text paragraphs to HTML <p> tags
        paragraphs_html = "\n".join(
            f'<p style="color:#374151;font-size:16px;line-height:1.7;margin:0 0 18px 0;">{p}</p>'
            for p in summary_text.split("\n\n")
            if p.strip()
        )

        content = f"""
            <p style="color:#64748b;font-size:13px;text-transform:uppercase;letter-spacing:1px;
                       font-weight:600;margin:0 0 24px 0;">
                {frequency} Business Summary
            </p>
            {paragraphs_html}
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                   style="margin-top:32px;border-top:1px solid #e2e8f0;padding-top:24px;">
                <tr>
                    <td>
                        <a href="{settings.FRONTEND_URL}/overview"
                           style="display:inline-block;background:linear-gradient(135deg,{primary_color} 0%,{secondary_color} 100%);
                                  color:#ffffff;text-decoration:none;padding:12px 32px;border-radius:8px;
                                  font-size:14px;font-weight:600;">
                            View Dashboard &rarr;
                        </a>
                    </td>
                </tr>
            </table>
            <p style="color:#9ca3af;font-size:12px;margin-top:24px;">
                You are receiving this because you are an admin of
                <strong>{org_name}</strong> on UnifiedLayer.
                To unsubscribe from digest emails, visit your
                <a href="{settings.FRONTEND_URL}/settings"
                   style="color:{primary_color};">notification settings</a>.
            </p>
        """

        return self._email_notifier.get_branded_template(
            content=content,
            header_title=f"Your {frequency} Summary",
            header_subtitle=org_name,
            brand_primary_color=primary_color,
            brand_secondary_color=secondary_color,
            logo_url=logo_url,
            organization_name=organization_name or org_name,
        )

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _get_org(self, org_id: int) -> Optional[Organization]:
        return (
            self.db.query(Organization)
            .filter(Organization.id == org_id, Organization.is_active == True)  # noqa: E712
            .first()
        )

    def _get_admin_emails(self, org_id: int) -> List[str]:
        """Return email addresses of all active admins in the organization."""
        users = (
            self.db.query(User)
            .filter(
                User.organization_id == org_id,
                User.is_active == True,  # noqa: E712
                User.email_verified == True,  # noqa: E712
            )
            .all()
        )
        # Include org admins and super admins who belong to the org
        return [
            u.email
            for u in users
            if u.is_org_admin(org_id) or u.is_super_admin()
        ]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_summary_service(db: Session) -> BusinessSummaryService:
    """FastAPI dependency factory for BusinessSummaryService."""
    return BusinessSummaryService(db)
