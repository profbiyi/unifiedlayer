"""
Audit Log API Routes.

Provides endpoints for querying audit logs within an organization.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.pipeline import User
from backend.models.audit import AuditLog

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get("")
def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action (create, update, delete, login, export, execute)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (pipeline, source, destination, user, billing)"),
    start_date: Optional[datetime] = Query(None, description="Filter logs from this date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter logs until this date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    List audit logs for the current user's organization.

    Supports filtering by action, resource_type, and date range with pagination.
    """
    query = db.query(AuditLog).filter(
        AuditLog.organization_id == current_user.organization_id
    )

    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    total = query.count()
    offset = (page - 1) * page_size
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size).all()

    return {
        "data": [
            {
                "id": str(log.public_id),
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "changes": log.changes,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }
