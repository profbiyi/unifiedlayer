"""
Admin API routes (Super Admin only).

Endpoints for platform administration:
- Create organizations
- Manage subscriptions
- View platform statistics
- Manage all users
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Organization, User, Pipeline, PipelineRun, UserRole, Role
from backend.auth import require_super_admin, get_password_hash, get_request_info
from backend.schemas.rbac import (
    CreateOrganizationRequest,
    OrganizationCreatedResponse,
    OrganizationWithStats,
    OrganizationSubscriptionUpdate,
    PlatformStats,
    UserWithRoles,
)
from backend.rbac.audit import log_organization_action, log_user_action


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/organizations", response_model=OrganizationCreatedResponse)
async def create_organization(
    request: Request,
    org_request: CreateOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Create a new organization with an admin user.

    **Super Admin Only**

    Creates:
    1. Organization with specified plan
    2. Admin user for the organization
    3. Assigns ORG_ADMIN role to the user

    Returns organization and admin user details.
    """
    request_info = get_request_info(request)

    # Check if organization name or slug already exists
    existing = db.query(Organization).filter(
        (Organization.name == org_request.name) | (Organization.slug == org_request.slug)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization with this name or slug already exists"
        )

    # Check if admin email already exists
    existing_user = db.query(User).filter(User.email == org_request.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Check if admin username already exists
    existing_username = db.query(User).filter(User.username == org_request.admin_username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create organization
    organization = Organization(
        name=org_request.name,
        slug=org_request.slug,
        description=org_request.description,
        subscription_plan=org_request.subscription_plan,
        max_users=org_request.max_users,
        billing_email=org_request.billing_email,
        is_active=True,
    )
    db.add(organization)
    db.flush()  # Get organization ID

    # Create admin user
    admin_user = User(
        organization_id=organization.id,
        email=org_request.admin_email,
        username=org_request.admin_username,
        full_name=org_request.admin_full_name,
        hashed_password=get_password_hash(org_request.admin_password),
        is_active=True,
        is_superuser=False,
        email_verified=True,  # Auto-verify for admin-created users
    )
    db.add(admin_user)
    db.flush()  # Get user ID

    # Assign ORG_ADMIN role
    org_admin_role = db.query(Role).filter(Role.slug == 'org_admin').first()
    if not org_admin_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ORG_ADMIN role not found in database"
        )

    user_role = UserRole(
        user_id=admin_user.id,
        role_id=org_admin_role.id,
        organization_id=organization.id,
        assigned_by_id=current_user.id,
    )
    db.add(user_role)
    db.commit()
    db.refresh(organization)
    db.refresh(admin_user)

    # Log action
    log_organization_action(
        db=db,
        user=current_user,
        action="organization.created",
        organization_id=organization.id,
        details={
            "organization_name": organization.name,
            "subscription_plan": organization.subscription_plan,
            "admin_email": admin_user.email,
        },
        ip_address=request_info["ip_address"],
    )

    # Prepare response
    org_stats = OrganizationWithStats(
        id=organization.id,
        public_id=str(organization.public_id),
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        is_active=organization.is_active,
        can_sync_data=organization.can_sync_data,
        subscription_plan=organization.subscription_plan,
        max_users=organization.max_users,
        current_user_count=1,
        subscription_status=organization.subscription_status,
        trial_ends_at=organization.trial_ends_at,
        billing_email=organization.billing_email,
        admin_onboarded=organization.admin_onboarded,
        admin_onboarded_at=organization.admin_onboarded_at,
        logo_url=organization.logo_url,
        brand_primary_color=organization.brand_primary_color,
        brand_secondary_color=organization.brand_secondary_color,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        can_add_users=True,
    )

    admin_with_roles = UserWithRoles(
        id=admin_user.id,
        public_id=str(admin_user.public_id),
        organization_id=admin_user.organization_id,
        email=admin_user.email,
        username=admin_user.username,
        full_name=admin_user.full_name,
        is_active=admin_user.is_active,
        email_verified=admin_user.email_verified,
        roles=['ORG_ADMIN'],
        invited_by_id=None,
        invitation_status='pending',  # Pending until first login
        invitation_accepted_at=None,
        invitation_expires_at=None,
        last_login=None,
        created_at=admin_user.created_at,
    )

    return OrganizationCreatedResponse(
        organization=org_stats,
        admin_user=admin_with_roles,
        message=f"Organization '{organization.name}' created successfully with admin user '{admin_user.email}'"
    )


@router.post("/onboard-organization", response_model=OrganizationCreatedResponse)
async def onboard_organization(
    request: Request,
    org_request: CreateOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Onboard a new organization with an admin user.

    **Super Admin Only**

    This is the primary endpoint for onboarding new companies/organizations.
    It creates the organization, sets up an admin account with the ORG_ADMIN role,
    and sends a welcome email with login credentials.

    Takes:
    - Organization name, slug, description, plan
    - Admin email, username, password, full name

    Returns the created org and user details.
    """
    import secrets
    import logging
    from backend.notifications import email_notifier

    logger = logging.getLogger(__name__)
    logger.info(f"Onboarding organization: {org_request.name}")

    request_info = get_request_info(request)

    # Check if organization name or slug already exists
    existing = db.query(Organization).filter(
        (Organization.name == org_request.name) | (Organization.slug == org_request.slug)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization with this name or slug already exists"
        )

    # Check if admin email already exists
    existing_user = db.query(User).filter(User.email == org_request.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Check if admin username already exists
    existing_username = db.query(User).filter(User.username == org_request.admin_username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Use provided password or generate a temporary one
    temp_password = org_request.admin_password or secrets.token_urlsafe(12)

    # Create organization
    organization = Organization(
        name=org_request.name,
        slug=org_request.slug,
        description=org_request.description,
        subscription_plan=org_request.subscription_plan,
        max_users=org_request.max_users,
        billing_email=org_request.billing_email,
        is_active=True,
    )
    db.add(organization)
    db.flush()

    # Create admin user
    admin_user = User(
        organization_id=organization.id,
        email=org_request.admin_email,
        username=org_request.admin_username,
        full_name=org_request.admin_full_name,
        hashed_password=get_password_hash(temp_password),
        is_active=True,
        is_superuser=False,
        email_verified=True,
    )
    db.add(admin_user)
    db.flush()

    # Assign ORG_ADMIN role
    org_admin_role = db.query(Role).filter(Role.slug == 'org_admin').first()
    if not org_admin_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ORG_ADMIN role not found in database"
        )

    user_role = UserRole(
        user_id=admin_user.id,
        role_id=org_admin_role.id,
        organization_id=organization.id,
        assigned_by_id=current_user.id,
    )
    db.add(user_role)
    db.commit()
    db.refresh(organization)
    db.refresh(admin_user)
    logger.info(f"Organization {organization.name} created successfully")

    # Send welcome email in background thread (non-blocking)
    import threading
    from backend.config import settings

    def send_email_async():
        try:
            logger.info(f"Sending welcome email to {admin_user.email}...")
            email_notifier.send_welcome_email(
                to_email=admin_user.email,
                user_name=admin_user.full_name or admin_user.username,
                organization_name=organization.name,
                login_url=f"{settings.FRONTEND_URL}/login",
                temporary_password=temp_password,
            )
            logger.info(f"Welcome email sent to {admin_user.email}")
        except Exception as e:
            logger.warning("Failed to send welcome email to %s: %s", admin_user.email, str(e))

    # Start email in background - don't wait for it
    email_thread = threading.Thread(target=send_email_async)
    email_thread.start()

    # Log action
    log_organization_action(
        db=db,
        user=current_user,
        action="organization.onboarded",
        organization_id=organization.id,
        details={
            "organization_name": organization.name,
            "subscription_plan": organization.subscription_plan,
            "admin_email": admin_user.email,
        },
        ip_address=request_info["ip_address"],
    )

    # Prepare response
    org_stats = OrganizationWithStats(
        id=organization.id,
        public_id=str(organization.public_id),
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        is_active=organization.is_active,
        can_sync_data=organization.can_sync_data,
        subscription_plan=organization.subscription_plan,
        max_users=organization.max_users,
        current_user_count=1,
        subscription_status=organization.subscription_status,
        trial_ends_at=organization.trial_ends_at,
        billing_email=organization.billing_email,
        admin_onboarded=organization.admin_onboarded,
        admin_onboarded_at=organization.admin_onboarded_at,
        logo_url=organization.logo_url,
        brand_primary_color=organization.brand_primary_color,
        brand_secondary_color=organization.brand_secondary_color,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        can_add_users=True,
    )

    admin_with_roles = UserWithRoles(
        id=admin_user.id,
        public_id=str(admin_user.public_id),
        organization_id=admin_user.organization_id,
        email=admin_user.email,
        username=admin_user.username,
        full_name=admin_user.full_name,
        is_active=admin_user.is_active,
        email_verified=admin_user.email_verified,
        roles=['ORG_ADMIN'],
        invited_by_id=None,
        invitation_status='pending',
        invitation_accepted_at=None,
        invitation_expires_at=None,
        last_login=None,
        created_at=admin_user.created_at,
    )

    return OrganizationCreatedResponse(
        organization=org_stats,
        admin_user=admin_with_roles,
        message=f"Organization '{organization.name}' onboarded successfully. Welcome email sent to '{admin_user.email}'."
    )


@router.get("/organizations", response_model=List[OrganizationWithStats])
async def list_all_organizations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    List all organizations in the platform.

    **Super Admin Only**

    Returns all organizations with usage statistics.
    Excludes the system 'platform' organization.
    """
    orgs = db.query(Organization).filter(
        Organization.slug != "platform"  # Exclude system org
    ).offset(skip).limit(limit).all()

    org_stats_list = []
    for org in orgs:
        org_stats_list.append(OrganizationWithStats(
            id=org.id,
            public_id=str(org.public_id),
            name=org.name,
            slug=org.slug,
            description=org.description,
            is_active=org.is_active,
            can_sync_data=org.can_sync_data,
            subscription_plan=org.subscription_plan,
            max_users=org.max_users,
            current_user_count=org.current_user_count,
            subscription_status=org.subscription_status,
            trial_ends_at=org.trial_ends_at,
            billing_email=org.billing_email,
            admin_onboarded=org.admin_onboarded,
            admin_onboarded_at=org.admin_onboarded_at,
            logo_url=org.logo_url,
            brand_primary_color=org.brand_primary_color,
            brand_secondary_color=org.brand_secondary_color,
            created_at=org.created_at,
            updated_at=org.updated_at,
            can_add_users=org.can_add_users,
        ))

    return org_stats_list


@router.put("/organizations/{org_id}/subscription", response_model=OrganizationWithStats)
async def update_organization_subscription(
    request: Request,
    org_id: int,
    subscription: OrganizationSubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Update an organization's subscription plan.

    **Super Admin Only**

    Changes subscription plan and user limits.
    """
    request_info = get_request_info(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    old_plan = org.subscription_plan
    old_max_users = org.max_users

    org.subscription_plan = subscription.subscription_plan
    if subscription.max_users:
        org.max_users = subscription.max_users

    db.commit()
    db.refresh(org)

    # Log action
    log_organization_action(
        db=db,
        user=current_user,
        action="subscription.updated",
        organization_id=org.id,
        details={
            "old_plan": old_plan,
            "new_plan": org.subscription_plan,
            "old_max_users": old_max_users,
            "new_max_users": org.max_users,
        },
        ip_address=request_info["ip_address"],
    )

    return OrganizationWithStats(
        id=org.id,
        public_id=str(org.public_id),
        name=org.name,
        slug=org.slug,
        description=org.description,
        is_active=org.is_active,
        can_sync_data=org.can_sync_data,
        subscription_plan=org.subscription_plan,
        max_users=org.max_users,
        current_user_count=org.current_user_count,
        subscription_status=org.subscription_status,
        trial_ends_at=org.trial_ends_at,
        billing_email=org.billing_email,
        admin_onboarded=org.admin_onboarded,
        admin_onboarded_at=org.admin_onboarded_at,
        logo_url=org.logo_url,
        brand_primary_color=org.brand_primary_color,
        brand_secondary_color=org.brand_secondary_color,
        created_at=org.created_at,
        updated_at=org.updated_at,
        can_add_users=org.can_add_users,
    )


@router.get("/stats", response_model=PlatformStats)
async def get_platform_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Get platform-wide statistics.

    **Super Admin Only**

    Returns:
    - Total organizations and users
    - Pipeline and run statistics
    - Organizations breakdown by plan
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import func

    # Count organizations
    total_orgs = db.query(func.count(Organization.id)).scalar()
    active_orgs = db.query(func.count(Organization.id)).filter(Organization.is_active == True).scalar()

    # Count users
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()

    # Count pipelines
    total_pipelines = db.query(func.count(Pipeline.id)).scalar()

    # Count runs
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    runs_today = db.query(func.count(PipelineRun.id)).filter(
        PipelineRun.created_at >= today_start
    ).scalar()

    runs_week = db.query(func.count(PipelineRun.id)).filter(
        PipelineRun.created_at >= week_start
    ).scalar()

    runs_month = db.query(func.count(PipelineRun.id)).filter(
        PipelineRun.created_at >= month_start
    ).scalar()

    # Organizations by plan
    orgs_by_plan = {}
    for plan in ['starter', 'professional', 'enterprise']:
        count = db.query(func.count(Organization.id)).filter(
            Organization.subscription_plan == plan
        ).scalar()
        orgs_by_plan[plan] = count or 0

    return PlatformStats(
        total_organizations=total_orgs or 0,
        active_organizations=active_orgs or 0,
        total_users=total_users or 0,
        active_users=active_users or 0,
        total_pipelines=total_pipelines or 0,
        total_runs_today=runs_today or 0,
        total_runs_this_week=runs_week or 0,
        total_runs_this_month=runs_month or 0,
        organizations_by_plan=orgs_by_plan,
    )


@router.patch("/organizations/{org_id}/disable-sync")
async def disable_organization_sync(
    request: Request,
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Disable data syncing for an organization (soft warning).

    **Super Admin Only**

    Users can still login and view data, but cannot run pipelines.
    Use this as a warning before full deactivation (for non-payment, etc).
    """
    request_info = get_request_info(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    org.can_sync_data = False
    db.commit()

    # Log action
    log_organization_action(
        db=db,
        user=current_user,
        action="organization.sync_disabled",
        organization_id=org.id,
        details={
            "organization_name": org.name,
            "reason": "Manual disable by super admin"
        },
        ip_address=request_info["ip_address"],
    )

    return {
        "message": f"Data syncing disabled for {org.name}",
        "organization_id": org.id,
        "can_sync_data": org.can_sync_data
    }


@router.patch("/organizations/{org_id}/enable-sync")
async def enable_organization_sync(
    request: Request,
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Re-enable data syncing for an organization.

    **Super Admin Only**
    """
    request_info = get_request_info(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    org.can_sync_data = True
    db.commit()

    # Log action
    log_organization_action(
        db=db,
        user=current_user,
        action="organization.sync_enabled",
        organization_id=org.id,
        details={
            "organization_name": org.name,
        },
        ip_address=request_info["ip_address"],
    )

    return {
        "message": f"Data syncing enabled for {org.name}",
        "organization_id": org.id,
        "can_sync_data": org.can_sync_data
    }


@router.patch("/organizations/{org_id}/deactivate")
async def deactivate_organization(
    request: Request,
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Completely deactivate an organization (hard shutdown).

    **Super Admin Only**

    Users cannot login, no access to any data or features.
    Use this for organizations that left, refused to pay, or violated terms.
    """
    request_info = get_request_info(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    org.is_active = False
    org.can_sync_data = False  # Also disable syncing
    db.commit()

    # Log action
    log_organization_action(
        db=db,
        user=current_user,
        action="organization.deactivated",
        organization_id=org.id,
        details={
            "organization_name": org.name,
            "user_count": org.current_user_count,
            "subscription_plan": org.subscription_plan,
        },
        ip_address=request_info["ip_address"],
    )

    return {
        "message": f"Organization {org.name} completely deactivated",
        "organization_id": org.id,
        "is_active": org.is_active,
        "can_sync_data": org.can_sync_data
    }


@router.patch("/organizations/{org_id}/activate")
async def activate_organization(
    request: Request,
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Reactivate a deactivated organization.

    **Super Admin Only**

    Restores full access and data syncing.
    """
    request_info = get_request_info(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    org.is_active = True
    org.can_sync_data = True
    db.commit()

    # Log action
    log_organization_action(
        db=db,
        user=current_user,
        action="organization.activated",
        organization_id=org.id,
        details={
            "organization_name": org.name,
        },
        ip_address=request_info["ip_address"],
    )

    return {
        "message": f"Organization {org.name} reactivated",
        "organization_id": org.id,
        "is_active": org.is_active,
        "can_sync_data": org.can_sync_data
    }


@router.delete("/organizations/{org_id}")
async def delete_pending_organization(
    request: Request,
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Delete a pending organization that hasn't onboarded yet.

    **Super Admin Only**

    Can only delete organizations where admin_onboarded = False.
    Use this to remove organizations created by mistake or that never logged in.
    For active organizations, use deactivate endpoint instead.
    """
    request_info = get_request_info(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Protect the platform organization from deletion
    if org.slug == "platform":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete the platform organization"
        )

    # Only allow deleting organizations that haven't onboarded
    if org.admin_onboarded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete organization that has already onboarded. Use deactivate instead."
        )

    org_name = org.name
    org_id_val = org.id

    # Log action before deletion
    log_organization_action(
        db=db,
        user=current_user,
        action="organization.deleted",
        organization_id=org.id,
        details={
            "organization_name": org.name,
            "subscription_plan": org.subscription_plan,
            "reason": "Pending organization deleted (never onboarded)",
        },
        ip_address=request_info["ip_address"],
    )

    # Delete the organization (cascade will delete users, roles, etc.)
    db.delete(org)
    db.commit()

    return {
        "message": f"Pending organization '{org_name}' deleted successfully",
        "organization_id": org_id_val,
    }
