"""
Data Source API routes.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import DataSourceCreate, DataSourceUpdate, DataSourceResponse
from backend.models.pipeline import DataSource, User, Pipeline
from backend.auth import get_current_user
from backend.rbac.permissions import require_permission
from backend.services.auto_dashboard_service import get_auto_dashboard_service
import logging

logger = logging.getLogger(__name__)


# Response schema for source creation with auto-dashboard
class AutoDashboardInfo(BaseModel):
    """Auto-dashboard notification info."""
    dashboard_id: str
    template_id: str
    dashboard_name: str
    dashboard_url: str
    title: str
    message: str
    cta: str
    type: str = "auto_dashboard_created"


class DataSourceCreateResponse(BaseModel):
    """Extended response for source creation including auto-dashboard info."""
    source: DataSourceResponse
    auto_dashboard: Optional[AutoDashboardInfo] = None

    class Config:
        from_attributes = True

router = APIRouter(prefix="/sources", tags=["Data Sources"])


@router.get("", response_model=List[DataSourceResponse])
@require_permission("source", "read")
async def list_sources(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: bool = Query(None),
    org_id: Optional[int] = Query(None, description="Organization ID (super admin only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all data sources for the current user's organization.
    Super admins can optionally specify org_id to view another organization's sources.

    **Requires:** source.read permission
    """
    from backend.rbac.audit import log_super_admin_access

    # Determine target organization
    if org_id and current_user.is_super_admin():
        target_org_id = org_id
        # Log super admin cross-org access
        log_super_admin_access(
            db=db,
            super_admin=current_user,
            target_org_id=org_id,
            action="view_sources",
            resource_type="source",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    else:
        target_org_id = current_user.organization_id

    query = db.query(DataSource).filter(
        DataSource.organization_id == target_org_id
    )

    if is_active is not None:
        query = query.filter(DataSource.is_active == is_active)

    sources = query.offset(skip).limit(limit).all()
    return sources


@router.get("/{source_id}", response_model=DataSourceResponse)
@require_permission("source", "read")
async def get_source(
    request: Request,
    source_id: str,
    org_id: Optional[int] = Query(None, description="Organization ID (super admin only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific data source by ID.
    Super admins can optionally specify org_id to view another organization's source.

    **Requires:** source.read permission
    """
    from uuid import UUID
    from backend.rbac.audit import log_super_admin_access

    try:
        source_uuid = UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    # Determine target organization
    if org_id and current_user.is_super_admin():
        target_org_id = org_id
    else:
        target_org_id = current_user.organization_id

    source = db.query(DataSource).filter(
        DataSource.public_id == source_uuid,
        DataSource.organization_id == target_org_id,
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    # Log super admin access if viewing another org
    if org_id and current_user.is_super_admin():
        log_super_admin_access(
            db=db,
            super_admin=current_user,
            target_org_id=org_id,
            action="view_source",
            resource_type="source",
            resource_id=str(source.public_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    return source


@router.post("", response_model=DataSourceCreateResponse, status_code=status.HTTP_201_CREATED)
@require_permission("source", "create")
async def create_source(
    source_data: DataSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new data source.

    If this is the first source of its type, an auto-dashboard may be created
    and returned in the response.

    **Requires:** source.create permission
    """
    if source_data.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create source for different organization",
        )

    # Normalize source_type to uppercase to match database enum
    # Frontend sends: "postgresql", "mysql", "mongodb"
    # Database expects: "POSTGRES", "MYSQL", "MONGODB"
    normalized_source_type = source_data.source_type.upper()

    # Handle special case: postgresql -> POSTGRES
    if normalized_source_type == "POSTGRESQL":
        normalized_source_type = "POSTGRES"

    source = DataSource(
        name=source_data.name,
        description=source_data.description,
        organization_id=source_data.organization_id,
        source_type=normalized_source_type,
        config=source_data.config,
        is_active=True,
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    logger.info(f"Data source created: {source.id} - {source.name}")

    # Try to create auto-dashboard for the new source
    auto_dashboard_info = None
    try:
        auto_dashboard_service = get_auto_dashboard_service(db)

        # Check if we should create an auto-dashboard
        should_create, reason = auto_dashboard_service.should_create_auto_dashboard(
            org_id=current_user.organization_id,
            source_type=source_data.source_type,
        )

        if should_create:
            dashboard = auto_dashboard_service.create_auto_dashboard(
                org_id=current_user.organization_id,
                source=source,
            )

            if dashboard:
                notification = auto_dashboard_service.get_auto_dashboard_notification(dashboard)
                auto_dashboard_info = AutoDashboardInfo(
                    dashboard_id=notification["dashboard_id"],
                    template_id=notification["template_id"],
                    dashboard_name=notification["dashboard_name"],
                    dashboard_url=notification["dashboard_url"],
                    title=notification["title"],
                    message=notification["message"],
                    cta=notification["cta"],
                    type=notification["type"],
                )
                logger.info(
                    f"Auto-dashboard created for source {source.id}: {dashboard['name']}"
                )
        else:
            logger.debug(
                f"Auto-dashboard not created for source {source.id}: {reason}"
            )

    except Exception as e:
        # Don't fail source creation if auto-dashboard creation fails
        logger.warning(
            f"Failed to create auto-dashboard for source {source.id}: {e}"
        )

    return DataSourceCreateResponse(
        source=DataSourceResponse.model_validate(source),
        auto_dashboard=auto_dashboard_info,
    )


@router.put("/{source_id}", response_model=DataSourceResponse)
@require_permission("source", "update")
async def update_source(
    source_id: str,
    source_data: DataSourceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing data source.

    **Requires:** source.update permission
    """
    from uuid import UUID

    try:
        source_uuid = UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    source = db.query(DataSource).filter(
        DataSource.public_id == source_uuid,
        DataSource.organization_id == current_user.organization_id,
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    update_data = source_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)

    logger.info(f"Data source updated: {source.id} - {source.name}")
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("source", "delete")
async def delete_source(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a data source and all dependent pipelines.

    **Requires:** source.delete permission
    """
    from uuid import UUID

    try:
        source_uuid = UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    source = db.query(DataSource).filter(
        DataSource.public_id == source_uuid,
        DataSource.organization_id == current_user.organization_id,
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    # Delete all pipelines that use this source (cascade delete)
    dependent_pipelines = db.query(Pipeline).filter(
        Pipeline.source_id == source.id,  # Use integer ID
        Pipeline.organization_id == current_user.organization_id,
    ).all()

    if dependent_pipelines:
        logger.info(f"Deleting {len(dependent_pipelines)} dependent pipeline(s) for source {source.id}")
        for pipeline in dependent_pipelines:
            db.delete(pipeline)

    db.delete(source)
    db.commit()

    logger.info(f"Data source deleted: {source.id}")
    return None


@router.post("/{source_id}/test")
@require_permission("source", "read")
async def test_source_connection(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test connection to a data source.

    **Requires:** source.read permission
    """
    from uuid import UUID

    try:
        source_uuid = UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    source = db.query(DataSource).filter(
        DataSource.public_id == source_uuid,
        DataSource.organization_id == current_user.organization_id,
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )

    # Test the connection
    logger.info(f"Testing connection for source: {source.id} (type: {source.source_type})")

    from backend.utils.connection_tester import test_connection

    success, message = test_connection(source.source_type.value, source.config)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection test failed: {message}",
        )

    return {
        "source_id": str(source.public_id),  # Return UUID string
        "status": "success",
        "message": message,
    }
