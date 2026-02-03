"""
Permission checking utilities for RBAC system.

This module provides functions to check user permissions and enforce
role-based access control throughout the application.
"""

from typing import List, Optional
from functools import wraps
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models import User, Organization, Role, Permission, UserRole, RolePermission


def get_user_permissions(user: User, db: Session) -> List[Permission]:
    """
    Get all permissions for a user based on their roles.

    Args:
        user: User object
        db: Database session

    Returns:
        List of Permission objects
    """
    permissions = []
    permission_ids = set()

    # Get all user's roles
    for user_role in user.user_roles:
        # Get permissions for this role
        role_perms = db.query(Permission).join(
            RolePermission, RolePermission.permission_id == Permission.id
        ).filter(
            RolePermission.role_id == user_role.role_id
        ).all()

        # Add to set to avoid duplicates
        for perm in role_perms:
            if perm.id not in permission_ids:
                permission_ids.add(perm.id)
                permissions.append(perm)

    return permissions


def user_has_permission(
    user: User,
    resource: str,
    action: str,
    db: Session,
    organization_id: Optional[int] = None
) -> bool:
    """
    Check if user has a specific permission.

    Args:
        user: User object
        resource: Resource name (e.g., 'pipeline', 'user')
        action: Action name (e.g., 'create', 'read', 'delete')
        db: Database session
        organization_id: Optional organization ID to check scope

    Returns:
        True if user has permission, False otherwise
    """
    # Super admins have all permissions
    if user.is_super_admin():
        return True

    # Get user's permissions
    user_permissions = get_user_permissions(user, db)

    # Check if user has the specific permission
    for perm in user_permissions:
        if perm.resource == resource and perm.action == action:
            # If organization_id is specified, verify user belongs to that org
            if organization_id is not None:
                if user.organization_id != organization_id:
                    return False
            return True

    return False


def require_permission(resource: str, action: str):
    """
    Decorator to require specific permission for an endpoint.

    Usage:
        @router.post("/pipelines")
        @require_permission("pipeline", "create")
        async def create_pipeline(...):
            ...

    Args:
        resource: Resource name
        action: Action name

    Raises:
        HTTPException: 403 if user doesn't have permission
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user and db from kwargs
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            if not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session not available"
                )

            # Check permission
            has_perm = user_has_permission(current_user, resource, action, db)

            if not has_perm:
                # Log failed permission check
                from backend.rbac.audit import log_audit
                log_audit(
                    db=db,
                    user=current_user,
                    action="permission.denied",
                    resource_type=resource,
                    details={
                        "resource": resource,
                        "action": action,
                        "endpoint": func.__name__,
                    },
                    ip_address=kwargs.get('request', {}).client.host if kwargs.get('request') else None,
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {resource}:{action}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_org_user_limit(organization: Organization, db: Session) -> bool:
    """
    Check if organization can add more users.

    Args:
        organization: Organization object
        db: Database session

    Returns:
        True if can add users, False if limit reached

    Raises:
        HTTPException: 403 if limit reached
    """
    current_count = len([u for u in organization.users if u.is_active])

    if current_count >= organization.max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User limit reached. Your {organization.subscription_plan} plan allows {organization.max_users} users. Please upgrade to add more users."
        )

    return True


def user_can_manage_user(manager: User, target_user: User, db: Session) -> bool:
    """
    Check if a user can manage another user.

    Rules:
    - Super admins can manage anyone
    - Org admins can manage users in their org (except other org admins unless they're super admin)
    - Regular users can't manage anyone

    Args:
        manager: User attempting to perform the action
        target_user: User being managed
        db: Database session

    Returns:
        True if allowed, False otherwise
    """
    # Super admins can manage anyone
    if manager.is_super_admin():
        return True

    # Users can't manage themselves for certain actions
    if manager.id == target_user.id:
        return False

    # Check if both users are in the same organization
    if manager.organization_id != target_user.organization_id:
        return False

    # Org admins can manage users in their org
    if manager.is_org_admin(manager.organization_id):
        # Can't demote or remove another org admin unless you're super admin
        if target_user.is_org_admin(target_user.organization_id):
            return False
        return True

    return False


def user_can_change_role(manager: User, target_user: User, new_role_slug: str, db: Session) -> bool:
    """
    Check if a user can change another user's role.

    Args:
        manager: User attempting to change the role
        target_user: User whose role is being changed
        new_role_slug: New role slug
        db: Database session

    Returns:
        True if allowed, False otherwise
    """
    # Super admins can change anyone's role
    if manager.is_super_admin():
        return True

    # Users can't change their own role
    if manager.id == target_user.id:
        return False

    # Must be in same organization
    if manager.organization_id != target_user.organization_id:
        return False

    # Only org admins can change roles
    if not manager.is_org_admin(manager.organization_id):
        return False

    # Org admins can't change role of another org admin
    if target_user.is_org_admin(target_user.organization_id):
        return False

    # Can only assign org-level roles
    if new_role_slug not in ['org_admin', 'org_user']:
        return False

    return True


def get_user_role_in_org(user: User, organization_id: int) -> Optional[str]:
    """
    Get user's role in a specific organization.

    Args:
        user: User object
        organization_id: Organization ID

    Returns:
        Role slug or None
    """
    for user_role in user.user_roles:
        if user_role.organization_id == organization_id or user_role.role.scope == 'global':
            return user_role.role.slug
    return None


def require_super_admin(user: User) -> None:
    """
    Require user to be a super admin.

    Args:
        user: User object

    Raises:
        HTTPException: 403 if not super admin
    """
    if not user.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )


def require_org_admin(user: User, organization_id: Optional[int] = None) -> None:
    """
    Require user to be an organization admin.

    Args:
        user: User object
        organization_id: Optional organization ID to check

    Raises:
        HTTPException: 403 if not org admin
    """
    org_id = organization_id or user.organization_id

    if not user.is_super_admin() and not user.is_org_admin(org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin access required"
        )
