"""
Audit logging utility.

Provides a helper function for recording audit log entries.
"""
from typing import Optional, Dict, Any
import logging

from fastapi import Request
from sqlalchemy.orm import Session

from backend.models.audit import AuditLog

logger = logging.getLogger(__name__)


def log_audit(
    db: Session,
    user_id: int,
    org_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        db: Database session
        user_id: ID of the user performing the action
        org_id: Organization ID
        action: Action performed (create, update, delete, login, export, execute)
        resource_type: Type of resource (pipeline, source, destination, user, billing)
        resource_id: ID of the affected resource
        changes: Dictionary of changes {field: {old: ..., new: ...}}
        request: FastAPI request object for extracting IP and user-agent

    Returns:
        The created AuditLog record
    """
    ip_address = None
    user_agent = None

    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    audit_entry = AuditLog(
        user_id=user_id,
        organization_id=org_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)

    logger.info(
        f"Audit: user={user_id} org={org_id} action={action} "
        f"resource={resource_type}/{resource_id}"
    )

    return audit_entry
