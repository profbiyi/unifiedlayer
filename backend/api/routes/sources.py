"""
Data Source API routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import DataSourceCreate, DataSourceUpdate, DataSourceResponse
from backend.models.pipeline import DataSource, User, Pipeline
from backend.auth import get_current_user
from backend.rbac.permissions import require_permission
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["Data Sources"])


@router.get("", response_model=List[DataSourceResponse])
@require_permission("source", "read")
async def list_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: bool = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all data sources for the current user's organization.

    **Requires:** source.read permission
    """
    query = db.query(DataSource).filter(
        DataSource.organization_id == current_user.organization_id
    )

    if is_active is not None:
        query = query.filter(DataSource.is_active == is_active)

    sources = query.offset(skip).limit(limit).all()
    return sources


@router.get("/{source_id}", response_model=DataSourceResponse)
@require_permission("source", "read")
async def get_source(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific data source by ID.

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

    return source


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
@require_permission("source", "create")
async def create_source(
    source_data: DataSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new data source.

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
    return source


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
