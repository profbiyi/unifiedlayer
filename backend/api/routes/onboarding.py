"""
Onboarding API routes.

Provides endpoints for the onboarding wizard and progress tracking.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models.pipeline import User
from backend.models.onboarding import UserRole, OnboardingStatus
from backend.services.onboarding_service import get_onboarding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# ============================================================
# Schemas
# ============================================================

class SetRoleRequest(BaseModel):
    role: str  # founder, finance, operations, sales, developer, other


class SkipOnboardingRequest(BaseModel):
    reason: Optional[str] = None


class MarkStepRequest(BaseModel):
    step: str  # role_selected, first_source_connected, etc.


class SourceRecommendation(BaseModel):
    type: str
    name: str
    reason: str
    priority: int


class ChecklistItem(BaseModel):
    id: str
    title: str
    description: str
    completed: bool
    href: str


class OnboardingStatusResponse(BaseModel):
    status: str
    completion_percentage: int
    next_step: str
    business_role: Optional[str]
    checklist: List[ChecklistItem]


class RoleOption(BaseModel):
    value: str
    label: str
    description: str
    icon: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/roles", response_model=List[RoleOption])
async def get_role_options():
    """
    Get available role options for onboarding.
    """
    return [
        RoleOption(
            value="founder",
            label="Founder / CEO",
            description="Track revenue, growth metrics, and overall business health",
            icon="rocket",
        ),
        RoleOption(
            value="finance",
            label="Finance / Accounting",
            description="Monitor cash flow, invoices, and financial reconciliation",
            icon="calculator",
        ),
        RoleOption(
            value="operations",
            label="Operations",
            description="Sync operational data and track business processes",
            icon="settings",
        ),
        RoleOption(
            value="sales",
            label="Sales",
            description="Analyze sales performance and customer metrics",
            icon="trending-up",
        ),
        RoleOption(
            value="developer",
            label="Developer / Data Engineer",
            description="Set up data infrastructure and pipelines",
            icon="code",
        ),
        RoleOption(
            value="other",
            label="Other",
            description="Get a general overview of all features",
            icon="user",
        ),
    ]


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current user's onboarding status and checklist.
    """
    service = get_onboarding_service(db)
    return service.get_checklist(current_user.id, current_user.organization_id)


@router.post("/role")
async def set_role(
    request: SetRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Set the user's business role for personalized onboarding.
    """
    try:
        role = UserRole(request.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join([r.value for r in UserRole])}",
        )

    service = get_onboarding_service(db)
    progress = service.set_role(
        user_id=current_user.id,
        org_id=current_user.organization_id,
        role=role,
    )

    return {
        "message": "Role set successfully",
        "role": role.value,
        "status": progress.status.value,
    }


@router.get("/recommendations/sources", response_model=List[SourceRecommendation])
async def get_source_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get recommended data sources based on user's role.
    """
    service = get_onboarding_service(db)
    return service.get_source_recommendations(current_user.id)


@router.get("/recommendations/dashboards")
async def get_dashboard_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get recommended dashboard templates based on user's role.
    """
    service = get_onboarding_service(db)
    dashboard_ids = service.get_dashboard_recommendations(current_user.id)

    return {
        "dashboard_ids": dashboard_ids,
    }


@router.post("/step")
async def mark_step_complete(
    request: MarkStepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark an onboarding step as complete.
    """
    service = get_onboarding_service(db)
    progress = service.mark_step_complete(current_user.id, request.step)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding progress not found",
        )

    return {
        "message": "Step marked complete",
        "step": request.step,
        "completion_percentage": progress.completion_percentage,
        "status": progress.status.value,
    }


@router.post("/skip")
async def skip_onboarding(
    request: SkipOnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Skip the onboarding flow.
    """
    service = get_onboarding_service(db)
    progress = service.skip_onboarding(current_user.id, request.reason)

    if not progress:
        # Create progress first
        progress = service.get_or_create_progress(
            current_user.id,
            current_user.organization_id,
        )
        progress = service.skip_onboarding(current_user.id, request.reason)

    return {
        "message": "Onboarding skipped",
        "status": progress.status.value,
    }


@router.post("/sync")
async def sync_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sync onboarding progress based on actual data in the system.

    Useful for users who set up data before completing onboarding.
    """
    service = get_onboarding_service(db)
    progress = service.sync_progress_from_data(
        current_user.id,
        current_user.organization_id,
    )

    return {
        "message": "Progress synced",
        "completion_percentage": progress.completion_percentage,
        "status": progress.status.value,
    }
