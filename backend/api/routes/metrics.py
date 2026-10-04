"""
Metrics API Routes

Provides aggregated metrics and analytics for pipelines and platform health.
"""
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_, case, text, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.async_database import get_async_db
from backend.models.pipeline import Pipeline, PipelineRun, DataSource, Destination, User
from backend.auth import get_current_user

router = APIRouter(prefix="/metrics", tags=["Metrics"])


def _start_time(timerange: str) -> datetime:
    now = datetime.now(timezone.utc)
    if timerange == "24h":
        return now - timedelta(hours=24)
    if timerange == "7d":
        return now - timedelta(days=7)
    return now - timedelta(days=30)


@router.get("/overview")
async def get_overview_metrics(
    timerange: str = Query("24h", regex="^(24h|7d|30d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Get overview metrics for the organization."""
    org_id = current_user.organization_id
    start_time = _start_time(timerange)

    # Single query for all run statistics using conditional aggregation
    run_stats = (
        await db.execute(
            select(
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
            .where(
                Pipeline.organization_id == org_id,
                PipelineRun.created_at >= start_time,
            )
        )
    ).first()

    total_runs = run_stats.total_runs or 0
    completed_runs = int(run_stats.completed_runs or 0)
    failed_runs = int(run_stats.failed_runs or 0)
    running_runs = int(run_stats.running_runs or 0)
    avg_duration = float(run_stats.avg_duration) if run_stats.avg_duration else 0
    total_rows = int(run_stats.total_rows or 0)

    success_rate = (completed_runs / total_runs * 100) if total_runs > 0 else 0

    pipeline_stats = (
        await db.execute(
            select(
                func.count(Pipeline.id).label("total"),
                func.sum(case((Pipeline.is_active, 1), else_=0)).label("active"),
            )
            .where(Pipeline.organization_id == org_id)
        )
    ).first()
    active_pipelines = int(pipeline_stats.active or 0)

    most_active = None
    slowest = None

    if total_runs > 0:
        most_active = (
            await db.execute(
                select(Pipeline.name, func.count(PipelineRun.id).label("run_count"))
                .join(PipelineRun)
                .where(
                    Pipeline.organization_id == org_id,
                    PipelineRun.created_at >= start_time,
                )
                .group_by(Pipeline.id, Pipeline.name)
                .order_by(func.count(PipelineRun.id).desc())
                .limit(1)
            )
        ).first()

        if completed_runs > 0:
            slowest = (
                await db.execute(
                    select(Pipeline.name, func.avg(PipelineRun.duration_seconds).label("avg_duration"))
                    .join(PipelineRun)
                    .where(
                        Pipeline.organization_id == org_id,
                        PipelineRun.created_at >= start_time,
                        PipelineRun.status == "completed",
                        PipelineRun.duration_seconds.isnot(None),
                    )
                    .group_by(Pipeline.id, Pipeline.name)
                    .order_by(func.avg(PipelineRun.duration_seconds).desc())
                    .limit(1)
                )
            ).first()

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
            "run_count": most_active[1] if most_active else 0,
        },
        "slowest_pipeline": {
            "name": slowest[0] if slowest else None,
            "avg_duration": round(float(slowest[1]), 2) if slowest else 0,
        },
    }


@router.get("/pipeline/{pipeline_id}/performance")
async def get_pipeline_performance(
    pipeline_id: int,
    timerange: str = Query("7d", regex="^(24h|7d|30d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Get performance metrics for a specific pipeline."""
    org_id = current_user.organization_id

    pipeline = (
        await db.execute(
            select(Pipeline).where(
                Pipeline.id == pipeline_id,
                Pipeline.organization_id == org_id,
            )
        )
    ).scalar_one_or_none()

    if not pipeline:
        return {"error": "Pipeline not found"}

    start_time = _start_time(timerange)

    runs = (
        await db.execute(
            select(PipelineRun)
            .where(
                PipelineRun.pipeline_id == pipeline_id,
                PipelineRun.created_at >= start_time,
            )
            .order_by(PipelineRun.created_at.asc())
        )
    ).scalars().all()

    duration_trend = []
    for run in runs:
        if run.status == "completed" and run.duration_seconds:
            duration_trend.append({
                "timestamp": run.created_at.isoformat(),
                "duration": round(run.duration_seconds, 2),
                "rows": run.rows_written or 0,
            })

    total_runs = len(runs)
    completed = sum(1 for r in runs if r.status == "completed")
    success_rate = (completed / total_runs * 100) if total_runs > 0 else 0

    durations = [r.duration_seconds for r in runs if r.status == "completed" and r.duration_seconds]
    avg_duration = sum(durations) / len(durations) if durations else 0

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
                "created_at": r.created_at.isoformat(),
            }
            for r in runs[-10:]
        ],
    }


@router.get("/system-health")
async def get_system_health(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """Get system health metrics."""
    org_id = current_user.organization_id

    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    pipeline_counts = (
        await db.execute(
            select(
                func.count(Pipeline.id).label("total"),
                func.sum(case((Pipeline.is_active, 1), else_=0)).label("active"),
            )
            .where(Pipeline.organization_id == org_id)
        )
    ).first()

    running_count = await db.scalar(
        select(func.count(PipelineRun.id))
        .join(Pipeline)
        .where(
            Pipeline.organization_id == org_id,
            PipelineRun.status == "running",
        )
    ) or 0

    sources_count = await db.scalar(
        select(func.count(DataSource.id)).where(DataSource.organization_id == org_id)
    ) or 0

    destinations_count = await db.scalar(
        select(func.count(Destination.id)).where(Destination.organization_id == org_id)
    ) or 0

    return {
        "database": db_status,
        "sources": sources_count,
        "destinations": destinations_count,
        "active_pipelines": int(pipeline_counts.active or 0),
        "running_pipelines": running_count,
        "status": "healthy" if db_status == "healthy" else "degraded",
    }
