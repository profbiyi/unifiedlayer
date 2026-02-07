"""
Destination API routes.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import DestinationCreate, DestinationUpdate, DestinationResponse
from backend.models.pipeline import Destination, User, Pipeline
from backend.auth import get_current_user
from backend.rbac.permissions import require_permission
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/destinations", tags=["Destinations"])


@router.get("", response_model=List[DestinationResponse])
@require_permission("destination", "read")
async def list_destinations(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: bool = Query(None),
    org_id: Optional[int] = Query(None, description="Organization ID (super admin only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all destinations for the current user's organization.
    Super admins can optionally specify org_id to view another organization's destinations.

    **Requires:** destination.read permission
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
            action="view_destinations",
            resource_type="destination",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    else:
        target_org_id = current_user.organization_id

    query = db.query(Destination).filter(
        Destination.organization_id == target_org_id
    )

    if is_active is not None:
        query = query.filter(Destination.is_active == is_active)

    destinations = query.offset(skip).limit(limit).all()
    return destinations


@router.get("/{destination_id}", response_model=DestinationResponse)
@require_permission("destination", "read")
async def get_destination(
    request: Request,
    destination_id: str,
    org_id: Optional[int] = Query(None, description="Organization ID (super admin only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific destination by ID.
    Super admins can optionally specify org_id to view another organization's destination.

    **Requires:** destination.read permission
    """
    from uuid import UUID
    from backend.rbac.audit import log_super_admin_access

    try:
        destination_uuid = UUID(destination_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid destination ID format",
        )

    # Determine target organization
    if org_id and current_user.is_super_admin():
        target_org_id = org_id
    else:
        target_org_id = current_user.organization_id

    destination = db.query(Destination).filter(
        Destination.public_id == destination_uuid,
        Destination.organization_id == target_org_id,
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found",
        )

    # Log super admin access if viewing another org
    if org_id and current_user.is_super_admin():
        log_super_admin_access(
            db=db,
            super_admin=current_user,
            target_org_id=org_id,
            action="view_destination",
            resource_type="destination",
            resource_id=str(destination.public_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    return destination


@router.post("", response_model=DestinationResponse, status_code=status.HTTP_201_CREATED)
@require_permission("destination", "create")
async def create_destination(
    destination_data: DestinationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new destination.

    **Requires:** destination.create permission
    """
    if destination_data.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create destination for different organization",
        )

    # Normalize destination_type to uppercase to match database enum
    # Frontend sends: "postgres", "s3", "bigquery"
    # Database expects: "POSTGRES", "S3", "BIGQUERY"
    normalized_destination_type = destination_data.destination_type.upper()

    # Handle special case: postgresql -> POSTGRES
    if normalized_destination_type == "POSTGRESQL":
        normalized_destination_type = "POSTGRES"

    destination = Destination(
        name=destination_data.name,
        description=destination_data.description,
        organization_id=destination_data.organization_id,
        destination_type=normalized_destination_type,
        config=destination_data.config,
        is_active=True,
    )

    db.add(destination)
    db.commit()
    db.refresh(destination)

    logger.info(f"Destination created: {destination.id} - {destination.name}")
    return destination


@router.put("/{destination_id}", response_model=DestinationResponse)
@require_permission("destination", "update")
async def update_destination(
    destination_id: str,
    destination_data: DestinationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing destination.

    **Requires:** destination.update permission
    """
    from uuid import UUID

    try:
        destination_uuid = UUID(destination_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid destination ID format",
        )

    destination = db.query(Destination).filter(
        Destination.public_id == destination_uuid,
        Destination.organization_id == current_user.organization_id,
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found",
        )

    update_data = destination_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(destination, field, value)

    db.commit()
    db.refresh(destination)

    logger.info(f"Destination updated: {destination.id} - {destination.name}")
    return destination


@router.delete("/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("destination", "delete")
async def delete_destination(
    destination_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a destination and all dependent pipelines.

    **Requires:** destination.delete permission
    """
    from uuid import UUID

    try:
        destination_uuid = UUID(destination_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid destination ID format",
        )

    destination = db.query(Destination).filter(
        Destination.public_id == destination_uuid,
        Destination.organization_id == current_user.organization_id,
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found",
        )

    # Delete all pipelines that use this destination (cascade delete)
    dependent_pipelines = db.query(Pipeline).filter(
        Pipeline.destination_id == destination.id,  # Use integer ID
        Pipeline.organization_id == current_user.organization_id,
    ).all()

    if dependent_pipelines:
        logger.info(f"Deleting {len(dependent_pipelines)} dependent pipeline(s) for destination {destination.id}")
        for pipeline in dependent_pipelines:
            db.delete(pipeline)

    db.delete(destination)
    db.commit()

    logger.info(f"Destination deleted: {destination.id}")
    return None


@router.post("/{destination_id}/test")
@require_permission("destination", "read")
async def test_destination_connection(
    destination_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test connection to a destination.

    **Requires:** destination.read permission
    """
    from uuid import UUID

    try:
        destination_uuid = UUID(destination_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid destination ID format",
        )

    destination = db.query(Destination).filter(
        Destination.public_id == destination_uuid,
        Destination.organization_id == current_user.organization_id,
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found",
        )

    # Test the connection
    logger.info(f"Testing connection for destination: {destination.id} (type: {destination.destination_type})")

    from backend.utils.connection_tester import test_destination_connection as test_dest_conn

    success, message = test_dest_conn(destination.destination_type.value, destination.config)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection test failed: {message}",
        )

    return {
        "destination_id": str(destination.public_id),
        "status": "success",
        "message": message,
    }
