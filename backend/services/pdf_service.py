"""
PDF Report Generation Service.

Generates styled PDF reports using WeasyPrint from HTML templates.
Falls back to HTML if WeasyPrint is not installed.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.models.pipeline import Organization, Pipeline, PipelineRun

logger = logging.getLogger(__name__)

try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning(
        "weasyprint is not installed. PDF generation will fall back to HTML. "
        "Install with: pip install weasyprint>=60.0"
    )


class PDFReportService:
    """
    Generates pipeline activity PDF reports for an organization.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_pipeline_report(
        self,
        org_id: int,
        period_days: int = 7,
        title: str = "Pipeline Activity Report",
    ) -> bytes:
        """
        Generate a PDF (or HTML fallback) report of pipeline activity.

        Args:
            org_id: Organization ID.
            period_days: Number of days to cover (7 = weekly, 30 = monthly).
            title: Report title shown in the header.

        Returns:
            PDF bytes, or HTML bytes when WeasyPrint is unavailable.
        """
        data = self._gather_report_data(org_id, period_days)
        html = self._render_html(data, title)
        content, is_pdf = self._html_to_pdf(html)
        return content, is_pdf

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _gather_report_data(self, org_id: int, period_days: int) -> dict:
        """Collect all data needed for the report from the database."""
        since = datetime.now(timezone.utc) - timedelta(days=period_days)

        org = (
            self.db.query(Organization)
            .filter(Organization.id == org_id)
            .first()
        )
        if not org:
            logger.warning("generate_pipeline_report called with unknown org_id=%d", org_id)
        org_name = org.name if org else "Unknown Organization"

        # Fetch all pipelines in the org
        pipelines = (
            self.db.query(Pipeline)
            .filter(Pipeline.organization_id == org_id)
            .all()
        )
        pipeline_ids = [p.id for p in pipelines]
        pipeline_map = {p.id: p.name for p in pipelines}

        # Fetch runs within the period
        runs = []
        if pipeline_ids:
            runs = (
                self.db.query(PipelineRun)
                .filter(
                    PipelineRun.pipeline_id.in_(pipeline_ids),
                    PipelineRun.created_at >= since,
                )
                .order_by(PipelineRun.created_at.desc())
                .all()
            )

        total_runs = len(runs)
        completed_runs = [r for r in runs if r.status and r.status.value == "completed"]
        failed_runs = [r for r in runs if r.status and r.status.value == "failed"]

        success_rate = (
            round(len(completed_runs) / total_runs * 100, 1) if total_runs > 0 else 0.0
        )
        total_rows = sum(r.rows_written or 0 for r in completed_runs)

        # Per-pipeline summary
        pipeline_summaries = []
        for p in pipelines:
            p_runs = [r for r in runs if r.pipeline_id == p.id]
            p_completed = [r for r in p_runs if r.status and r.status.value == "completed"]
            p_failed = [r for r in p_runs if r.status and r.status.value == "failed"]
            p_rows = sum(r.rows_written or 0 for r in p_completed)
            avg_dur = (
                round(
                    sum(r.duration_seconds or 0 for r in p_completed) / len(p_completed),
                    1,
                )
                if p_completed
                else None
            )
            pipeline_summaries.append(
                {
                    "name": p.name,
                    "total_runs": len(p_runs),
                    "completed": len(p_completed),
                    "failed": len(p_failed),
                    "rows_synced": p_rows,
                    "avg_duration_s": avg_dur,
                }
            )

        # Recent run rows (up to 50 for the table)
        run_rows = []
        for r in runs[:50]:
            run_rows.append(
                {
                    "pipeline_name": pipeline_map.get(r.pipeline_id, f"Pipeline {r.pipeline_id}"),
                    "status": r.status.value if r.status else "unknown",
                    "rows_synced": r.rows_written or 0,
                    "duration_s": round(r.duration_seconds, 1) if r.duration_seconds else "-",
                    "date": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "-",
                }
            )

        return {
            "org_name": org_name,
            "period_days": period_days,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "total_runs": total_runs,
            "completed_runs": len(completed_runs),
            "failed_runs": len(failed_runs),
            "success_rate": success_rate,
            "total_rows_synced": total_rows,
            "active_pipelines": len([p for p in pipelines if p.is_active]),
            "pipeline_summaries": pipeline_summaries,
            "run_rows": run_rows,
        }

    def _render_html(self, data: dict, title: str) -> str:
        """Render a professional HTML report from the gathered data."""

        # Build pipeline summary rows
        pipeline_rows_html = ""
        for ps in data["pipeline_summaries"]:
            avg_dur_str = f"{ps['avg_duration_s']}s" if ps["avg_duration_s"] is not None else "-"
            pipeline_rows_html += f"""
            <tr>
                <td>{ps['name']}</td>
                <td class="center">{ps['total_runs']}</td>
                <td class="center green">{ps['completed']}</td>
                <td class="center red">{ps['failed']}</td>
                <td class="center">{ps['rows_synced']:,}</td>
                <td class="center">{avg_dur_str}</td>
            </tr>"""

        # Build run history rows
        run_rows_html = ""
        for r in data["run_rows"]:
            status_class = {
                "completed": "badge-success",
                "failed": "badge-danger",
                "running": "badge-info",
            }.get(r["status"], "badge-secondary")
            rows_display = f"{r['rows_synced']:,}" if isinstance(r["rows_synced"], int) else r["rows_synced"]
            run_rows_html += f"""
            <tr>
                <td>{r['pipeline_name']}</td>
                <td class="center"><span class="badge {status_class}">{r['status']}</span></td>
                <td class="center">{rows_display}</td>
                <td class="center">{r['duration_s']}{'s' if r['duration_s'] != '-' else ''}</td>
                <td class="center">{r['date']}</td>
            </tr>"""

        no_runs_msg = (
            '<tr><td colspan="5" class="center muted">No runs in this period</td></tr>'
            if not data["run_rows"]
            else run_rows_html
        )

        period_label = {7: "Last 7 Days", 30: "Last 30 Days"}.get(
            data["period_days"], f"Last {data['period_days']} Days"
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
    color: #1a1a2e;
    background: #fff;
    line-height: 1.5;
  }}
  /* Header */
  .header {{
    background: linear-gradient(135deg, #4c1d95 0%, #7c3aed 60%, #a78bfa 100%);
    color: #fff;
    padding: 32px 40px 28px;
  }}
  .header h1 {{ font-size: 26px; font-weight: 700; letter-spacing: -0.5px; }}
  .header .subtitle {{
    font-size: 13px;
    opacity: 0.85;
    margin-top: 4px;
  }}
  .header .meta {{
    font-size: 11px;
    opacity: 0.7;
    margin-top: 2px;
  }}
  /* Body */
  .body {{ padding: 28px 40px 40px; }}
  /* KPI cards */
  .kpi-row {{
    display: flex;
    gap: 16px;
    margin-bottom: 28px;
    flex-wrap: wrap;
  }}
  .kpi-card {{
    flex: 1;
    min-width: 130px;
    background: #f5f3ff;
    border: 1px solid #ede9fe;
    border-radius: 10px;
    padding: 16px 20px;
  }}
  .kpi-card .label {{ font-size: 11px; color: #7c3aed; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
  .kpi-card .value {{ font-size: 28px; font-weight: 800; color: #1a1a2e; margin-top: 4px; }}
  .kpi-card .sub {{ font-size: 11px; color: #6b7280; margin-top: 2px; }}
  /* Section headings */
  .section-title {{
    font-size: 14px;
    font-weight: 700;
    color: #4c1d95;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 2px solid #ede9fe;
  }}
  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 28px;
    font-size: 12px;
  }}
  thead tr {{ background: #4c1d95; color: #fff; }}
  thead th {{
    padding: 9px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.3px;
  }}
  tbody tr:nth-child(even) {{ background: #f9f9fb; }}
  tbody tr:hover {{ background: #f0ebff; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #ede9fe; }}
  .center {{ text-align: center; }}
  .green {{ color: #059669; font-weight: 600; }}
  .red {{ color: #dc2626; font-weight: 600; }}
  .muted {{ color: #9ca3af; font-style: italic; }}
  /* Badges */
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }}
  .badge-success {{ background: #d1fae5; color: #065f46; }}
  .badge-danger  {{ background: #fee2e2; color: #991b1b; }}
  .badge-info    {{ background: #dbeafe; color: #1d4ed8; }}
  .badge-secondary {{ background: #f3f4f6; color: #4b5563; }}
  /* Footer */
  .footer {{
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #e5e7eb;
    font-size: 10px;
    color: #9ca3af;
    text-align: center;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>UnifiedLayer &mdash; {title}</h1>
  <div class="subtitle">{data['org_name']} &middot; {period_label}</div>
  <div class="meta">Generated: {data['generated_at']}</div>
</div>

<div class="body">

  <!-- KPI Cards -->
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="label">Total Runs</div>
      <div class="value">{data['total_runs']}</div>
      <div class="sub">{period_label}</div>
    </div>
    <div class="kpi-card">
      <div class="label">Success Rate</div>
      <div class="value">{data['success_rate']}%</div>
      <div class="sub">{data['completed_runs']} completed</div>
    </div>
    <div class="kpi-card">
      <div class="label">Rows Synced</div>
      <div class="value">{data['total_rows_synced']:,}</div>
      <div class="sub">Total records</div>
    </div>
    <div class="kpi-card">
      <div class="label">Active Pipelines</div>
      <div class="value">{data['active_pipelines']}</div>
      <div class="sub">Configured</div>
    </div>
  </div>

  <!-- Pipeline Summary -->
  <div class="section-title">Pipeline Summary</div>
  <table>
    <thead>
      <tr>
        <th>Pipeline</th>
        <th class="center">Total Runs</th>
        <th class="center">Completed</th>
        <th class="center">Failed</th>
        <th class="center">Rows Synced</th>
        <th class="center">Avg Duration</th>
      </tr>
    </thead>
    <tbody>
      {''.join(pipeline_rows_html) if data['pipeline_summaries'] else '<tr><td colspan="6" class="center muted">No pipelines found</td></tr>'}
    </tbody>
  </table>

  <!-- Recent Run History -->
  <div class="section-title">Run History (Most Recent 50)</div>
  <table>
    <thead>
      <tr>
        <th>Pipeline</th>
        <th class="center">Status</th>
        <th class="center">Rows Synced</th>
        <th class="center">Duration</th>
        <th class="center">Date (UTC)</th>
      </tr>
    </thead>
    <tbody>
      {no_runs_msg}
    </tbody>
  </table>

  <!-- Data Quality Note -->
  <div class="section-title">Data Quality</div>
  <p style="font-size:12px; color:#4b5563; margin-bottom:16px;">
    This report covers pipeline activity for the selected period.
    Failed runs ({data['failed_runs']}) may indicate connectivity or schema issues in your sources.
    Review individual run logs in the UnifiedLayer dashboard for details.
  </p>

  <div class="footer">
    UnifiedLayer &mdash; Data Integration Platform &middot; report generated automatically &middot; unifiedlayer.io
  </div>

</div>
</body>
</html>"""
        return html

    def _html_to_pdf(self, html: str) -> tuple[bytes, bool]:
        """
        Convert HTML string to PDF bytes via WeasyPrint.

        Returns:
            (content_bytes, is_pdf) — is_pdf=False means the bytes are HTML (fallback).
        """
        if WEASYPRINT_AVAILABLE:
            try:
                return weasyprint.HTML(string=html).write_pdf(), True
            except Exception as exc:
                logger.warning(
                    "WeasyPrint failed at runtime — falling back to HTML: %s", exc
                )
        else:
            logger.warning(
                "WeasyPrint not installed — returning raw HTML bytes instead of PDF."
            )
        return html.encode("utf-8"), False
