"""
Analytics API routes.

Provides data analytics and reporting endpoints for end users
to get insights from their synced data.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from backend.database import get_db
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


@router.get("/overview")
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get high-level analytics overview for the organization dashboard."""
    org_id = current_user.organization_id

    # Pipeline counts
    total_pipelines = db.query(func.count(Pipeline.id)).filter(
        Pipeline.organization_id == org_id
    ).scalar() or 0

    active_pipelines = db.query(func.count(Pipeline.id)).filter(
        Pipeline.organization_id == org_id,
        Pipeline.is_active == True,
        Pipeline.schedule_enabled == True,
    ).scalar() or 0

    # Run stats (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    total_runs = db.query(func.count(PipelineRun.id)).join(Pipeline).filter(
        Pipeline.organization_id == org_id,
        PipelineRun.created_at >= thirty_days_ago,
    ).scalar() or 0

    successful_runs = db.query(func.count(PipelineRun.id)).join(Pipeline).filter(
        Pipeline.organization_id == org_id,
        PipelineRun.created_at >= thirty_days_ago,
        PipelineRun.status == PipelineStatus.COMPLETED,
    ).scalar() or 0

    failed_runs = db.query(func.count(PipelineRun.id)).join(Pipeline).filter(
        Pipeline.organization_id == org_id,
        PipelineRun.created_at >= thirty_days_ago,
        PipelineRun.status == PipelineStatus.FAILED,
    ).scalar() or 0

    # Rows synced (last 30 days)
    rows_synced = db.query(func.sum(PipelineRun.rows_written)).join(Pipeline).filter(
        Pipeline.organization_id == org_id,
        PipelineRun.created_at >= thirty_days_ago,
        PipelineRun.status == PipelineStatus.COMPLETED,
    ).scalar() or 0

    # Avg duration
    avg_duration = db.query(func.avg(PipelineRun.duration_seconds)).join(Pipeline).filter(
        Pipeline.organization_id == org_id,
        PipelineRun.created_at >= thirty_days_ago,
        PipelineRun.status == PipelineStatus.COMPLETED,
    ).scalar() or 0

    # Source and destination counts
    source_count = db.query(func.count(DataSource.id)).filter(
        DataSource.organization_id == org_id,
    ).scalar() or 0

    destination_count = db.query(func.count(Destination.id)).filter(
        Destination.organization_id == org_id,
    ).scalar() or 0

    success_rate = round((successful_runs / total_runs) * 100, 1) if total_runs > 0 else 0

    return {
        "period": "last_30_days",
        "pipelines": {
            "total": total_pipelines,
            "active": active_pipelines,
        },
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
        "connectors": {
            "sources": source_count,
            "destinations": destination_count,
        },
    }


@router.get("/runs/timeline")
async def get_runs_timeline(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get daily pipeline run counts for charting (success vs failure over time)."""
    org_id = current_user.organization_id
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    runs = db.query(
        func.date(PipelineRun.created_at).label("date"),
        PipelineRun.status,
        func.count(PipelineRun.id).label("count"),
    ).join(Pipeline).filter(
        Pipeline.organization_id == org_id,
        PipelineRun.created_at >= start_date,
    ).group_by(
        func.date(PipelineRun.created_at),
        PipelineRun.status,
    ).order_by("date").all()

    # Group by date
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
    db: Session = Depends(get_db),
):
    """Get daily rows synced for charting volume over time."""
    org_id = current_user.organization_id
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    rows = db.query(
        func.date(PipelineRun.created_at).label("date"),
        func.sum(PipelineRun.rows_written).label("rows"),
    ).join(Pipeline).filter(
        Pipeline.organization_id == org_id,
        PipelineRun.created_at >= start_date,
        PipelineRun.status == PipelineStatus.COMPLETED,
    ).group_by(func.date(PipelineRun.created_at)).order_by("date").all()

    return {
        "timeline": [
            {"date": str(row.date), "rows_synced": row.rows or 0}
            for row in rows
        ]
    }


@router.get("/pipelines/performance")
async def get_pipeline_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get performance metrics per pipeline (success rate, avg duration, rows)."""
    org_id = current_user.organization_id
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    pipelines = db.query(Pipeline).filter(
        Pipeline.organization_id == org_id,
    ).all()

    results = []
    for p in pipelines:
        runs = db.query(PipelineRun).filter(
            PipelineRun.pipeline_id == p.id,
            PipelineRun.created_at >= thirty_days_ago,
        ).all()

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

    # Sort by total runs descending
    results.sort(key=lambda x: x["total_runs"], reverse=True)
    return {"pipelines": results}


@router.get("/sources/breakdown")
async def get_source_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get breakdown of data synced by source type."""
    org_id = current_user.organization_id
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    sources = db.query(
        DataSource.source_type,
        func.count(Pipeline.id).label("pipeline_count"),
        func.sum(PipelineRun.rows_written).label("total_rows"),
    ).join(
        Pipeline, Pipeline.source_id == DataSource.id
    ).join(
        PipelineRun, PipelineRun.pipeline_id == Pipeline.id
    ).filter(
        DataSource.organization_id == org_id,
        PipelineRun.created_at >= thirty_days_ago,
        PipelineRun.status == PipelineStatus.COMPLETED,
    ).group_by(DataSource.source_type).all()

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
    db: Session = Depends(get_db),
):
    """Get usage history over the past N months for trending."""
    org_id = current_user.organization_id

    records = db.query(UsageRecord).filter(
        UsageRecord.organization_id == org_id,
    ).order_by(
        desc(UsageRecord.period_year),
        desc(UsageRecord.period_month),
    ).limit(months).all()

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
