"""
Business Summary API Routes.

Provides endpoints to generate AI business summaries on demand
and manage summary delivery preferences.

Register in main.py:
    from backend.api.routes.summaries import router as summaries_router
    app.include_router(summaries_router, prefix="/api/v1")
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth import require_org_admin
from backend.database import get_db
from backend.models.pipeline import User
from backend.services.summary_service import get_summary_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/summaries", tags=["Summaries"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SummaryGenerateRequest(BaseModel):
    frequency: str = Field(
        default="weekly",
        description='Summary period: "weekly" (last 7 days) or "daily" (last 24 hours)',
    )
    send_email: bool = Field(
        default=False,
        description="If True, also email the summary to all org admins",
    )


class SummaryGenerateResponse(BaseModel):
    summary: str = Field(description="Generated plain-English summary text")
    frequency: str
    email_sent: Optional[bool] = Field(
        default=None,
        description="True/False if send_email was requested; None otherwise",
    )
    org_id: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=SummaryGenerateResponse)
async def generate_summary(
    request: SummaryGenerateRequest,
    current_user: User = Depends(require_org_admin),
    db: Session = Depends(get_db),
):
    """
    Generate an AI business summary for the current organization.

    Requires: org_admin or super_admin role.

    - **frequency**: "weekly" (default) covers the last 7 days;
      "daily" covers the last 24 hours.
    - **send_email**: When True, the summary is also emailed to all org admins
      in the background. Email is dispatched as a Celery task so the HTTP
      response returns immediately.

    Returns the generated summary text alongside email delivery status.
    """
    frequency = request.frequency.lower()
    if frequency not in ("weekly", "daily"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='frequency must be "weekly" or "daily"',
        )

    org_id = current_user.organization_id
    service = get_summary_service(db)

    try:
        if frequency == "daily":
            summary_text = service.generate_daily_summary(org_id)
        else:
            summary_text = service.generate_weekly_summary(org_id)
    except Exception as exc:
        logger.error(f"Summary generation failed for org {org_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary. Please try again.",
        )

    email_sent: Optional[bool] = None

    if request.send_email:
        # Dispatch email as a background Celery task to avoid blocking the
        # HTTP response on SMTP latency.
        try:
            from backend.tasks.summary_tasks import send_org_summary
            send_org_summary.delay(org_id=org_id, frequency=frequency)
            email_sent = True  # task dispatched (actual delivery is async)
            logger.info(
                f"Summary email task dispatched for org {org_id} ({frequency})"
            )
        except Exception as exc:
            # Celery might not be running in dev — degrade gracefully
            logger.warning(
                f"Could not dispatch summary email task (Celery may be down): {exc}. "
                "Attempting synchronous send as fallback."
            )
            try:
                email_sent = service.send_summary_email(org_id=org_id, frequency=frequency)
            except Exception as email_exc:
                logger.error(f"Synchronous summary email also failed: {email_exc}")
                email_sent = False

    return SummaryGenerateResponse(
        summary=summary_text,
        frequency=frequency,
        email_sent=email_sent,
        org_id=org_id,
    )


@router.get("/preview")
async def preview_summary_stats(
    frequency: str = "weekly",
    current_user: User = Depends(require_org_admin),
    db: Session = Depends(get_db),
):
    """
    Return the raw pipeline statistics used to generate a summary.

    Useful for debugging or building custom summary UIs. Does not call OpenAI.

    Query param:
      - **frequency**: "weekly" (last 7 days) or "daily" (last 24 hours)
    """
    frequency = frequency.lower()
    if frequency not in ("weekly", "daily"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='frequency must be "weekly" or "daily"',
        )

    days = 7 if frequency == "weekly" else 1
    service = get_summary_service(db)
    stats = service._gather_pipeline_stats(current_user.organization_id, days=days)

    return {
        "org_id": current_user.organization_id,
        "frequency": frequency,
        "period_days": days,
        "stats": stats,
    }
