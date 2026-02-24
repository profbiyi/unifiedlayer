"""
Pipeline API routes.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import PipelineCreate, PipelineUpdate, PipelineResponse
from backend.models.pipeline import Pipeline, User, PipelineStatus, PipelineRun
from backend.models.billing import Subscription, SubscriptionStatus
from backend.auth import get_current_user
from backend.prefect_flows.pipeline_flow import execute_pipeline_flow
from backend.rbac.permissions import require_permission
from backend.utils.cron_utils import (
    validate_cron_expression,
    calculate_next_run,
    get_cron_description,
    PREDEFINED_SCHEDULES,
    CronValidationError,
)

# Prefect flow execution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


def check_subscription_active(org_id: int, db: Session) -> bool:
    """
    Check if an organization has an active subscription.

    Args:
        org_id: Organization ID
        db: Database session

    Returns:
        True if subscription status is ACTIVE or TRIALING, False otherwise
    """
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == org_id
    ).first()

    if not subscription:
        # No subscription record found - treat as inactive
        return False

    return subscription.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)


@router.get("", response_model=List[PipelineResponse])
@require_permission("pipeline", "read")
async def list_pipelines(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: bool = Query(None),
    org_id: Optional[int] = Query(None, description="Organization ID (super admin only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all pipelines for the current user's organization.
    Super admins can optionally specify org_id to view another organization's pipelines.

    **Requires:** pipeline.read permission

    Args:
        request: FastAPI request
        skip: Number of records to skip
        limit: Maximum number of records to return
        is_active: Filter by active status
        org_id: Organization ID (super admin only)
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of pipelines
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
            action="view_pipelines",
            resource_type="pipeline",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    else:
        target_org_id = current_user.organization_id

    query = db.query(Pipeline).filter(
        Pipeline.organization_id == target_org_id
    )

    if is_active is not None:
        query = query.filter(Pipeline.is_active == is_active)

    pipelines = query.offset(skip).limit(limit).all()
    return pipelines


@router.get("/{pipeline_id}", response_model=PipelineResponse)
@require_permission("pipeline", "read")
async def get_pipeline(
    request: Request,
    pipeline_id: str,
    org_id: Optional[int] = Query(None, description="Organization ID (super admin only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific pipeline by ID.
    Super admins can optionally specify org_id to view another organization's pipeline.

    **Requires:** pipeline.read permission

    Args:
        request: FastAPI request
        pipeline_id: Pipeline ID (UUID string)
        org_id: Organization ID (super admin only)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Pipeline details
    """
    from uuid import UUID
    from backend.rbac.audit import log_super_admin_access

    try:
        pipeline_uuid = UUID(pipeline_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pipeline ID format",
        )

    # Determine target organization
    if org_id and current_user.is_super_admin():
        target_org_id = org_id
    else:
        target_org_id = current_user.organization_id

    pipeline = db.query(Pipeline).filter(
        Pipeline.public_id == pipeline_uuid,
        Pipeline.organization_id == target_org_id,
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found",
        )

    # Log super admin access if viewing another org
    if org_id and current_user.is_super_admin():
        log_super_admin_access(
            db=db,
            super_admin=current_user,
            target_org_id=org_id,
            action="view_pipeline",
            resource_type="pipeline",
            resource_id=str(pipeline.public_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    return pipeline


@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
@require_permission("pipeline", "create")
async def create_pipeline(
    pipeline_data: PipelineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new pipeline.

    **Requires:** pipeline.create permission

    Args:
        pipeline_data: Pipeline creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created pipeline
    """
    # Verify organization access
    if pipeline_data.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create pipeline for different organization",
        )

    # Verify source belongs to user's organization
    from backend.models.pipeline import DataSource, Destination
    from uuid import UUID

    # Convert UUID string to integer ID
    try:
        source_uuid = UUID(pipeline_data.source_id)
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Source not found or access denied",
        )

    # Verify destination belongs to user's organization
    try:
        destination_uuid = UUID(pipeline_data.destination_id)
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Destination not found or access denied",
        )

    pipeline = Pipeline(
        name=pipeline_data.name,
        description=pipeline_data.description,
        organization_id=pipeline_data.organization_id,
        source_id=source.id,  # Use integer ID from resolved source
        destination_id=destination.id,  # Use integer ID from resolved destination
        schedule=pipeline_data.schedule,
        config=pipeline_data.config,
        is_active=True,
    )

    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    logger.info(f"Pipeline created: {pipeline.id} - {pipeline.name}")
    return pipeline


@router.put("/{pipeline_id}", response_model=PipelineResponse)
@require_permission("pipeline", "update")
async def update_pipeline(
    pipeline_id: str,
    pipeline_data: PipelineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing pipeline.

    **Requires:** pipeline.update permission

    Args:
        pipeline_id: Pipeline ID (UUID string)
        pipeline_data: Pipeline update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated pipeline
    """
    from uuid import UUID

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

    # Update fields
    update_data = pipeline_data.dict(exclude_unset=True)

    # If updating source_id, verify it belongs to user's org
    if "source_id" in update_data:
        from backend.models.pipeline import DataSource
        source = db.query(DataSource).filter(
            DataSource.id == update_data["source_id"],
            DataSource.organization_id == current_user.organization_id,
        ).first()

        if not source:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Source not found or access denied",
            )

    # If updating destination_id, verify it belongs to user's org
    if "destination_id" in update_data:
        from backend.models.pipeline import Destination
        destination = db.query(Destination).filter(
            Destination.id == update_data["destination_id"],
            Destination.organization_id == current_user.organization_id,
        ).first()

        if not destination:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Destination not found or access denied",
            )

    for field, value in update_data.items():
        setattr(pipeline, field, value)

    db.commit()
    db.refresh(pipeline)

    logger.info(f"Pipeline updated: {pipeline.id} - {pipeline.name}")
    return pipeline


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("pipeline", "delete")
async def delete_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a pipeline.

    **Requires:** pipeline.delete permission

    Args:
        pipeline_id: Pipeline ID (UUID string)
        current_user: Current authenticated user
        db: Database session
    """
    from uuid import UUID

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

    db.delete(pipeline)
    db.commit()

    logger.info(f"Pipeline deleted: {pipeline.id}")
    return None


@router.post("/{pipeline_id}/clone", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
@require_permission("pipeline", "create")
async def clone_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Clone/duplicate an existing pipeline.

    **Requires:** pipeline.create permission

    Creates a new pipeline with the same source, destination, config, and schedule,
    but with a new ID, "(Copy)" appended to the name, and inactive status.

    Args:
        pipeline_id: Pipeline ID (UUID string)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Cloned pipeline
    """
    from uuid import UUID

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

    cloned = Pipeline(
        name=f"{pipeline.name} (Copy)",
        description=pipeline.description,
        organization_id=pipeline.organization_id,
        source_id=pipeline.source_id,
        destination_id=pipeline.destination_id,
        schedule=pipeline.schedule,
        schedule_timezone=pipeline.schedule_timezone,
        config=pipeline.config,
        is_active=False,
    )

    db.add(cloned)
    db.commit()
    db.refresh(cloned)

    logger.info(f"Pipeline cloned: {cloned.id} - {cloned.name} (from {pipeline.id})")
    return cloned


@router.post("/{pipeline_id}/run", status_code=status.HTTP_202_ACCEPTED)
@require_permission("pipeline", "execute")
async def trigger_pipeline_run(
    pipeline_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger a pipeline run.

    **Requires:** pipeline.execute permission

    Args:
        pipeline_id: Pipeline ID (UUID string)
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        db: Database session

    Returns:
        Run ID and status
    """
    from uuid import UUID

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

    if not pipeline.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline is not active",
        )

    # Check if organization can sync data (soft warning by super admin)
    if not current_user.organization.can_sync_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your organization's data syncing has been disabled. Please contact support.",
        )

    # Check subscription status - block execution if subscription is inactive
    from backend.models.billing import Subscription, SubscriptionStatus
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == current_user.organization_id
    ).first()

    if subscription:
        inactive_statuses = {
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.UNPAID,
            SubscriptionStatus.INCOMPLETE,
        }
        if subscription.status in inactive_statuses:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Subscription inactive ({subscription.status.value}). Please update your payment to continue.",
            )

    # Check for existing active run on this pipeline (prevent concurrent runs)
    active_run = db.query(PipelineRun).filter(
        PipelineRun.pipeline_id == pipeline.id,
        PipelineRun.status.in_([PipelineStatus.PENDING, PipelineStatus.RUNNING]),
    ).first()

    if active_run:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pipeline already has an active run (ID: {active_run.id}, status: {active_run.status.value}). Please wait for it to complete.",
        )

    # Create pipeline run
    run = PipelineRun(
        pipeline_id=pipeline.id,  # Use integer ID
        status=PipelineStatus.PENDING,
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info(f"Pipeline run triggered: {run.id} for pipeline {pipeline.id}")

    # Submit flow execution to Prefect (production-grade with full logging)
    background_tasks.add_task(
        _submit_flow_to_prefect,
        pipeline.id,
        run.id
    )

    logger.info(f"Submitted run {run.id} to Prefect for pipeline {pipeline.id}")

    return {
        "run_id": run.id,
        "pipeline_id": str(pipeline.public_id),  # Return UUID string
        "status": run.status,
        "message": "Pipeline run submitted to Prefect",
    }


def _submit_flow_to_prefect(pipeline_id: int, run_id: int):
    """
    Submit flow run to Prefect for execution.

    Prefect flows are automatically tracked in Prefect UI with full logging.
    On failure, updates the pipeline run status to FAILED.
    """
    from backend.database import get_db_session

    try:
        # Execute the Prefect flow
        # Prefect automatically:
        # - Logs all execution details
        # - Tracks flow runs in the UI
        # - Handles retries and failures
        # - Stores metrics and state
        result = execute_pipeline_flow(pipeline_id, run_id)
        logger.info(f"Flow run completed for pipeline_id={pipeline_id}, run_id={run_id}")
        return result
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Flow run failed for pipeline_id={pipeline_id}, run_id={run_id}: {error_msg}", exc_info=True)

        # Update run status to FAILED on submission/execution error
        try:
            db = get_db_session()
            run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
            if run and run.status in [PipelineStatus.PENDING, PipelineStatus.RUNNING]:
                run.status = PipelineStatus.FAILED
                run.error_message = f"Flow execution failed: {error_msg[:500]}"
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Marked run {run_id} as FAILED due to execution error")
            db.close()
        except Exception as db_error:
            logger.error(f"Failed to update run status after error: {db_error}")

        raise


@router.get("/{pipeline_id}/runs")
@require_permission("pipeline", "read")
async def get_pipeline_runs(
    pipeline_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all runs for a specific pipeline.

    **Requires:** pipeline.read permission

    Args:
        pipeline_id: Pipeline ID (UUID string)
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of pipeline runs
    """
    from uuid import UUID

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

    runs = db.query(PipelineRun).filter(
        PipelineRun.pipeline_id == pipeline.id  # Use integer ID
    ).order_by(PipelineRun.created_at.desc()).offset(skip).limit(limit).all()

    return runs


@router.get("/{pipeline_id}/runs/{run_id}")
@require_permission("pipeline", "read")
async def get_pipeline_run_details(
    pipeline_id: str,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific pipeline run.

    **Requires:** pipeline.read permission

    Args:
        pipeline_id: Pipeline ID (UUID string)
        run_id: Pipeline run ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Pipeline run details including logs and errors
    """
    from uuid import UUID

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

    run = db.query(PipelineRun).filter(
        PipelineRun.id == run_id,
        PipelineRun.pipeline_id == pipeline.id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    return {
        "id": run.id,
        "public_id": str(run.public_id),
        "pipeline_id": str(pipeline.public_id),
        "pipeline_name": pipeline.name,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "duration_seconds": run.duration_seconds,
        "rows_written": run.rows_written,
        "bytes_written": run.bytes_written,
        "error_message": run.error_message,
        "error_traceback": run.error_traceback,
        "run_metadata": run.run_metadata,
        "created_at": run.created_at,
    }


# ==================== PIPELINE SCHEDULING ENDPOINTS ====================


class SetScheduleRequest(BaseModel):
    """Request to set pipeline schedule."""
    schedule: str = Field(..., description="Cron expression (e.g., '0 0 * * *')")
    timezone: str = Field(default="UTC", description="Timezone for schedule (e.g., 'America/New_York', 'UTC')")
    enabled: bool = Field(default=True, description="Whether to enable the schedule")

    @field_validator('schedule')
    @classmethod
    def validate_schedule(cls, v):
        """Validate cron expression."""
        try:
            validate_cron_expression(v)
            return v
        except CronValidationError as e:
            raise ValueError(f"Invalid cron expression: {str(e)}")


class ScheduleResponse(BaseModel):
    """Pipeline schedule response."""
    pipeline_id: str
    pipeline_name: str
    schedule: Optional[str]
    schedule_enabled: bool
    schedule_timezone: str
    description: Optional[str]
    next_run: Optional[str]  # ISO format datetime
    last_run: Optional[str]  # ISO format datetime


@router.put("/{pipeline_id}/schedule")
@require_permission("pipeline", "update")
async def set_pipeline_schedule(
    pipeline_id: str,
    schedule_request: SetScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Set or update pipeline schedule.

    **Requires:** pipeline.update permission

    Args:
        pipeline_id: Pipeline ID (UUID)
        schedule_request: Schedule configuration
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated schedule information
    """
    from uuid import UUID

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

    # Validate and set schedule
    try:
        # Validate cron expression
        validate_cron_expression(schedule_request.schedule)

        # Calculate next run time
        next_run = calculate_next_run(
            schedule_request.schedule,
            timezone_str=schedule_request.timezone
        )

        # Update pipeline
        pipeline.schedule = schedule_request.schedule
        pipeline.schedule_timezone = schedule_request.timezone
        pipeline.schedule_enabled = schedule_request.enabled
        pipeline.next_scheduled_run = next_run

        db.commit()
        db.refresh(pipeline)

        logger.info(
            f"Updated schedule for pipeline {pipeline.id} ({pipeline.name}): "
            f"{schedule_request.schedule} ({schedule_request.timezone}), "
            f"next run: {next_run.isoformat()}"
        )

        return ScheduleResponse(
            pipeline_id=str(pipeline.public_id),
            pipeline_name=pipeline.name,
            schedule=pipeline.schedule,
            schedule_enabled=pipeline.schedule_enabled,
            schedule_timezone=pipeline.schedule_timezone or "UTC",
            description=get_cron_description(pipeline.schedule) if pipeline.schedule else None,
            next_run=pipeline.next_scheduled_run.isoformat() if pipeline.next_scheduled_run else None,
            last_run=pipeline.last_scheduled_run.isoformat() if pipeline.last_scheduled_run else None,
        )

    except CronValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to set schedule: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set schedule: {str(e)}"
        )


@router.get("/{pipeline_id}/schedule", response_model=ScheduleResponse)
@require_permission("pipeline", "read")
async def get_pipeline_schedule(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get pipeline schedule information.

    **Requires:** pipeline.read permission

    Args:
        pipeline_id: Pipeline ID (UUID)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Schedule information
    """
    from uuid import UUID

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

    return ScheduleResponse(
        pipeline_id=str(pipeline.public_id),
        pipeline_name=pipeline.name,
        schedule=pipeline.schedule,
        schedule_enabled=pipeline.schedule_enabled,
        schedule_timezone=pipeline.schedule_timezone or "UTC",
        description=get_cron_description(pipeline.schedule) if pipeline.schedule else None,
        next_run=pipeline.next_scheduled_run.isoformat() if pipeline.next_scheduled_run else None,
        last_run=pipeline.last_scheduled_run.isoformat() if pipeline.last_scheduled_run else None,
    )


@router.delete("/{pipeline_id}/schedule")
@require_permission("pipeline", "update")
async def delete_pipeline_schedule(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove pipeline schedule (disable scheduling).

    **Requires:** pipeline.update permission

    Args:
        pipeline_id: Pipeline ID (UUID)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message
    """
    from uuid import UUID

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

    # Disable and clear schedule
    pipeline.schedule = None
    pipeline.schedule_enabled = False
    pipeline.next_scheduled_run = None

    db.commit()

    logger.info(f"Deleted schedule for pipeline {pipeline.id} ({pipeline.name})")

    return {"message": "Schedule removed successfully"}


@router.post("/{pipeline_id}/schedule/enable")
@require_permission("pipeline", "update")
async def enable_pipeline_schedule(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enable pipeline scheduling.

    **Requires:** pipeline.update permission

    Args:
        pipeline_id: Pipeline ID (UUID)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated schedule information
    """
    from uuid import UUID

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

    if not pipeline.schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline has no schedule to enable. Set a schedule first.",
        )

    # Enable schedule and recalculate next run
    pipeline.schedule_enabled = True

    try:
        next_run = calculate_next_run(
            pipeline.schedule,
            timezone_str=pipeline.schedule_timezone or "UTC"
        )
        pipeline.next_scheduled_run = next_run
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate next run: {str(e)}"
        )

    db.commit()
    db.refresh(pipeline)

    logger.info(f"Enabled schedule for pipeline {pipeline.id} ({pipeline.name})")

    return ScheduleResponse(
        pipeline_id=str(pipeline.public_id),
        pipeline_name=pipeline.name,
        schedule=pipeline.schedule,
        schedule_enabled=pipeline.schedule_enabled,
        schedule_timezone=pipeline.schedule_timezone or "UTC",
        description=get_cron_description(pipeline.schedule) if pipeline.schedule else None,
        next_run=pipeline.next_scheduled_run.isoformat() if pipeline.next_scheduled_run else None,
        last_run=pipeline.last_scheduled_run.isoformat() if pipeline.last_scheduled_run else None,
    )


@router.post("/{pipeline_id}/schedule/disable")
@require_permission("pipeline", "update")
async def disable_pipeline_schedule(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Disable pipeline scheduling (keeps schedule configuration).

    **Requires:** pipeline.update permission

    Args:
        pipeline_id: Pipeline ID (UUID)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated schedule information
    """
    from uuid import UUID

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

    # Disable schedule (but keep configuration)
    pipeline.schedule_enabled = False

    db.commit()
    db.refresh(pipeline)

    logger.info(f"Disabled schedule for pipeline {pipeline.id} ({pipeline.name})")

    return ScheduleResponse(
        pipeline_id=str(pipeline.public_id),
        pipeline_name=pipeline.name,
        schedule=pipeline.schedule,
        schedule_enabled=pipeline.schedule_enabled,
        schedule_timezone=pipeline.schedule_timezone or "UTC",
        description=get_cron_description(pipeline.schedule) if pipeline.schedule else None,
        next_run=pipeline.next_scheduled_run.isoformat() if pipeline.next_scheduled_run else None,
        last_run=pipeline.last_scheduled_run.isoformat() if pipeline.last_scheduled_run else None,
    )


@router.get("/schedules/predefined")
async def get_predefined_schedules():
    """
    Get list of predefined schedule templates.

    Returns common cron expressions with descriptions.
    """
    return {
        "schedules": [
            {
                "id": key,
                "expression": value["expression"],
                "description": value["description"],
            }
            for key, value in PREDEFINED_SCHEDULES.items()
        ]
    }
