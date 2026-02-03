"""
Metrics API Routes

Provides aggregated metrics and analytics for pipelines and platform health.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend.database import get_db
from backend.models.pipeline import Pipeline, PipelineRun, DataSource, Destination, User
from backend.auth import get_current_user

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/overview")
async def get_overview_metrics(
    timerange: str = Query("24h", regex="^(24h|7d|30d)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get overview metrics for the organization.

    Args:
        timerange: Time range for metrics (24h, 7d, 30d)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Overview metrics including success rate, run counts, duration stats
    """
    from sqlalchemy import case

    org_id = current_user.organization_id

    # Calculate time threshold
    now = datetime.now(timezone.utc)
    if timerange == "24h":
        start_time = now - timedelta(hours=24)
    elif timerange == "7d":
        start_time = now - timedelta(days=7)
    else:  # 30d
        start_time = now - timedelta(days=30)

    # OPTIMIZED: Single query for all run statistics using conditional aggregation
    run_stats = (
        db.query(
            func.count(PipelineRun.id).label("total_runs"),
            func.sum(case((PipelineRun.status == "completed", 1), else_=0)).label("completed_runs"),
            func.sum(case((PipelineRun.status == "failed", 1), else_=0)).label("failed_runs"),
            func.sum(case((PipelineRun.status == "running", 1), else_=0)).label("running_runs"),
            func.avg(case(
                (and_(PipelineRun.status == "completed", PipelineRun.duration_seconds.isnot(None)),
                 PipelineRun.duration_seconds),
                else_=None
            )).label("avg_duration"),
            func.sum(case(
                (and_(PipelineRun.status == "completed", PipelineRun.rows_written.isnot(None)),
                 PipelineRun.rows_written),
                else_=0
            )).label("total_rows"),
        )
        .join(Pipeline)
        .filter(
            Pipeline.organization_id == org_id,
            PipelineRun.created_at >= start_time
        )
        .first()
    )

    total_runs = run_stats.total_runs or 0
    completed_runs = int(run_stats.completed_runs or 0)
    failed_runs = int(run_stats.failed_runs or 0)
    running_runs = int(run_stats.running_runs or 0)
    avg_duration = float(run_stats.avg_duration) if run_stats.avg_duration else 0
    total_rows = int(run_stats.total_rows or 0)

    # Success rate
    success_rate = (completed_runs / total_runs * 100) if total_runs > 0 else 0

    # OPTIMIZED: Single query for pipeline counts
    pipeline_stats = (
        db.query(
            func.count(Pipeline.id).label("total"),
            func.sum(case((Pipeline.is_active == True, 1), else_=0)).label("active"),
        )
        .filter(Pipeline.organization_id == org_id)
        .first()
    )
    active_pipelines = int(pipeline_stats.active or 0)

    # OPTIMIZED: Combined query for most active and slowest (only if we have runs)
    most_active = None
    slowest = None

    if total_runs > 0:
        # Most active pipeline
        most_active = (
            db.query(
                Pipeline.name,
                func.count(PipelineRun.id).label("run_count")
            )
            .join(PipelineRun)
            .filter(
                Pipeline.organization_id == org_id,
                PipelineRun.created_at >= start_time
            )
            .group_by(Pipeline.id, Pipeline.name)
            .order_by(func.count(PipelineRun.id).desc())
            .limit(1)
            .first()
        )

        # Slowest pipeline (only if completed runs exist)
        if completed_runs > 0:
            slowest = (
                db.query(
                    Pipeline.name,
                    func.avg(PipelineRun.duration_seconds).label("avg_duration")
                )
                .join(PipelineRun)
                .filter(
                    Pipeline.organization_id == org_id,
                    PipelineRun.created_at >= start_time,
                    PipelineRun.status == "completed",
                    PipelineRun.duration_seconds.isnot(None)
                )
                .group_by(Pipeline.id, Pipeline.name)
                .order_by(func.avg(PipelineRun.duration_seconds).desc())
                .limit(1)
                .first()
            )

    return {
        "timerange": timerange,
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "failed_runs": failed_runs,
        "running_runs": running_runs,
        "success_rate": round(success_rate, 1),
        "avg_duration_seconds": round(avg_duration, 2),
        "total_rows_processed": total_rows,
        "active_pipelines": active_pipelines,
        "most_active_pipeline": {
            "name": most_active[0] if most_active else None,
            "run_count": most_active[1] if most_active else 0
        },
        "slowest_pipeline": {
            "name": slowest[0] if slowest else None,
            "avg_duration": round(float(slowest[1]), 2) if slowest else 0
        }
    }


@router.get("/pipeline/{pipeline_id}/performance")
async def get_pipeline_performance(
    pipeline_id: int,
    timerange: str = Query("7d", regex="^(24h|7d|30d)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get performance metrics for a specific pipeline.

    Args:
        pipeline_id: Pipeline ID
        timerange: Time range for metrics
        current_user: Current authenticated user
        db: Database session

    Returns:
        Performance metrics and trend data
    """
    org_id = current_user.organization_id

    # Verify pipeline belongs to user's org
    pipeline = (
        db.query(Pipeline)
        .filter(
            Pipeline.id == pipeline_id,
            Pipeline.organization_id == org_id
        )
        .first()
    )

    if not pipeline:
        return {"error": "Pipeline not found"}

    # Calculate time threshold
    now = datetime.now(timezone.utc)
    if timerange == "24h":
        start_time = now - timedelta(hours=24)
    elif timerange == "7d":
        start_time = now - timedelta(days=7)
    else:  # 30d
        start_time = now - timedelta(days=30)

    # Get runs for this pipeline
    runs = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.pipeline_id == pipeline_id,
            PipelineRun.created_at >= start_time
        )
        .order_by(PipelineRun.created_at.asc())
        .all()
    )

    # Build duration trend
    duration_trend = []
    for run in runs:
        if run.status == "completed" and run.duration_seconds:
            duration_trend.append({
                "timestamp": run.created_at.isoformat(),
                "duration": round(run.duration_seconds, 2),
                "rows": run.rows_written or 0
            })

    # Calculate stats
    total_runs = len(runs)
    completed = sum(1 for r in runs if r.status == "completed")
    failed = sum(1 for r in runs if r.status == "failed")
    success_rate = (completed / total_runs * 100) if total_runs > 0 else 0

    # Average duration
    durations = [r.duration_seconds for r in runs if r.status == "completed" and r.duration_seconds]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Total rows processed
    total_rows = sum(r.rows_written or 0 for r in runs if r.status == "completed")

    return {
        "pipeline_name": pipeline.name,
        "timerange": timerange,
        "total_runs": total_runs,
        "success_rate": round(success_rate, 1),
        "avg_duration_seconds": round(avg_duration, 2),
        "total_rows_processed": total_rows,
        "duration_trend": duration_trend,
        "recent_runs": [
            {
                "id": r.id,
                "status": r.status,
                "duration": r.duration_seconds,
                "rows": r.rows_written,
                "created_at": r.created_at.isoformat()
            }
            for r in runs[-10:]  # Last 10 runs
        ]
    }


@router.get("/system-health")
async def get_system_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get system health metrics.

    Returns:
        System health indicators
    """
    from sqlalchemy import text, case

    org_id = current_user.organization_id

    # Database health check
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # OPTIMIZED: Single query for all counts
    counts = (
        db.query(
            func.count(func.distinct(DataSource.id)).label("sources"),
            func.count(func.distinct(Destination.id)).label("destinations"),
        )
        .select_from(DataSource)
        .outerjoin(Destination, Destination.organization_id == org_id)
        .filter(DataSource.organization_id == org_id)
        .first()
    )

    # Get pipeline counts separately (cleaner query)
    pipeline_counts = (
        db.query(
            func.count(Pipeline.id).label("total"),
            func.sum(case((Pipeline.is_active == True, 1), else_=0)).label("active"),
        )
        .filter(Pipeline.organization_id == org_id)
        .first()
    )

    # Running pipelines count
    running_count = (
        db.query(func.count(PipelineRun.id))
        .join(Pipeline)
        .filter(
            Pipeline.organization_id == org_id,
            PipelineRun.status == "running"
        )
        .scalar() or 0
    )

    # Simpler count queries (actually faster for simple counts)
    sources_count = db.query(func.count(DataSource.id)).filter(
        DataSource.organization_id == org_id
    ).scalar() or 0

    destinations_count = db.query(func.count(Destination.id)).filter(
        Destination.organization_id == org_id
    ).scalar() or 0

    return {
        "database": db_status,
        "sources": sources_count,
        "destinations": destinations_count,
        "active_pipelines": int(pipeline_counts.active or 0),
        "running_pipelines": running_count,
        "status": "healthy" if db_status == "healthy" else "degraded"
    }
