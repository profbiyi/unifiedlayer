"""
Analytics API routes.

Provides data analytics and reporting endpoints for end users
to get insights from their synced data.
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.async_database import get_async_db
from backend.auth import get_current_user
from backend.models.pipeline import (
    User,
    Pipeline,
    PipelineRun,
    PipelineStatus,
    DataSource,
    Destination,
)
from backend.models.billing import UsageRecord

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _days_ago(days: int) -> datetime:
    # Naive UTC to match the naive `timestamp` columns (asyncpg rejects aware).
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


@router.get("/overview")
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get high-level analytics overview for the organization dashboard."""
    org_id = current_user.organization_id
    thirty_days_ago = _days_ago(30)

    total_pipelines = await db.scalar(
        select(func.count(Pipeline.id)).where(Pipeline.organization_id == org_id)
    ) or 0

    active_pipelines = await db.scalar(
        select(func.count(Pipeline.id)).where(
            Pipeline.organization_id == org_id,
            Pipeline.is_active,
            Pipeline.schedule_enabled,
        )
    ) or 0

    total_runs = await db.scalar(
        select(func.count(PipelineRun.id)).join(Pipeline).where(
            Pipeline.organization_id == org_id,
            PipelineRun.created_at >= thirty_days_ago,
        )
    ) or 0

    successful_runs = await db.scalar(
        select(func.count(PipelineRun.id)).join(Pipeline).where(
            Pipeline.organization_id == org_id,
            PipelineRun.created_at >= thirty_days_ago,
            PipelineRun.status == PipelineStatus.COMPLETED,
        )
    ) or 0

    failed_runs = await db.scalar(
        select(func.count(PipelineRun.id)).join(Pipeline).where(
            Pipeline.organization_id == org_id,
            PipelineRun.created_at >= thirty_days_ago,
            PipelineRun.status == PipelineStatus.FAILED,
        )
    ) or 0

    rows_synced = await db.scalar(
        select(func.sum(PipelineRun.rows_written)).join(Pipeline).where(
            Pipeline.organization_id == org_id,
            PipelineRun.created_at >= thirty_days_ago,
            PipelineRun.status == PipelineStatus.COMPLETED,
        )
    ) or 0

    avg_duration = await db.scalar(
        select(func.avg(PipelineRun.duration_seconds)).join(Pipeline).where(
            Pipeline.organization_id == org_id,
            PipelineRun.created_at >= thirty_days_ago,
            PipelineRun.status == PipelineStatus.COMPLETED,
        )
    ) or 0

    source_count = await db.scalar(
        select(func.count(DataSource.id)).where(DataSource.organization_id == org_id)
    ) or 0

    destination_count = await db.scalar(
        select(func.count(Destination.id)).where(Destination.organization_id == org_id)
    ) or 0

    success_rate = round((successful_runs / total_runs) * 100, 1) if total_runs > 0 else 0

    return {
        "period": "last_30_days",
        "pipelines": {"total": total_pipelines, "active": active_pipelines},
        "runs": {
            "total": total_runs,
            "successful": successful_runs,
            "failed": failed_runs,
            "success_rate": success_rate,
        },
        "data": {
            "rows_synced": rows_synced,
            "avg_duration_seconds": round(avg_duration, 2),
        },
        "connectors": {"sources": source_count, "destinations": destination_count},
    }


@router.get("/runs/timeline")
async def get_runs_timeline(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get daily pipeline run counts for charting (success vs failure over time)."""
    org_id = current_user.organization_id
    start_date = _days_ago(days)

    runs = (
        await db.execute(
            select(
                func.date(PipelineRun.created_at).label("date"),
                PipelineRun.status,
                func.count(PipelineRun.id).label("count"),
            )
            .join(Pipeline)
            .where(
                Pipeline.organization_id == org_id,
                PipelineRun.created_at >= start_date,
            )
            .group_by(func.date(PipelineRun.created_at), PipelineRun.status)
            .order_by(func.date(PipelineRun.created_at))
        )
    ).all()

    timeline = {}
    for row in runs:
        date_str = str(row.date)
        if date_str not in timeline:
            timeline[date_str] = {"date": date_str, "completed": 0, "failed": 0, "total": 0}
        if row.status == PipelineStatus.COMPLETED:
            timeline[date_str]["completed"] = row.count
        elif row.status == PipelineStatus.FAILED:
            timeline[date_str]["failed"] = row.count
        timeline[date_str]["total"] += row.count

    return {"timeline": list(timeline.values())}


@router.get("/rows/timeline")
async def get_rows_timeline(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get daily rows synced for charting volume over time."""
    org_id = current_user.organization_id
    start_date = _days_ago(days)

    rows = (
        await db.execute(
            select(
                func.date(PipelineRun.created_at).label("date"),
                func.sum(PipelineRun.rows_written).label("rows"),
            )
            .join(Pipeline)
            .where(
                Pipeline.organization_id == org_id,
                PipelineRun.created_at >= start_date,
                PipelineRun.status == PipelineStatus.COMPLETED,
            )
            .group_by(func.date(PipelineRun.created_at))
            .order_by(func.date(PipelineRun.created_at))
        )
    ).all()

    return {
        "timeline": [
            {"date": str(row.date), "rows_synced": row.rows or 0}
            for row in rows
        ]
    }


@router.get("/pipelines/performance")
async def get_pipeline_performance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get performance metrics per pipeline (success rate, avg duration, rows)."""
    org_id = current_user.organization_id
    thirty_days_ago = _days_ago(30)

    pipelines = (
        await db.execute(select(Pipeline).where(Pipeline.organization_id == org_id))
    ).scalars().all()

    results = []
    for p in pipelines:
        runs = (
            await db.execute(
                select(PipelineRun).where(
                    PipelineRun.pipeline_id == p.id,
                    PipelineRun.created_at >= thirty_days_ago,
                )
            )
        ).scalars().all()

        total = len(runs)
        completed = sum(1 for r in runs if r.status == PipelineStatus.COMPLETED)
        failed = sum(1 for r in runs if r.status == PipelineStatus.FAILED)
        total_rows = sum(r.rows_written or 0 for r in runs if r.status == PipelineStatus.COMPLETED)
        avg_duration = (
            sum(r.duration_seconds or 0 for r in runs if r.status == PipelineStatus.COMPLETED) / completed
            if completed > 0 else 0
        )

        results.append({
            "pipeline_id": str(p.public_id),
            "pipeline_name": p.name,
            "total_runs": total,
            "successful": completed,
            "failed": failed,
            "success_rate": round((completed / total) * 100, 1) if total > 0 else 0,
            "total_rows_synced": total_rows,
            "avg_duration_seconds": round(avg_duration, 2),
            "is_active": p.is_active and p.schedule_enabled,
            "schedule": p.schedule,
        })

    results.sort(key=lambda x: x["total_runs"], reverse=True)
    return {"pipelines": results}


@router.get("/sources/breakdown")
async def get_source_breakdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get breakdown of data synced by source type."""
    org_id = current_user.organization_id
    thirty_days_ago = _days_ago(30)

    sources = (
        await db.execute(
            select(
                DataSource.source_type,
                func.count(Pipeline.id).label("pipeline_count"),
                func.sum(PipelineRun.rows_written).label("total_rows"),
            )
            .join(Pipeline, Pipeline.source_id == DataSource.id)
            .join(PipelineRun, PipelineRun.pipeline_id == Pipeline.id)
            .where(
                DataSource.organization_id == org_id,
                PipelineRun.created_at >= thirty_days_ago,
                PipelineRun.status == PipelineStatus.COMPLETED,
            )
            .group_by(DataSource.source_type)
        )
    ).all()

    return {
        "sources": [
            {
                "source_type": str(s.source_type.value) if s.source_type else "unknown",
                "pipeline_count": s.pipeline_count or 0,
                "total_rows_synced": s.total_rows or 0,
            }
            for s in sources
        ]
    }


@router.get("/usage/history")
async def get_usage_history(
    months: int = Query(default=6, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get usage history over the past N months for trending."""
    org_id = current_user.organization_id

    records = (
        await db.execute(
            select(UsageRecord)
            .where(UsageRecord.organization_id == org_id)
            .order_by(desc(UsageRecord.period_year), desc(UsageRecord.period_month))
            .limit(months)
        )
    ).scalars().all()

    return {
        "usage_history": [
            {
                "period": f"{r.period_year}-{r.period_month:02d}",
                "rows_synced": r.rows_synced,
                "api_calls": r.api_calls,
                "pipeline_runs": r.pipeline_runs,
                "rows_limit": r.rows_limit,
                "usage_percent": round((r.rows_synced / r.rows_limit) * 100, 1) if r.rows_limit > 0 else 0,
            }
            for r in reversed(records)
        ]
    }
