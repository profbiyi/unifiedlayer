"""
Scheduled PDF/Email Report Routes.

Provides endpoints for managing automated report schedules and
generating on-demand PDF reports.

Register in main.py:
    from backend.api.routes.reports import router as reports_router
    app.include_router(reports_router, prefix="/api/v1")
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth import require_org_admin
from backend.database import get_db
from backend.models.pipeline import User
from backend.models.scheduled_report import ReportFrequency, ScheduledReport
from backend.services.pdf_service import PDFReportService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class ScheduledReportCreate(BaseModel):
    """Body for POST /reports/scheduled."""

    name: str = Field(..., min_length=1, max_length=200)
    frequency: ReportFrequency = ReportFrequency.WEEKLY
    recipients: List[str] = Field(
        ...,
        min_length=1,
        description="List of recipient email addresses.",
    )
    include_pipelines: bool = True
    include_quality: bool = True


class ScheduledReportUpdate(BaseModel):
    """Body for PUT /reports/scheduled/{id}."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    frequency: Optional[ReportFrequency] = None
    recipients: Optional[List[str]] = None
    is_active: Optional[bool] = None
    include_pipelines: Optional[bool] = None
    include_quality: Optional[bool] = None


class ScheduledReportResponse(BaseModel):
    """Report schedule response schema."""

    id: int
    organization_id: int
    created_by_id: Optional[int]
    name: str
    frequency: ReportFrequency
    recipients: List[str]
    is_active: bool
    include_pipelines: bool
    include_quality: bool
    last_sent_at: Optional[datetime]
    next_send_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj: ScheduledReport) -> "ScheduledReportResponse":
        return cls(
            id=obj.id,
            organization_id=obj.organization_id,
            created_by_id=obj.created_by_id,
            name=obj.name,
            frequency=obj.frequency,
            recipients=obj.get_recipients_list(),
            is_active=obj.is_active,
            include_pipelines=obj.include_pipelines,
            include_quality=obj.include_quality,
            last_sent_at=obj.last_sent_at,
            next_send_at=obj.next_send_at,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class GenerateReportRequest(BaseModel):
    """Body for POST /reports/generate."""

    period_days: int = Field(
        7,
        ge=1,
        le=90,
        description="Number of days to cover (1=daily, 7=weekly, 30=monthly).",
    )
    title: str = Field("Pipeline Activity Report", max_length=200)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _compute_next_send_at(frequency: ReportFrequency) -> datetime:
    """Return the next send time based on frequency starting from now."""
    now = datetime.now(timezone.utc)
    if frequency == ReportFrequency.DAILY:
        return now + timedelta(days=1)
    if frequency == ReportFrequency.WEEKLY:
        return now + timedelta(weeks=1)
    # monthly
    return now + timedelta(days=30)


def _get_report_or_404(
    report_id: int, org_id: int, db: Session
) -> ScheduledReport:
    report = (
        db.query(ScheduledReport)
        .filter(
            ScheduledReport.id == report_id,
            ScheduledReport.organization_id == org_id,
        )
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheduled report {report_id} not found.",
        )
    return report


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/scheduled",
    response_model=List[ScheduledReportResponse],
    summary="List scheduled reports",
)
def list_scheduled_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
) -> List[ScheduledReportResponse]:
    """Return all scheduled reports for the current user's organization."""
    reports = (
        db.query(ScheduledReport)
        .filter(ScheduledReport.organization_id == current_user.organization_id)
        .order_by(ScheduledReport.created_at.desc())
        .all()
    )
    return [ScheduledReportResponse.from_orm_obj(r) for r in reports]


@router.post(
    "/scheduled",
    response_model=ScheduledReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scheduled report",
)
def create_scheduled_report(
    body: ScheduledReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
) -> ScheduledReportResponse:
    """Create a new scheduled PDF report configuration."""
    report = ScheduledReport(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        name=body.name,
        frequency=body.frequency,
        recipients=",".join(body.recipients),
        include_pipelines=body.include_pipelines,
        include_quality=body.include_quality,
        is_active=True,
        next_send_at=_compute_next_send_at(body.frequency),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info(
        "Created scheduled report %d for org %d", report.id, current_user.organization_id
    )
    return ScheduledReportResponse.from_orm_obj(report)


@router.put(
    "/scheduled/{report_id}",
    response_model=ScheduledReportResponse,
    summary="Update a scheduled report",
)
def update_scheduled_report(
    report_id: int,
    body: ScheduledReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
) -> ScheduledReportResponse:
    """Update an existing scheduled report configuration."""
    report = _get_report_or_404(report_id, current_user.organization_id, db)

    if body.name is not None:
        report.name = body.name
    if body.frequency is not None:
        report.frequency = body.frequency
        report.next_send_at = _compute_next_send_at(body.frequency)
    if body.recipients is not None:
        report.recipients = ",".join(body.recipients)
    if body.is_active is not None:
        report.is_active = body.is_active
    if body.include_pipelines is not None:
        report.include_pipelines = body.include_pipelines
    if body.include_quality is not None:
        report.include_quality = body.include_quality

    report.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return ScheduledReportResponse.from_orm_obj(report)


@router.delete(
    "/scheduled/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a scheduled report",
)
def delete_scheduled_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
) -> None:
    """Delete a scheduled report configuration."""
    report = _get_report_or_404(report_id, current_user.organization_id, db)
    db.delete(report)
    db.commit()
    logger.info(
        "Deleted scheduled report %d for org %d", report_id, current_user.organization_id
    )


@router.post(
    "/generate",
    summary="Generate and download a report immediately",
)
def generate_report_now(
    body: GenerateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
) -> Response:
    """
    Generate a PDF report immediately and return it as a download.

    Returns a PDF file if WeasyPrint is installed, otherwise returns HTML.
    """
    service = PDFReportService(db)
    report_bytes, is_pdf = service.generate_pipeline_report(
        org_id=current_user.organization_id,
        period_days=body.period_days,
        title=body.title,
    )

    if is_pdf:
        media_type = "application/pdf"
        filename = f"unifiedlayer-report-{body.period_days}d.pdf"
    else:
        media_type = "text/html; charset=utf-8"
        filename = f"unifiedlayer-report-{body.period_days}d.html"

    return Response(
        content=report_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(report_bytes)),
        },
    )
