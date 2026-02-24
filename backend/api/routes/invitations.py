"""
User invitation API routes.

Endpoints for inviting users to organizations and accepting invitations.
"""

import secrets
import logging
from typing import List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Role, UserRole, UserInvitation
from backend.auth import (
    require_org_admin,
    get_password_hash,
    get_request_info,
)
from backend.notifications import email_notifier
from backend.config import settings
from backend.schemas.rbac import (
    CreateInvitationRequest,
    InvitationResponse,
    InvitationPublicResponse,
    AcceptInvitationRequest,
    UserWithRoles,
)
from backend.rbac.audit import log_user_action
from backend.rbac.permissions import check_org_user_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("/invite", response_model=InvitationResponse)
async def invite_user(
    request: Request,
    invitation_request: CreateInvitationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    Invite a user to join your organization.

    **Org Admin or Super Admin Only**

    Requirements:
    - Organization must not exceed user limit
    - Email must not already be in use
    - Email must not have pending invitation

    Creates invitation token valid for 7 days.
    """
    request_info = get_request_info(request)

    # Check organization user limit
    check_org_user_limit(current_user.organization, db)

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == invitation_request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Check if there's already a pending invitation for this email
    existing_invitation = db.query(UserInvitation).filter(
        UserInvitation.email == invitation_request.email,
        UserInvitation.organization_id == current_user.organization_id,
        UserInvitation.status == 'pending'
    ).first()

    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is already a pending invitation for this email"
        )

    # Get the role
    role = db.query(Role).filter(Role.slug == invitation_request.role_slug).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    # Create invitation
    invitation = UserInvitation(
        public_id=str(secrets.token_urlsafe(16)),
        organization_id=current_user.organization_id,
        email=invitation_request.email,
        role_id=role.id,
        invited_by_id=current_user.id,
        token=token,
        expires_at=expires_at,
        status='pending',
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    # Log action
    log_user_action(
        db=db,
        user=current_user,
        action="user.invited",
        details={
            "email": invitation_request.email,
            "role": invitation_request.role_slug,
            "invitation_id": invitation.id,
        },
        ip_address=request_info["ip_address"],
    )

    # Send invitation email
    try:
        # Build invitation link
        frontend_url = settings.FRONTEND_URL
        invitation_link = f"{frontend_url}/accept-invitation?token={token}"

        # Get organization branding
        org = current_user.organization

        # Send email with branding
        email_notifier.send_invitation_email(
            to_email=invitation.email,
            organization_name=org.name,
            invited_by_name=current_user.full_name or current_user.username,
            invitation_link=invitation_link,
            role_name=role.name,
            logo_url=org.logo_url,
            brand_primary_color=org.brand_primary_color,
            brand_secondary_color=org.brand_secondary_color,
        )
        logger.info(f"Invitation email sent to {invitation.email}")
    except Exception as e:
        # Log error but don't fail the invitation creation
        # The invitation is still valid and can be accessed via the frontend
        logger.error(f"Failed to send invitation email: {str(e)}")
        # Continue without raising - invitation is still created

    return InvitationResponse(
        id=invitation.id,
        public_id=invitation.public_id,
        organization_id=invitation.organization_id,
        organization_name=current_user.organization.name,
        email=invitation.email,
        role_id=invitation.role_id,
        role_name=role.name,
        invited_by_id=invitation.invited_by_id,
        invited_by_name=current_user.full_name or current_user.username,
        token=invitation.token,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        status=invitation.status,
        created_at=invitation.created_at,
        is_expired=invitation.is_expired,
        is_valid=invitation.is_valid,
    )


@router.get("/pending", response_model=List[InvitationResponse])
async def list_pending_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    List all pending invitations for your organization.

    **Org Admin or Super Admin Only**
    """
    invitations = db.query(UserInvitation).filter(
        UserInvitation.organization_id == current_user.organization_id,
        UserInvitation.status == 'pending'
    ).order_by(UserInvitation.created_at.desc()).all()

    result = []
    for inv in invitations:
        result.append(InvitationResponse(
            id=inv.id,
            public_id=inv.public_id,
            organization_id=inv.organization_id,
            organization_name=current_user.organization.name,
            email=inv.email,
            role_id=inv.role_id,
            role_name=inv.role.name,
            invited_by_id=inv.invited_by_id,
            invited_by_name=inv.invited_by.full_name or inv.invited_by.username,
            token=inv.token,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
            status=inv.status,
            created_at=inv.created_at,
            is_expired=inv.is_expired,
            is_valid=inv.is_valid,
        ))

    return result


@router.delete("/{invitation_id}")
async def cancel_invitation(
    request: Request,
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    """
    Cancel a pending invitation.

    **Org Admin or Super Admin Only**
    """
    request_info = get_request_info(request)

    invitation = db.query(UserInvitation).filter(
        UserInvitation.id == invitation_id,
        UserInvitation.organization_id == current_user.organization_id
    ).first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    if invitation.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel invitation with status: {invitation.status}"
        )

    invitation.status = 'cancelled'
    db.commit()

    # Log action
    log_user_action(
        db=db,
        user=current_user,
        action="invitation.cancelled",
        details={
            "invitation_id": invitation.id,
            "email": invitation.email,
        },
        ip_address=request_info["ip_address"],
    )

    return {"message": "Invitation cancelled successfully"}


@router.get("/validate/{token}", response_model=InvitationPublicResponse)
async def validate_invitation_token(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Validate an invitation token (public endpoint).

    Returns invitation details if valid.
    Used on the invitation acceptance page.
    """
    invitation = db.query(UserInvitation).filter(
        UserInvitation.token == token
    ).first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )

    return InvitationPublicResponse(
        public_id=invitation.public_id,
        organization_name=invitation.organization.name,
        role_name=invitation.role.name,
        email=invitation.email,
        invited_by_name=invitation.invited_by.full_name or invitation.invited_by.username if invitation.invited_by else None,
        expires_at=invitation.expires_at,
        is_valid=invitation.is_valid,
        is_expired=invitation.is_expired,
    )


@router.post("/accept", response_model=UserWithRoles)
async def accept_invitation(
    request: Request,
    accept_request: AcceptInvitationRequest,
    db: Session = Depends(get_db),
):
    """
    Accept an invitation and create user account (public endpoint).

    Creates:
    1. User account
    2. Assigns role from invitation
    3. Marks invitation as accepted

    Returns the created user with roles.
    """
    request_info = get_request_info(request)

    # Find invitation
    invitation = db.query(UserInvitation).filter(
        UserInvitation.token == accept_request.token
    ).first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )

    # Validate invitation
    if not invitation.is_valid:
        if invitation.is_expired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation is not valid (status: {invitation.status})"
            )

    # Check if user with this email already exists
    existing_user = db.query(User).filter(User.email == invitation.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Check if username is taken
    existing_username = db.query(User).filter(User.username == accept_request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )

    # Check organization user limit
    organization = invitation.organization
    if organization.current_user_count >= organization.max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization has reached its user limit ({organization.max_users} users)"
        )

    # Create user
    new_user = User(
        organization_id=invitation.organization_id,
        email=invitation.email,
        username=accept_request.username,
        full_name=accept_request.full_name,
        hashed_password=get_password_hash(accept_request.password),
        is_active=True,
        is_superuser=False,
        email_verified=True,
        invited_by_id=invitation.invited_by_id,
        invitation_accepted_at=datetime.now(timezone.utc),
    )

    db.add(new_user)
    db.flush()  # Get user ID

    # Assign role from invitation
    user_role = UserRole(
        user_id=new_user.id,
        role_id=invitation.role_id,
        organization_id=invitation.organization_id,
        assigned_by_id=invitation.invited_by_id,
    )
    db.add(user_role)

    # Mark invitation as accepted
    invitation.status = 'accepted'
    invitation.accepted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(new_user)

    # Log action
    log_user_action(
        db=db,
        user=new_user,
        action="user.registered",
        target_user_id=new_user.id,
        details={
            "invitation_id": invitation.id,
            "role": invitation.role.slug,
        },
        ip_address=request_info["ip_address"],
    )

    return UserWithRoles(
        id=new_user.id,
        public_id=str(new_user.public_id),
        organization_id=new_user.organization_id,
        email=new_user.email,
        username=new_user.username,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        email_verified=new_user.email_verified,
        roles=[invitation.role.name],
        invited_by_id=new_user.invited_by_id,
        invitation_accepted_at=new_user.invitation_accepted_at,
        last_login=new_user.last_login,
        created_at=new_user.created_at,
    )
