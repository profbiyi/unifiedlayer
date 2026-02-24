"""
API Dependencies.

Common dependency functions for FastAPI routes.
"""
from typing import Optional, Tuple, Any
from fastapi import HTTPException, status, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.models import User, Organization
from backend.rbac.permissions import user_has_permission
from backend.utils.idempotency import get_idempotency_result, store_idempotency_result


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


async def check_idempotency(
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
) -> Optional[str]:
    """
    Dependency to extract idempotency key from request header.

    Usage:
        @router.post("/create")
        async def create_resource(
            idempotency_key: Optional[str] = Depends(check_idempotency),
        ):
            # Check for cached result
            cached = get_cached_idempotency_result(idempotency_key)
            if cached:
                return JSONResponse(
                    status_code=cached["status_code"],
                    content=cached["body"],
                )
            # ... process request ...
            # Store result if idempotency_key provided
            if idempotency_key:
                store_idempotency_result(idempotency_key, 201, response_dict)
    """
    return x_idempotency_key


def get_cached_idempotency_result(
    idempotency_key: Optional[str],
) -> Optional[dict]:
    """
    Check if we have a cached result for this idempotency key.

    Args:
        idempotency_key: The idempotency key from header

    Returns:
        Cached result dict with 'status_code' and 'body' if exists, None otherwise
    """
    if not idempotency_key:
        return None
    return get_idempotency_result(idempotency_key)


__all__ = [
    "get_current_user",
    "check_permission",
    "verify_org_access",
    "check_idempotency",
    "get_cached_idempotency_result",
    "store_idempotency_result",
]
