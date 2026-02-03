"""
Data Export API Routes.

Provides endpoints for exporting pipeline runs and audit logs as CSV or JSON.
"""
import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.pipeline import PipelineRun, Pipeline, User
from backend.models.audit import AuditLog

router = APIRouter(prefix="/exports", tags=["Exports"])


def _datetime_serializer(obj):
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return obj.isoformat().replace("+00:00", "Z")
    return str(obj)


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    """Build a StreamingResponse for CSV data."""
    if not rows:
        output = io.StringIO()
        output.write("")
        output.seek(0)
    else:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _json_response(rows: list[dict], filename: str) -> StreamingResponse:
    """Build a StreamingResponse for a downloadable JSON file."""
    content = json.dumps(rows, default=_datetime_serializer, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/runs")
def export_runs(
    format: str = Query("csv", regex="^(csv|json)$"),
    pipeline_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export pipeline runs as CSV or JSON."""
    query = db.query(PipelineRun).join(Pipeline).filter(
        Pipeline.organization_id == current_user.organization_id
    )

    if pipeline_id is not None:
        query = query.filter(PipelineRun.pipeline_id == pipeline_id)
    if start_date:
        query = query.filter(PipelineRun.created_at >= start_date)
    if end_date:
        query = query.filter(PipelineRun.created_at <= end_date)

    runs = query.order_by(desc(PipelineRun.created_at)).all()

    rows = [
        {
            "id": run.id,
            "public_id": str(run.public_id),
            "pipeline_id": run.pipeline_id,
            "pipeline_name": run.pipeline.name if run.pipeline else None,
            "status": run.status.value if run.status else None,
            "started_at": run.started_at.isoformat() if run.started_at else "",
            "completed_at": run.completed_at.isoformat() if run.completed_at else "",
            "rows_read": run.rows_read or "",
            "rows_written": run.rows_written or "",
            "bytes_read": run.bytes_read or "",
            "bytes_written": run.bytes_written or "",
            "duration_seconds": run.duration_seconds or "",
            "error_message": run.error_message or "",
            "retry_count": run.retry_count,
            "is_retry": run.is_retry,
            "created_at": run.created_at.isoformat() if run.created_at else "",
        }
        for run in runs
    ]

    if format == "json":
        return _json_response(rows, "pipeline_runs.json")
    return _csv_response(rows, "pipeline_runs.csv")


@router.get("/audit-logs")
def export_audit_logs(
    format: str = Query("csv", regex="^(csv|json)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export audit logs as CSV or JSON."""
    query = db.query(AuditLog).filter(
        AuditLog.organization_id == current_user.organization_id
    )

    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    logs = query.order_by(desc(AuditLog.created_at)).all()

    rows = [
        {
            "id": str(log.public_id),
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id or "",
            "changes": json.dumps(log.changes) if log.changes else "",
            "ip_address": log.ip_address or "",
            "user_agent": log.user_agent or "",
            "created_at": log.created_at.isoformat() if log.created_at else "",
        }
        for log in logs
    ]

    if format == "json":
        return _json_response(rows, "audit_logs.json")
    return _csv_response(rows, "audit_logs.csv")
