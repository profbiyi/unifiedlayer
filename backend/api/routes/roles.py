"""
Role management API routes.

Endpoints for managing user roles within organizations.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Role, UserRole
from backend.auth import get_current_user, require_org_admin, get_request_info
from backend.schemas.rbac import (
    ChangeUserRoleRequest,
    UserWithRoles,
    UserListItem,
)
from backend.rbac.audit import log_user_action
from backend.rbac.permissions import user_can_change_role, user_can_manage_user


router = APIRouter(prefix="/organizations/me", tags=["roles"])


@router.get("/users", response_model=List[UserListItem])
async def list_organization_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all users in your organization.

    Returns users with their roles.
    """
    users = db.query(User).filter(
        User.organization_id == current_user.organization_id
    ).all()

    result = []
    for user in users:
        result.append(UserListItem(
            id=user.id,
            public_id=str(user.public_id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=user.role_names,
            last_login=user.last_login,
            created_at=user.created_at,
        ))

    return result


@router.put("/users/{user_id}/role", response_model=UserWithRoles)
async def change_user_role(
    request: Request,
    user_id: int,
    role_request: ChangeUserRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    Change a user's role in your organization.

    **Org Admin or Super Admin Only**

    Rules:
    - Can only change roles within your organization
    - Cannot change your own role
    - Cannot change another org admin's role (unless super admin)
    - Can only assign org_admin or org_user roles
    """
    request_info = get_request_info(request)

    # Get target user
    target_user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization"
        )

    # Check if user can change this role
    if not user_can_change_role(current_user, target_user, role_request.role_slug, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to change this user's role"
        )

    # Get the new role
    new_role = db.query(Role).filter(Role.slug == role_request.role_slug).first()
    if not new_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Get current role assignment
    current_role_assignment = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.organization_id == current_user.organization_id
    ).first()

    old_role_name = None
    if current_role_assignment:
        old_role_name = current_role_assignment.role.name
        # Update existing role
        current_role_assignment.role_id = new_role.id
        current_role_assignment.assigned_by_id = current_user.id
    else:
        # Create new role assignment
        current_role_assignment = UserRole(
            user_id=user_id,
            role_id=new_role.id,
            organization_id=current_user.organization_id,
            assigned_by_id=current_user.id,
        )
        db.add(current_role_assignment)

    db.commit()
    db.refresh(target_user)

    # Log action
    log_user_action(
        db=db,
        user=current_user,
        action="role.changed",
        target_user_id=user_id,
        details={
            "old_role": old_role_name,
            "new_role": new_role.name,
            "target_email": target_user.email,
        },
        ip_address=request_info["ip_address"],
    )

    return UserWithRoles(
        id=target_user.id,
        public_id=str(target_user.public_id),
        organization_id=target_user.organization_id,
        email=target_user.email,
        username=target_user.username,
        full_name=target_user.full_name,
        is_active=target_user.is_active,
        email_verified=target_user.email_verified,
        roles=target_user.role_names,
        invited_by_id=target_user.invited_by_id,
        invitation_accepted_at=target_user.invitation_accepted_at,
        last_login=target_user.last_login,
        created_at=target_user.created_at,
    )


@router.delete("/users/{user_id}")
async def remove_user_from_organization(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    Remove a user from your organization.

    **Org Admin or Super Admin Only**

    Rules:
    - Can only remove users from your organization
    - Cannot remove yourself
    - Cannot remove another org admin (unless super admin)
    """
    request_info = get_request_info(request)

    # Get target user
    target_user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization"
        )

    # Check if user can manage this user
    if not user_can_manage_user(current_user, target_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to remove this user"
        )

    user_email = target_user.email
    user_roles = target_user.role_names

    # Delete user (cascades to user_roles)
    db.delete(target_user)
    db.commit()

    # Log action
    log_user_action(
        db=db,
        user=current_user,
        action="user.removed",
        target_user_id=user_id,
        details={
            "email": user_email,
            "roles": user_roles,
        },
        ip_address=request_info["ip_address"],
    )

    return {"message": f"User {user_email} removed successfully"}


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    Deactivate a user (soft delete).

    **Org Admin or Super Admin Only**

    User can be reactivated later.
    """
    request_info = get_request_info(request)

    target_user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user_can_manage_user(current_user, target_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to deactivate this user"
        )

    target_user.is_active = False
    db.commit()

    # Log action
    log_user_action(
        db=db,
        user=current_user,
        action="user.deactivated",
        target_user_id=user_id,
        details={"email": target_user.email},
        ip_address=request_info["ip_address"],
    )

    return {"message": f"User {target_user.email} deactivated successfully"}


@router.patch("/users/{user_id}/activate")
async def activate_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    Reactivate a deactivated user.

    **Org Admin or Super Admin Only**
    """
    request_info = get_request_info(request)

    target_user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    target_user.is_active = True
    db.commit()

    # Log action
    log_user_action(
        db=db,
        user=current_user,
        action="user.activated",
        target_user_id=user_id,
        details={"email": target_user.email},
        ip_address=request_info["ip_address"],
    )

    return {"message": f"User {target_user.email} activated successfully"}
