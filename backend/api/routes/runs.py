"""
Pipeline Run API routes.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import PipelineRunResponse, PipelineRunUpdate
from backend.models.pipeline import PipelineRun, Pipeline, User
from backend.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["Pipeline Runs"])


@router.get("", response_model=List[PipelineRunResponse])
async def list_runs(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: str = Query(None, alias="status"),
    org_id: Optional[int] = Query(None, description="Organization ID (super admin only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all pipeline runs for the current user's organization.
    Super admins can optionally specify org_id to view another organization's runs.
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
            action="view_runs",
            resource_type="run",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    else:
        target_org_id = current_user.organization_id

    query = db.query(PipelineRun).join(Pipeline).filter(
        Pipeline.organization_id == target_org_id
    )

    if status_filter:
        query = query.filter(PipelineRun.status == status_filter)

    runs = query.order_by(PipelineRun.created_at.desc()).offset(skip).limit(limit).all()
    return runs


@router.get("/{run_id}", response_model=PipelineRunResponse)
async def get_run(
    request: Request,
    run_id: int,
    org_id: Optional[int] = Query(None, description="Organization ID (super admin only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific pipeline run by ID.
    Super admins can optionally specify org_id to view another organization's run.
    """
    from backend.rbac.audit import log_super_admin_access

    # Determine target organization
    if org_id and current_user.is_super_admin():
        target_org_id = org_id
    else:
        target_org_id = current_user.organization_id

    run = db.query(PipelineRun).join(Pipeline).filter(
        PipelineRun.id == run_id,
        Pipeline.organization_id == target_org_id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run not found",
        )

    # Log super admin access if viewing another org
    if org_id and current_user.is_super_admin():
        log_super_admin_access(
            db=db,
            super_admin=current_user,
            target_org_id=org_id,
            action="view_run",
            resource_type="run",
            resource_id=str(run.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    return run


@router.put("/{run_id}", response_model=PipelineRunResponse)
async def update_run(
    run_id: int,
    run_data: PipelineRunUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a pipeline run (typically called by the pipeline executor)."""
    run = db.query(PipelineRun).join(Pipeline).filter(
        PipelineRun.id == run_id,
        Pipeline.organization_id == current_user.organization_id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run not found",
        )

    update_data = run_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(run, field, value)

    db.commit()
    db.refresh(run)

    logger.info(f"Pipeline run updated: {run.id} - Status: {run.status}")
    return run


@router.post("/{run_id}/cancel")
async def cancel_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a running pipeline."""
    run = db.query(PipelineRun).join(Pipeline).filter(
        PipelineRun.id == run_id,
        Pipeline.organization_id == current_user.organization_id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run not found",
        )

    if run.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel run with status: {run.status}",
        )

    run.status = "cancelled"
    db.commit()

    logger.info(f"Pipeline run cancelled: {run.id}")

    # Cancel the Prefect flow
    cancellation_attempted = False
    cancellation_error = None

    try:
        from prefect import get_client
        import asyncio

        # Cancel the flow run in Prefect
        async def cancel_flow():
            async with get_client() as client:
                # Find the flow run that matches our pipeline run
                flow_runs = await client.read_flow_runs(limit=100)

                for flow_run in flow_runs:
                    if flow_run.name and str(run.id) in flow_run.name:
                        # Cancel the flow run
                        await client.set_flow_run_state(
                            flow_run_id=flow_run.id,
                            state={"type": "CANCELLED", "message": "Cancelled by user"},
                        )
                        logger.info(f"Cancelled Prefect flow run: {flow_run.id}")
                        return True

                return False

        # Run async cancellation
        asyncio.run(cancel_flow())
        cancellation_attempted = True

    except Exception as e:
        logger.error(f"Failed to cancel Prefect flow: {str(e)}", exc_info=True)
        cancellation_error = str(e)

    return {
        "run_id": run_id,
        "status": "cancelled",
        "message": "Pipeline run cancelled successfully",
        "prefect_cancellation_attempted": cancellation_attempted,
        "prefect_cancellation_error": cancellation_error,
    }


@router.get("/{run_id}/logs")
async def get_run_logs(
    request: Request,
    run_id: int,
    org_id: Optional[int] = Query(None, description="Organization ID (super admin only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get logs for a specific pipeline run.
    Super admins can optionally specify org_id to view another organization's run logs.
    """
    from backend.rbac.audit import log_super_admin_access

    # Determine target organization
    if org_id and current_user.is_super_admin():
        target_org_id = org_id
    else:
        target_org_id = current_user.organization_id

    run = db.query(PipelineRun).join(Pipeline).filter(
        PipelineRun.id == run_id,
        Pipeline.organization_id == target_org_id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run not found",
        )

    # Log super admin access if viewing another org
    if org_id and current_user.is_super_admin():
        log_super_admin_access(
            db=db,
            super_admin=current_user,
            target_org_id=org_id,
            action="view_run_logs",
            resource_type="run",
            resource_id=str(run.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    # Retrieve logs from Prefect
    logs = []

    try:
        from prefect import get_client
        import asyncio

        # Get Prefect client
        async def fetch_logs():
            async with get_client() as client:
                # Query flow runs by our run metadata
                flow_runs = await client.read_flow_runs(
                    limit=100,
                )

                # Find the flow run that matches our pipeline run
                matching_run = None
                for flow_run in flow_runs:
                    if flow_run.name and str(run.id) in flow_run.name:
                        matching_run = flow_run
                        break

                if not matching_run:
                    return []

                # Fetch logs for this flow run
                log_filter = {
                    "flow_run_id": {"any_": [matching_run.id]},
                }

                logs_response = await client.read_logs(
                    log_filter=log_filter,
                    limit=1000,
                    offset=0,
                )

                return [
                    {
                        "timestamp": log.timestamp.isoformat() if log.timestamp else run.created_at.isoformat(),
                        "level": log.level,
                        "message": log.message,
                    }
                    for log in logs_response
                ]

        # Run async function
        logs = asyncio.run(fetch_logs())

    except Exception as e:
        logger.error(f"Failed to fetch Prefect logs: {str(e)}", exc_info=True)

        # Fallback to basic logs from run metadata
        logs = [
            {
                "timestamp": run.created_at.isoformat(),
                "level": "INFO",
                "message": f"Pipeline run {run_id} created",
            }
        ]

        if run.started_at:
            logs.append({
                "timestamp": run.started_at.isoformat(),
                "level": "INFO",
                "message": f"Pipeline run started",
            })

        if run.status.value == "failed" and run.error_message:
            logs.append({
                "timestamp": run.completed_at.isoformat() if run.completed_at else run.started_at.isoformat(),
                "level": "ERROR",
                "message": run.error_message,
            })

        if run.completed_at:
            logs.append({
                "timestamp": run.completed_at.isoformat(),
                "level": "INFO",
                "message": f"Pipeline run {run.status.value}",
            })

    return {
        "run_id": run_id,
        "logs": logs,
    }
