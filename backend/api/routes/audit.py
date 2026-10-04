"""
Audit Log API Routes.

Provides endpoints for querying audit logs within an organization.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.async_database import get_async_db
from backend.auth import get_current_user
from backend.models.pipeline import User
from backend.models.audit import AuditLog

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


def _naive(dt: Optional[datetime]) -> Optional[datetime]:
    # asyncpg rejects an aware datetime bound against a naive timestamp column.
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


@router.get("")
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action (create, update, delete, login, export, execute)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (pipeline, source, destination, user, billing)"),
    start_date: Optional[datetime] = Query(None, description="Filter logs from this date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter logs until this date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    List audit logs for the current user's organization.

    Supports filtering by action, resource_type, and date range with pagination.
    """
    conds = [AuditLog.organization_id == current_user.organization_id]
    if action:
        conds.append(AuditLog.action == action)
    if resource_type:
        conds.append(AuditLog.resource_type == resource_type)
    if start_date:
        conds.append(AuditLog.created_at >= _naive(start_date))
    if end_date:
        conds.append(AuditLog.created_at <= _naive(end_date))

    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*conds))
    total = total or 0
    offset = (page - 1) * page_size
    logs = (
        await db.execute(
            select(AuditLog)
            .where(*conds)
            .order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

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
