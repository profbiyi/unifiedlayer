"""
API Dependencies.

Common dependency functions for FastAPI routes.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.models import User, Organization
from backend.rbac.permissions import user_has_permission


def check_permission(user: User, permission: str, db: Session) -> None:
    """
    Check if user has a specific permission.

    Args:
        user: Current user
        permission: Permission string (e.g., "pipelines.create")
        db: Database session

    Raises:
        HTTPException: If user doesn't have permission
    """
    resource, action = permission.split(".")

    if not user_has_permission(user, resource, action, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have permission: {permission}",
        )


def verify_org_access(user: User, organization_id: int, db: Session) -> None:
    """
    Verify user has access to an organization.

    Args:
        user: Current user
        organization_id: Organization ID
        db: Database session

    Raises:
        HTTPException: If user doesn't have access
    """
    # Super admins have access to all organizations
    if user.has_role("SUPER_ADMIN"):
        return

    # Regular users can only access their own organization
    if user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this organization",
        )


__all__ = ["get_current_user", "check_permission", "verify_org_access"]
