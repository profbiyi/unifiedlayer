"""
Anomaly Detection API Routes.

Provides REST endpoints for querying pipeline anomalies detected by the
AnomalyDetector service.  Data is generated on-demand by running the
detector against the current database state — no separate storage table
is required.

Register in main.py:
    from backend.api.routes.anomaly import router as anomaly_router
    app.include_router(anomaly_router, prefix="/api/v1")
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models.pipeline import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/anomalies", tags=["Anomaly Detection"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AnomalyAlertResponse(BaseModel):
    """Public representation of a detected anomaly."""

    pipeline_id: int
    pipeline_name: str
    org_id: int
    alert_type: str
    severity: str
    message: str
    details: dict

    class Config:
        from_attributes = True


class AnomalySummaryResponse(BaseModel):
    """Paginated list of anomalies with metadata."""

    total: int
    anomalies: List[AnomalyAlertResponse]
    pipeline_id: Optional[int] = None
    message: str = "Anomaly scan complete."


# ---------------------------------------------------------------------------
# Helper: run detector and filter to current org
# ---------------------------------------------------------------------------

def _run_detector_for_org(
    db: Session,
    current_user: User,
    pipeline_id: Optional[int] = None,
) -> List:
    """
    Run the AnomalyDetector and return only results that belong to the
    current user's organisation.  Super-admins see all organisations.

    Args:
        db:           Database session.
        current_user: Authenticated user.
        pipeline_id:  Optionally restrict the scan to a single pipeline.

    Returns:
        List of AnomalyAlert objects.
    """
    from backend.services.anomaly_service import AnomalyDetector

    detector = AnomalyDetector(db)

    if pipeline_id is not None:
        raw_alerts = detector.check_pipeline(pipeline_id)
    else:
        raw_alerts = detector.check_all_pipelines()

    # Non-super-admins are restricted to their own organisation.
    if not current_user.is_super_admin():
        raw_alerts = [
            a for a in raw_alerts if a.org_id == current_user.organization_id
        ]
    # Super-admins see everything.

    return raw_alerts


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=AnomalySummaryResponse,
    summary="List recent anomalies for the organisation",
    description=(
        "Runs the anomaly detector against live pipeline run history and "
        "returns all currently-detected anomalies for the authenticated "
        "user's organisation.  Super-admins see anomalies across all orgs."
    ),
)
async def list_anomalies(
    severity: Optional[str] = Query(
        None,
        description="Filter by severity: 'warning' or 'critical'",
        regex="^(warning|critical)$",
    ),
    alert_type: Optional[str] = Query(
        None,
        description=(
            "Filter by anomaly type: 'row_drop', 'failure_spike', "
            "'slow_sync', or 'zero_rows'"
        ),
        regex="^(row_drop|failure_spike|slow_sync|zero_rows)$",
    ),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnomalySummaryResponse:
    """
    Return all currently-detected anomalies for the caller's organisation.

    The detector is run live — results reflect the current database state.
    For large organisations with many pipelines this call may take a few
    seconds.  Consider calling this endpoint asynchronously from the UI.
    """
    try:
        alerts = _run_detector_for_org(db, current_user)
    except Exception as exc:
        logger.exception("Anomaly scan failed in list_anomalies: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anomaly detection scan failed. See server logs for details.",
        )

    # Apply optional filters.
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    if alert_type:
        alerts = [a for a in alerts if a.alert_type == alert_type]

    total = len(alerts)
    page = alerts[skip : skip + limit]

    return AnomalySummaryResponse(
        total=total,
        anomalies=[
            AnomalyAlertResponse(
                pipeline_id=a.pipeline_id,
                pipeline_name=a.pipeline_name,
                org_id=a.org_id,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                details=a.details,
            )
            for a in page
        ],
        message=f"Found {total} anomal{'y' if total == 1 else 'ies'}.",
    )


@router.get(
    "/{pipeline_id}",
    response_model=AnomalySummaryResponse,
    summary="List anomalies for a specific pipeline",
    description=(
        "Runs the anomaly detector against a single pipeline's run history "
        "and returns all currently-detected anomalies.  Users can only query "
        "pipelines that belong to their organisation."
    ),
)
async def list_pipeline_anomalies(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnomalySummaryResponse:
    """
    Return anomalies for a specific pipeline.

    Args:
        pipeline_id: Integer primary key of the pipeline.
        current_user: Authenticated user; must belong to the same org as the pipeline.
        db: Database session.
    """
    from backend.models.pipeline import Pipeline

    # Verify that the pipeline exists and belongs to the caller's org.
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()

    if pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline id={pipeline_id} not found.",
        )

    if (
        not current_user.is_super_admin()
        and pipeline.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this pipeline.",
        )

    try:
        alerts = _run_detector_for_org(db, current_user, pipeline_id=pipeline_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(
            "Anomaly scan failed for pipeline id=%s: %s", pipeline_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anomaly detection scan failed. See server logs for details.",
        )

    total = len(alerts)

    return AnomalySummaryResponse(
        total=total,
        anomalies=[
            AnomalyAlertResponse(
                pipeline_id=a.pipeline_id,
                pipeline_name=a.pipeline_name,
                org_id=a.org_id,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                details=a.details,
            )
            for a in alerts
        ],
        pipeline_id=pipeline_id,
        message=f"Found {total} anomal{'y' if total == 1 else 'ies'} for pipeline '{pipeline.name}'.",
    )
