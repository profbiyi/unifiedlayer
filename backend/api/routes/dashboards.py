"""
Dashboard API routes.

Provides endpoints for dashboard templates and widget data.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models.pipeline import User
from backend.services.dashboard_service import get_dashboard_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


# ============================================================
# Schemas
# ============================================================

class WidgetConfig(BaseModel):
    metric: Optional[str] = None
    format: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    color: Optional[str] = None


class WidgetSummary(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None


class TemplateSummary(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    required_sources: List[str]
    preview_image: Optional[str] = None
    widget_count: int
    available: Optional[bool] = None


class TemplateRequirements(BaseModel):
    can_use: bool
    connected_sources: List[str]
    missing_sources: List[str]
    required_sources: List[str]


class DashboardDataRequest(BaseModel):
    source_type: Optional[str] = None


# ============================================================
# Endpoints
# ============================================================

@router.get("/templates", response_model=List[TemplateSummary])
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all dashboard templates with availability status.

    Templates are marked as available if any of their required sources
    are connected to the organization.
    """
    service = get_dashboard_service(db)
    templates = service.get_available_templates(current_user.organization_id)
    return templates


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get full template details including widget definitions.
    """
    service = get_dashboard_service(db)
    template = service.get_template_details(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Add availability info
    requirements = service.check_template_requirements(
        current_user.organization_id,
        template_id,
    )
    template["requirements"] = requirements

    return template


@router.get("/templates/{template_id}/requirements", response_model=TemplateRequirements)
async def check_template_requirements(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check what sources are needed to use a template.
    """
    service = get_dashboard_service(db)
    requirements = service.check_template_requirements(
        current_user.organization_id,
        template_id,
    )

    if "error" in requirements:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=requirements["error"],
        )

    return requirements


@router.get("/templates/{template_id}/data")
async def get_dashboard_data(
    template_id: str,
    source_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get dashboard with populated widget data.

    Executes all widget SQL queries and returns results.

    Args:
        template_id: Dashboard template ID
        source_type: Optional source type to use (defaults to first compatible)
    """
    service = get_dashboard_service(db)

    # Check requirements first
    requirements = service.check_template_requirements(
        current_user.organization_id,
        template_id,
    )

    if "error" in requirements:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=requirements["error"],
        )

    if not requirements["can_use"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required sources: {', '.join(requirements['missing_sources'])}",
        )

    # Get dashboard data
    data = service.get_dashboard_data(
        org_id=current_user.organization_id,
        template_id=template_id,
        source_type=source_type,
    )

    if "error" in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=data["error"],
        )

    return data


@router.post("/templates/{template_id}/refresh")
async def refresh_dashboard_data(
    template_id: str,
    request: DashboardDataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Refresh all widget data for a dashboard.

    Same as GET /data but allows POST for explicit refresh action.
    """
    return await get_dashboard_data(
        template_id=template_id,
        source_type=request.source_type,
        current_user=current_user,
        db=db,
    )
