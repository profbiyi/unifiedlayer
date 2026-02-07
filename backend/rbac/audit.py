"""
Audit logging utilities.

Track all user actions for security, compliance, and debugging.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.models import User, AuditLog


def log_audit(
    db: Session,
    user: Optional[User],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        db: Database session
        user: User performing the action (None for system actions)
        action: Action being performed (e.g., 'user.invited', 'pipeline.created')
        resource_type: Type of resource (e.g., 'pipeline', 'user')
        resource_id: ID of the resource
        details: Additional context (JSON)
        ip_address: IP address of the client
        user_agent: User agent string

    Returns:
        Created AuditLog object
    """
    audit_log = AuditLog(
        organization_id=user.organization_id if user else None,
        user_id=user.id if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    return audit_log


def log_user_action(
    db: Session,
    user: User,
    action: str,
    target_user_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Log a user management action.

    Args:
        db: Database session
        user: User performing the action
        action: Action performed (e.g., 'user.invited', 'user.deleted', 'role.changed')
        target_user_id: ID of the user being acted upon
        details: Additional details
        ip_address: IP address

    Returns:
        Created AuditLog
    """
    return log_audit(
        db=db,
        user=user,
        action=action,
        resource_type='user',
        resource_id=target_user_id,
        details=details,
        ip_address=ip_address,
    )


def log_pipeline_action(
    db: Session,
    user: User,
    action: str,
    pipeline_id: int,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Log a pipeline action.

    Args:
        db: Database session
        user: User performing the action
        action: Action performed (e.g., 'pipeline.created', 'pipeline.executed')
        pipeline_id: Pipeline ID
        details: Additional details
        ip_address: IP address

    Returns:
        Created AuditLog
    """
    return log_audit(
        db=db,
        user=user,
        action=action,
        resource_type='pipeline',
        resource_id=pipeline_id,
        details=details,
        ip_address=ip_address,
    )


def log_organization_action(
    db: Session,
    user: User,
    action: str,
    organization_id: int,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Log an organization action.

    Args:
        db: Database session
        user: User performing the action
        action: Action performed (e.g., 'organization.created', 'subscription.updated')
        organization_id: Organization ID
        details: Additional details
        ip_address: IP address

    Returns:
        Created AuditLog
    """
    return log_audit(
        db=db,
        user=user,
        action=action,
        resource_type='organization',
        resource_id=organization_id,
        details=details,
        ip_address=ip_address,
    )


def log_auth_event(
    db: Session,
    action: str,
    email: Optional[str] = None,
    user_id: Optional[int] = None,
    success: bool = True,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Log an authentication event.

    Args:
        db: Database session
        action: Action (e.g., 'login.success', 'login.failed', 'logout')
        email: Email address attempted
        user_id: User ID if known
        success: Whether the action succeeded
        ip_address: IP address
        user_agent: User agent
        details: Additional details

    Returns:
        Created AuditLog
    """
    log_details = details or {}
    log_details['success'] = success
    if email:
        log_details['email'] = email

    return log_audit(
        db=db,
        user=None,  # Auth events may not have user yet
        action=action,
        resource_type='auth',
        resource_id=user_id,
        details=log_details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def get_recent_user_activity(
    db: Session,
    user_id: int,
    limit: int = 50
) -> List[AuditLog]:
    """
    Get recent activity for a user.

    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of records

    Returns:
        List of AuditLog entries
    """
    return db.query(AuditLog).filter(
        AuditLog.user_id == user_id
    ).order_by(
        AuditLog.created_at.desc()
    ).limit(limit).all()


def get_organization_activity(
    db: Session,
    organization_id: int,
    limit: int = 100,
    offset: int = 0
) -> List[AuditLog]:
    """
    Get activity for an organization.

    Args:
        db: Database session
        organization_id: Organization ID
        limit: Maximum number of records
        offset: Offset for pagination

    Returns:
        List of AuditLog entries
    """
    return db.query(AuditLog).filter(
        AuditLog.organization_id == organization_id
    ).order_by(
        AuditLog.created_at.desc()
    ).limit(limit).offset(offset).all()


def get_failed_permission_attempts(
    db: Session,
    organization_id: Optional[int] = None,
    hours: int = 24,
    limit: int = 100
) -> List[AuditLog]:
    """
    Get recent failed permission attempts.

    Useful for security monitoring.

    Args:
        db: Database session
        organization_id: Optional organization filter
        hours: Look back this many hours
        limit: Maximum records

    Returns:
        List of failed permission attempts
    """
    from datetime import timedelta

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = db.query(AuditLog).filter(
        AuditLog.action == 'permission.denied',
        AuditLog.created_at >= cutoff_time
    )

    if organization_id:
        query = query.filter(AuditLog.organization_id == organization_id)

    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()


def log_super_admin_access(
    db: Session,
    super_admin: User,
    target_org_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """
    Log super admin cross-organization access.

    This is critical for security auditing - every time a super admin
    views another organization's data, it must be logged.

    Args:
        db: Database session
        super_admin: The super admin user accessing the data
        target_org_id: ID of the organization being accessed
        action: Type of access (view_pipelines, view_runs, impersonate, etc.)
        resource_type: Type of resource (pipeline, run, source, etc.)
        resource_id: Optional specific resource ID
        details: Additional context
        ip_address: IP address of the request
        user_agent: User agent string

    Returns:
        Created SuperAdminAccessLog
    """
    from backend.models.audit import SuperAdminAccessLog

    access_log = SuperAdminAccessLog(
        super_admin_id=super_admin.id,
        target_org_id=target_org_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(access_log)
    db.commit()
    db.refresh(access_log)

    return access_log


def get_super_admin_access_logs(
    db: Session,
    super_admin_id: Optional[int] = None,
    target_org_id: Optional[int] = None,
    hours: int = 168,  # 1 week
    limit: int = 100
) -> List:
    """
    Get super admin access logs.

    Args:
        db: Database session
        super_admin_id: Filter by specific admin
        target_org_id: Filter by target organization
        hours: Look back this many hours
        limit: Maximum records

    Returns:
        List of SuperAdminAccessLog entries
    """
    from datetime import timedelta
    from backend.models.audit import SuperAdminAccessLog

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = db.query(SuperAdminAccessLog).filter(
        SuperAdminAccessLog.created_at >= cutoff_time
    )

    if super_admin_id:
        query = query.filter(SuperAdminAccessLog.super_admin_id == super_admin_id)

    if target_org_id:
        query = query.filter(SuperAdminAccessLog.target_org_id == target_org_id)

    return query.order_by(SuperAdminAccessLog.created_at.desc()).limit(limit).all()
