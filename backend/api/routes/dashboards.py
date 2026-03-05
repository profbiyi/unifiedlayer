"""
Dashboard API routes.

Provides endpoints for dashboard templates, widget data, and
industry-specific pre-built dashboards (Feature B).

Register in main.py:
    from backend.api.routes.dashboards import router as dashboards_router
    app.include_router(dashboards_router, prefix="/api/v1")
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models.pipeline import User
from backend.services.dashboard_service import get_dashboard_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


# ============================================================
# Schemas — existing
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
# Schemas — Feature B: industry templates
# ============================================================

class IndustryTemplateSummary(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    industry: str
    target_connectors: List[str]
    recommended_for_source_types: List[str]
    widget_count: int


class IndustryDashboardCreateRequest(BaseModel):
    template_id: str = Field(
        description='Industry template ID, e.g. "ecommerce", "saas_startup"'
    )
    data_source_id: int = Field(
        description="ID of the connected DataSource whose connector type drives table name resolution"
    )


class IndustryDashboardResponse(BaseModel):
    id: str
    name: str
    description: str
    industry: str
    org_id: int
    data_source_id: int
    source_type: str
    widget_count: int
    instantiated_at: str
    widgets: list


class TemplateRecommendationResponse(BaseModel):
    recommended_template_id: Optional[str] = Field(
        description="Best-matching industry template ID, or null if no match"
    )
    reason: str


# ============================================================
# Existing endpoints
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


# ============================================================
# Feature B: Industry-specific dashboard template endpoints
# ============================================================

@router.get("/industry-templates", response_model=List[IndustryTemplateSummary])
async def list_industry_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all available industry-specific pre-built dashboard templates.

    Returns five templates covering:
    - **ecommerce** — E-commerce & Retail
    - **food_beverage** — Food & Beverage (Restaurant)
    - **fintech_payments** — Fintech & Payments
    - **professional_services** — Professional Services (Agency/Consulting)
    - **saas_startup** — SaaS & Tech Startup

    Each template defines widgets (KPIs, charts, tables) with SQL templates
    that are resolved to your actual destination table names when you call
    `POST /dashboards/from-industry-template`.
    """
    service = get_dashboard_service(db)
    return service.get_industry_templates()


@router.post("/from-industry-template", response_model=IndustryDashboardResponse)
async def create_from_industry_template(
    request: IndustryDashboardCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Instantiate an industry dashboard template for this organization.

    Takes a template ID and a connected data source ID, then resolves all
    SQL placeholder table names (e.g. `{transactions_table}`) to the actual
    destination table names used by the source's connector.

    Body:
    - **template_id**: e.g. `"ecommerce"`, `"saas_startup"`
    - **data_source_id**: ID of the DataSource (must belong to this org)

    Returns the fully-instantiated dashboard object including all widget
    SQL queries ready to be executed. The dashboard is **not** persisted
    to the database by this call — it is returned for the client to display
    or further store as needed.
    """
    service = get_dashboard_service(db)

    try:
        dashboard = service.create_dashboard_from_industry_template(
            org_id=current_user.organization_id,
            template_id=request.template_id,
            data_source_id=request.data_source_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(
            f"Failed to create industry dashboard for org {current_user.organization_id}: {exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to instantiate industry dashboard template.",
        )

    return IndustryDashboardResponse(
        id=dashboard["id"],
        name=dashboard["name"],
        description=dashboard["description"],
        industry=dashboard.get("industry", ""),
        org_id=dashboard["org_id"],
        data_source_id=dashboard["data_source_id"],
        source_type=dashboard["source_type"],
        widget_count=len(dashboard.get("widgets", [])),
        instantiated_at=dashboard.get("instantiated_at", ""),
        widgets=dashboard.get("widgets", []),
    )


@router.get("/recommend-template", response_model=TemplateRecommendationResponse)
async def recommend_industry_template(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Recommend the best-matching industry dashboard template for this organization.

    Examines the org's connected data sources and scores each industry template
    based on how many of its preferred connector types match. Returns the
    top-scoring template ID (or null if no sources are connected).

    Example response:
    ```json
    {
      "recommended_template_id": "ecommerce",
      "reason": "Your connected sources (Stripe, Paystack) match the E-commerce & Retail template."
    }
    ```
    """
    service = get_dashboard_service(db)
    template_id = service.recommend_industry_template(current_user.organization_id)

    if template_id is None:
        return TemplateRecommendationResponse(
            recommended_template_id=None,
            reason=(
                "No connected sources found. Connect a data source and we will "
                "recommend the best dashboard template for your business."
            ),
        )

    # Look up the template name for a friendly reason string
    from backend.templates.dashboard_templates import get_industry_template_by_id
    tmpl = get_industry_template_by_id(template_id)
    name = tmpl["name"] if tmpl else template_id

    return TemplateRecommendationResponse(
        recommended_template_id=template_id,
        reason=(
            f"Based on your connected data sources, the '{name}' template "
            "is the best match for your business."
        ),
    )
