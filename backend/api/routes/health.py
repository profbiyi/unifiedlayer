"""
Health Monitoring API Routes.

Provides endpoints for monitoring health status of sources, pipelines, and destinations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from backend.database import get_db
from backend.models.pipeline import User, DataSource, Pipeline, Destination
from backend.models.health import ResourceHealth, HealthStatus, ResourceType, HealthCheckLog
from backend.auth import get_current_user
from backend.services.health_monitor import (
    get_source_health,
    get_pipeline_health,
    get_destination_health,
    get_organization_health_overview,
    save_health_status,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health Monitoring"])


# --- Pydantic Schemas ---

class IssueResponse(BaseModel):
    code: str
    message: str
    severity: str


class HealthMetricsResponse(BaseModel):
    class Config:
        extra = "allow"


class ResourceHealthResponse(BaseModel):
    id: str
    resource_type: str
    resource_id: int
    status: str
    score: float
    issues: List[IssueResponse]
    metrics: dict
    last_checked_at: Optional[datetime] = None
    next_check_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HealthOverviewResponse(BaseModel):
    total_resources: int
    healthy: int
    warning: int
    critical: int
    unknown: int
    by_type: dict
    average_score: float
    overall_status: str
    critical_issues: List[dict]


class SourceHealthResponse(BaseModel):
    source_id: str
    source_name: str
    source_type: str
    status: str
    score: float
    issues: List[IssueResponse]
    metrics: dict
    last_checked_at: Optional[datetime] = None


class PipelineHealthResponse(BaseModel):
    pipeline_id: str
    pipeline_name: str
    status: str
    score: float
    issues: List[IssueResponse]
    metrics: dict
    last_checked_at: Optional[datetime] = None


class DestinationHealthResponse(BaseModel):
    destination_id: str
    destination_name: str
    destination_type: str
    status: str
    score: float
    issues: List[IssueResponse]
    metrics: dict
    last_checked_at: Optional[datetime] = None


class HealthCheckTriggerResponse(BaseModel):
    message: str
    status: str
    score: float
    issues_count: int


class HealthHistoryResponse(BaseModel):
    items: List[dict]
    total: int


# --- Endpoints ---

@router.get("/overview", response_model=HealthOverviewResponse)
async def get_health_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get overall system health overview for the organization.

    Returns aggregate health statistics across all sources, pipelines, and destinations.
    """
    overview = get_organization_health_overview(db, current_user.organization_id)
    return HealthOverviewResponse(**overview)


@router.get("/sources", response_model=List[SourceHealthResponse])
async def get_sources_health(
    status_filter: Optional[str] = Query(None, description="Filter by status (healthy, warning, critical)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get health status for all sources in the organization.

    Returns cached health data. Use POST /health/sources/{id}/check to trigger a fresh check.
    """
    # Get all sources
    sources = db.query(DataSource).filter(
        DataSource.organization_id == current_user.organization_id
    ).all()

    results = []
    for source in sources:
        # Get cached health or create if not exists
        health = db.query(ResourceHealth).filter(
            ResourceHealth.organization_id == current_user.organization_id,
            ResourceHealth.resource_type == ResourceType.SOURCE,
            ResourceHealth.resource_id == source.id,
        ).first()

        # If no cached health, run a quick check (without connection test)
        if not health:
            health_data = get_source_health(source, db, run_connection_test=False)
            health = save_health_status(db, current_user.organization_id, health_data, "on_demand")

        # Apply status filter
        if status_filter:
            if health.status.value != status_filter:
                continue

        source_type = source.source_type.value if hasattr(source.source_type, 'value') else str(source.source_type)

        results.append(SourceHealthResponse(
            source_id=str(source.public_id),
            source_name=source.name,
            source_type=source_type,
            status=health.status.value,
            score=health.score,
            issues=[IssueResponse(**i) for i in (health.issues or [])],
            metrics=health.metrics or {},
            last_checked_at=health.last_checked_at,
        ))

    return results


@router.get("/pipelines", response_model=List[PipelineHealthResponse])
async def get_pipelines_health(
    status_filter: Optional[str] = Query(None, description="Filter by status (healthy, warning, critical)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get health status for all pipelines in the organization.

    Returns cached health data. Use POST /health/pipelines/{id}/check to trigger a fresh check.
    """
    # Get all pipelines
    pipelines = db.query(Pipeline).filter(
        Pipeline.organization_id == current_user.organization_id
    ).all()

    results = []
    for pipeline in pipelines:
        # Get cached health or create if not exists
        health = db.query(ResourceHealth).filter(
            ResourceHealth.organization_id == current_user.organization_id,
            ResourceHealth.resource_type == ResourceType.PIPELINE,
            ResourceHealth.resource_id == pipeline.id,
        ).first()

        # If no cached health, run a check
        if not health:
            health_data = get_pipeline_health(pipeline, db)
            health = save_health_status(db, current_user.organization_id, health_data, "on_demand")

        # Apply status filter
        if status_filter:
            if health.status.value != status_filter:
                continue

        results.append(PipelineHealthResponse(
            pipeline_id=str(pipeline.public_id),
            pipeline_name=pipeline.name,
            status=health.status.value,
            score=health.score,
            issues=[IssueResponse(**i) for i in (health.issues or [])],
            metrics=health.metrics or {},
            last_checked_at=health.last_checked_at,
        ))

    return results


@router.get("/destinations", response_model=List[DestinationHealthResponse])
async def get_destinations_health(
    status_filter: Optional[str] = Query(None, description="Filter by status (healthy, warning, critical)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get health status for all destinations in the organization.

    Returns cached health data.
    """
    # Get all destinations
    destinations = db.query(Destination).filter(
        Destination.organization_id == current_user.organization_id
    ).all()

    results = []
    for destination in destinations:
        # Get cached health or create if not exists
        health = db.query(ResourceHealth).filter(
            ResourceHealth.organization_id == current_user.organization_id,
            ResourceHealth.resource_type == ResourceType.DESTINATION,
            ResourceHealth.resource_id == destination.id,
        ).first()

        # If no cached health, run a quick check (without connection test)
        if not health:
            health_data = get_destination_health(destination, db, run_connection_test=False)
            health = save_health_status(db, current_user.organization_id, health_data, "on_demand")

        # Apply status filter
        if status_filter:
            if health.status.value != status_filter:
                continue

        dest_type = destination.destination_type.value if hasattr(destination.destination_type, 'value') else str(destination.destination_type)

        results.append(DestinationHealthResponse(
            destination_id=str(destination.public_id),
            destination_name=destination.name,
            destination_type=dest_type,
            status=health.status.value,
            score=health.score,
            issues=[IssueResponse(**i) for i in (health.issues or [])],
            metrics=health.metrics or {},
            last_checked_at=health.last_checked_at,
        ))

    return results


@router.get("/source/{source_id}", response_model=SourceHealthResponse)
async def get_source_health_detail(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed health status for a specific source.
    """
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
            detail="Source not found",
        )

    # Get cached health
    health = db.query(ResourceHealth).filter(
        ResourceHealth.organization_id == current_user.organization_id,
        ResourceHealth.resource_type == ResourceType.SOURCE,
        ResourceHealth.resource_id == source.id,
    ).first()

    # If no cached health or stale, run a fresh check
    if not health:
        health_data = get_source_health(source, db, run_connection_test=False)
        health = save_health_status(db, current_user.organization_id, health_data, "on_demand")

    source_type = source.source_type.value if hasattr(source.source_type, 'value') else str(source.source_type)

    return SourceHealthResponse(
        source_id=str(source.public_id),
        source_name=source.name,
        source_type=source_type,
        status=health.status.value,
        score=health.score,
        issues=[IssueResponse(**i) for i in (health.issues or [])],
        metrics=health.metrics or {},
        last_checked_at=health.last_checked_at,
    )


@router.get("/pipeline/{pipeline_id}", response_model=PipelineHealthResponse)
async def get_pipeline_health_detail(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed health status for a specific pipeline.
    """
    try:
        pipeline_uuid = UUID(pipeline_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pipeline ID format",
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.public_id == pipeline_uuid,
        Pipeline.organization_id == current_user.organization_id,
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found",
        )

    # Get cached health
    health = db.query(ResourceHealth).filter(
        ResourceHealth.organization_id == current_user.organization_id,
        ResourceHealth.resource_type == ResourceType.PIPELINE,
        ResourceHealth.resource_id == pipeline.id,
    ).first()

    # If no cached health, run a check
    if not health:
        health_data = get_pipeline_health(pipeline, db)
        health = save_health_status(db, current_user.organization_id, health_data, "on_demand")

    return PipelineHealthResponse(
        pipeline_id=str(pipeline.public_id),
        pipeline_name=pipeline.name,
        status=health.status.value,
        score=health.score,
        issues=[IssueResponse(**i) for i in (health.issues or [])],
        metrics=health.metrics or {},
        last_checked_at=health.last_checked_at,
    )


@router.post("/source/{source_id}/check", response_model=HealthCheckTriggerResponse)
async def trigger_source_health_check(
    source_id: str,
    run_connection_test: bool = Query(True, description="Whether to run actual connection test"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger a fresh health check for a specific source.

    This runs a full health check including connection test (if enabled).
    """
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
            detail="Source not found",
        )

    # Run health check
    health_data = get_source_health(source, db, run_connection_test=run_connection_test)
    health = save_health_status(db, current_user.organization_id, health_data, "manual")

    logger.info(f"Health check triggered for source {source_id}: status={health.status.value}, score={health.score}")

    return HealthCheckTriggerResponse(
        message=f"Health check completed for source '{source.name}'",
        status=health.status.value,
        score=health.score,
        issues_count=len(health.issues or []),
    )


@router.post("/pipeline/{pipeline_id}/check", response_model=HealthCheckTriggerResponse)
async def trigger_pipeline_health_check(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger a fresh health check for a specific pipeline.
    """
    try:
        pipeline_uuid = UUID(pipeline_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pipeline ID format",
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.public_id == pipeline_uuid,
        Pipeline.organization_id == current_user.organization_id,
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found",
        )

    # Run health check
    health_data = get_pipeline_health(pipeline, db)
    health = save_health_status(db, current_user.organization_id, health_data, "manual")

    logger.info(f"Health check triggered for pipeline {pipeline_id}: status={health.status.value}, score={health.score}")

    return HealthCheckTriggerResponse(
        message=f"Health check completed for pipeline '{pipeline.name}'",
        status=health.status.value,
        score=health.score,
        issues_count=len(health.issues or []),
    )


@router.get("/history/{resource_type}/{resource_id}", response_model=HealthHistoryResponse)
async def get_health_history(
    resource_type: str,
    resource_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get health check history for a specific resource.
    """
    # Validate resource type
    try:
        rt = ResourceType(resource_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resource type. Must be one of: {[e.value for e in ResourceType]}",
        )

    # Find the resource to get its internal ID
    try:
        resource_uuid = UUID(resource_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource ID format",
        )

    internal_id = None
    if rt == ResourceType.SOURCE:
        resource = db.query(DataSource).filter(
            DataSource.public_id == resource_uuid,
            DataSource.organization_id == current_user.organization_id,
        ).first()
        if resource:
            internal_id = resource.id
    elif rt == ResourceType.PIPELINE:
        resource = db.query(Pipeline).filter(
            Pipeline.public_id == resource_uuid,
            Pipeline.organization_id == current_user.organization_id,
        ).first()
        if resource:
            internal_id = resource.id
    elif rt == ResourceType.DESTINATION:
        resource = db.query(Destination).filter(
            Destination.public_id == resource_uuid,
            Destination.organization_id == current_user.organization_id,
        ).first()
        if resource:
            internal_id = resource.id

    if internal_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    # Get history
    query = db.query(HealthCheckLog).filter(
        HealthCheckLog.organization_id == current_user.organization_id,
        HealthCheckLog.resource_type == rt,
        HealthCheckLog.resource_id == internal_id,
    ).order_by(HealthCheckLog.checked_at.desc())

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return HealthHistoryResponse(
        items=[{
            "id": item.id,
            "status": item.status.value,
            "score": item.score,
            "issues": item.issues,
            "metrics": item.metrics,
            "check_type": item.check_type,
            "checked_at": item.checked_at.isoformat() if item.checked_at else None,
        } for item in items],
        total=total,
    )
