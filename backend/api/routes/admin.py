"""
Admin API routes (Super Admin only).

Endpoints for platform administration:
- Create organizations
- Manage subscriptions
- View platform statistics
- Manage all users
"""

import hashlib
import secrets
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Organization, User, Pipeline, PipelineRun, UserRole, Role, DataSource, Destination
from backend.models.audit import ImpersonationSession
from backend.models.billing import (
    Subscription,
    SubscriptionPlan,
    REGIONAL_PRICING,
    currency_for_country,
)
from backend.auth import require_super_admin, get_password_hash, get_request_info
from backend.schemas.rbac import (
    CreateOrganizationRequest,
    OrganizationCreatedResponse,
    OrganizationWithStats,
    OrganizationSubscriptionUpdate,
    PlatformStats,
    UserWithRoles,
)
from backend.rbac.audit import log_organization_action, log_super_admin_access


router = APIRouter(prefix="/admin", tags=["admin"])


def _create_org_subscription(db: Session, organization: Organization, plan_str: str, country: Optional[str]) -> Subscription:
    """Create the org's subscription with its country's billing currency.

    Purchasing-power pricing: the country decides which market price the
    org gets (see COUNTRY_CURRENCY / REGIONAL_PRICING in models/billing.py).
    """
    try:
        plan = SubscriptionPlan(plan_str)
    except ValueError:
        plan = SubscriptionPlan.STARTER

    subscription = Subscription(
        organization_id=organization.id,
        plan=plan,
        currency=currency_for_country(country),
    )
    db.add(subscription)
    return subscription


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
        country=org_request.country,
        subscription_plan=org_request.subscription_plan,
        max_users=org_request.max_users,
        billing_email=org_request.billing_email,
        is_active=True,
    )
    db.add(organization)
    db.flush()  # Get organization ID

    # Billing currency follows the org's country (purchasing-power pricing)
    _create_org_subscription(db, organization, org_request.subscription_plan, org_request.country)

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
        country=org_request.country,
        subscription_plan=org_request.subscription_plan,
        max_users=org_request.max_users,
        billing_email=org_request.billing_email,
        is_active=True,
    )
    db.add(organization)
    db.flush()

    # Billing currency follows the org's country (purchasing-power pricing)
    _create_org_subscription(db, organization, org_request.subscription_plan, org_request.country)

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
    active_orgs = db.query(func.count(Organization.id)).filter(Organization.is_active).scalar()

    # Count users
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active).scalar()

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


class BillingCurrencyUpdate(BaseModel):
    currency: str


@router.patch("/organizations/{org_id}/billing-currency")
async def update_billing_currency(
    request: Request,
    org_id: int,
    payload: BillingCurrencyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Change an organization's billing currency.

    **Super Admin Only**

    The currency must be one of the deliberately priced markets in
    REGIONAL_PRICING (purchasing-power pricing — never an FX conversion).
    """
    request_info = get_request_info(request)

    currency = payload.currency.strip().upper()
    if currency not in REGIONAL_PRICING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported billing currency. Must be one of: {', '.join(sorted(REGIONAL_PRICING))}",
        )

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    subscription = db.query(Subscription).filter(
        Subscription.organization_id == org.id
    ).first()
    if not subscription:
        subscription = _create_org_subscription(db, org, org.subscription_plan, None)
    old_currency = subscription.currency
    subscription.currency = currency
    db.commit()

    log_organization_action(
        db=db,
        user=current_user,
        action="organization.billing_currency_changed",
        organization_id=org.id,
        details={
            "organization_name": org.name,
            "old_currency": old_currency,
            "new_currency": currency,
        },
        ip_address=request_info["ip_address"],
    )

    return {
        "message": f"Billing currency for {org.name} set to {currency}",
        "organization_id": org.id,
        "currency": currency,
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


class ForceDeleteRequest(BaseModel):
    reason: str


@router.delete("/organizations/{org_id}/force")
async def force_delete_organization(
    request: Request,
    org_id: int,
    body: ForceDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Permanently delete any organization, including fully onboarded ones.

    **Super Admin Only**

    All associated data (users, pipelines, sources, destinations, runs,
    billing records, audit logs) is deleted via database cascade.
    This action is irreversible. A reason must be provided for audit purposes.
    """
    request_info = get_request_info(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    if org.slug in ["platform", "platform-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete the platform administration organization"
        )

    org_name = org.name
    org_id_val = org.id
    user_count = db.query(User).filter(User.organization_id == org_id).count()
    pipeline_count = db.query(Pipeline).filter(Pipeline.organization_id == org_id).count()

    log_organization_action(
        db=db,
        user=current_user,
        action="organization.force_deleted",
        organization_id=org.id,
        details={
            "organization_name": org.name,
            "slug": org.slug,
            "subscription_plan": org.subscription_plan,
            "admin_onboarded": org.admin_onboarded,
            "user_count": user_count,
            "pipeline_count": pipeline_count,
            "reason": body.reason,
            "deleted_by": current_user.email,
        },
        ip_address=request_info["ip_address"],
    )

    db.delete(org)
    db.commit()

    return {
        "message": f"Organization '{org_name}' permanently deleted",
        "organization_id": org_id_val,
        "users_deleted": user_count,
        "pipelines_deleted": pipeline_count,
    }


@router.delete("/organizations/by-slug/{slug}")
async def force_delete_organization_by_slug(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Force delete an organization by slug (for cleanup purposes).

    **Super Admin Only**

    Use this to clean up stuck/orphaned organizations.
    """
    request_info = get_request_info(request)

    org = db.query(Organization).filter(Organization.slug == slug).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with slug '{slug}' not found"
        )

    # Protect the platform organization
    if org.slug in ["platform", "platform-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system organizations"
        )

    org_name = org.name
    org_id = org.id

    # Log before deletion
    log_organization_action(
        db=db,
        user=current_user,
        action="organization.force_deleted",
        organization_id=org.id,
        details={"organization_name": org.name, "slug": slug},
        ip_address=request_info["ip_address"],
    )

    db.delete(org)
    db.commit()

    return {"message": f"Organization '{org_name}' (slug: {slug}) deleted", "id": org_id}


# ==================== CROSS-ORG ACCESS ENDPOINTS ====================


class OrganizationDetailResponse(BaseModel):
    """Detailed organization information with resources."""
    id: int
    public_id: str
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    can_sync_data: bool
    subscription_plan: str
    max_users: int
    current_user_count: int
    logo_url: Optional[str]
    created_at: str
    pipelines_count: int
    sources_count: int
    destinations_count: int
    recent_runs_count: int


class PipelineSummary(BaseModel):
    """Pipeline summary for admin view."""
    id: int
    public_id: str
    name: str
    description: Optional[str]
    is_active: bool
    schedule: Optional[str]
    last_run_status: Optional[str]
    last_run_at: Optional[str]
    created_at: str


class RunSummary(BaseModel):
    """Run summary for admin view."""
    id: int
    public_id: str
    pipeline_id: int
    pipeline_name: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[float]
    rows_written: Optional[int]
    error_message: Optional[str]
    created_at: str


class ImpersonationResponse(BaseModel):
    """Impersonation session response."""
    impersonation_token: str
    target_org_id: int
    target_org_name: str
    expires_at: str
    message: str


@router.get("/organizations/{org_id}/details", response_model=OrganizationDetailResponse)
async def get_organization_details(
    request: Request,
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Get detailed information about an organization.

    **Super Admin Only**

    Returns organization details with resource counts.
    """
    from datetime import datetime, timedelta, timezone as tz

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Log access
    log_super_admin_access(
        db=db,
        super_admin=current_user,
        target_org_id=org_id,
        action="view_organization_details",
        resource_type="organization",
        resource_id=str(org.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Count resources
    pipelines_count = db.query(Pipeline).filter(Pipeline.organization_id == org_id).count()
    sources_count = db.query(DataSource).filter(DataSource.organization_id == org_id).count()
    destinations_count = db.query(Destination).filter(Destination.organization_id == org_id).count()

    # Count recent runs (last 7 days)
    week_ago = datetime.now(tz.utc) - timedelta(days=7)
    recent_runs_count = db.query(PipelineRun).join(Pipeline).filter(
        Pipeline.organization_id == org_id,
        PipelineRun.created_at >= week_ago
    ).count()

    return OrganizationDetailResponse(
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
        logo_url=org.logo_url,
        created_at=org.created_at.isoformat(),
        pipelines_count=pipelines_count,
        sources_count=sources_count,
        destinations_count=destinations_count,
        recent_runs_count=recent_runs_count,
    )


@router.get("/organizations/{org_id}/pipelines")
async def list_organization_pipelines(
    request: Request,
    org_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    List all pipelines for a specific organization.

    **Super Admin Only** - READ ONLY

    Returns pipelines with their status and last run info.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Log access
    log_super_admin_access(
        db=db,
        super_admin=current_user,
        target_org_id=org_id,
        action="view_org_pipelines",
        resource_type="pipeline",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    pipelines = db.query(Pipeline).filter(
        Pipeline.organization_id == org_id
    ).offset(skip).limit(limit).all()

    result = []
    for pipeline in pipelines:
        # Get last run
        last_run = db.query(PipelineRun).filter(
            PipelineRun.pipeline_id == pipeline.id
        ).order_by(PipelineRun.created_at.desc()).first()

        result.append({
            "id": pipeline.id,
            "public_id": str(pipeline.public_id),
            "name": pipeline.name,
            "description": pipeline.description,
            "is_active": pipeline.is_active,
            "schedule": pipeline.schedule,
            "last_run_status": last_run.status.value if last_run else None,
            "last_run_at": last_run.created_at.isoformat() if last_run else None,
            "created_at": pipeline.created_at.isoformat(),
        })

    return {
        "organization_id": org_id,
        "organization_name": org.name,
        "pipelines": result,
        "total": len(result),
    }


@router.get("/organizations/{org_id}/runs")
async def list_organization_runs(
    request: Request,
    org_id: int,
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    List all pipeline runs for a specific organization.

    **Super Admin Only** - READ ONLY

    Returns recent runs with status and details.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Log access
    log_super_admin_access(
        db=db,
        super_admin=current_user,
        target_org_id=org_id,
        action="view_org_runs",
        resource_type="run",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    query = db.query(PipelineRun).join(Pipeline).filter(
        Pipeline.organization_id == org_id
    )

    if status_filter:
        query = query.filter(PipelineRun.status == status_filter)

    runs = query.order_by(PipelineRun.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for run in runs:
        result.append({
            "id": run.id,
            "public_id": str(run.public_id),
            "pipeline_id": run.pipeline_id,
            "pipeline_name": run.pipeline.name if run.pipeline else None,
            "status": run.status.value,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "duration_seconds": run.duration_seconds,
            "rows_written": run.rows_written,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat(),
        })

    return {
        "organization_id": org_id,
        "organization_name": org.name,
        "runs": result,
        "total": len(result),
    }


@router.get("/organizations/{org_id}/runs/{run_id}")
async def get_organization_run_details(
    request: Request,
    org_id: int,
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Get detailed information about a specific pipeline run including logs.

    **Super Admin Only** - READ ONLY
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    run = db.query(PipelineRun).join(Pipeline).filter(
        PipelineRun.id == run_id,
        Pipeline.organization_id == org_id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    # Log access
    log_super_admin_access(
        db=db,
        super_admin=current_user,
        target_org_id=org_id,
        action="view_run_details",
        resource_type="run",
        resource_id=str(run_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "id": run.id,
        "public_id": str(run.public_id),
        "pipeline_id": run.pipeline_id,
        "pipeline_name": run.pipeline.name if run.pipeline else None,
        "status": run.status.value,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_seconds": run.duration_seconds,
        "rows_written": run.rows_written,
        "bytes_written": run.bytes_written,
        "error_message": run.error_message,
        "error_traceback": run.error_traceback,
        "run_metadata": run.run_metadata,
        "created_at": run.created_at.isoformat(),
        "organization_id": org_id,
        "organization_name": org.name,
    }


@router.get("/organizations/{org_id}/sources")
async def list_organization_sources(
    request: Request,
    org_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    List all data sources for a specific organization.

    **Super Admin Only** - READ ONLY

    Note: Connection credentials are NOT exposed for security.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Log access
    log_super_admin_access(
        db=db,
        super_admin=current_user,
        target_org_id=org_id,
        action="view_org_sources",
        resource_type="source",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    sources = db.query(DataSource).filter(
        DataSource.organization_id == org_id
    ).offset(skip).limit(limit).all()

    result = []
    for source in sources:
        result.append({
            "id": source.id,
            "public_id": str(source.public_id),
            "name": source.name,
            "description": source.description,
            "source_type": source.source_type.value,
            "is_active": source.is_active,
            "created_at": source.created_at.isoformat(),
            # NOTE: config is NOT exposed for security
        })

    return {
        "organization_id": org_id,
        "organization_name": org.name,
        "sources": result,
        "total": len(result),
    }


@router.get("/organizations/{org_id}/destinations")
async def list_organization_destinations(
    request: Request,
    org_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    List all destinations for a specific organization.

    **Super Admin Only** - READ ONLY

    Note: Connection credentials are NOT exposed for security.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Log access
    log_super_admin_access(
        db=db,
        super_admin=current_user,
        target_org_id=org_id,
        action="view_org_destinations",
        resource_type="destination",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    destinations = db.query(Destination).filter(
        Destination.organization_id == org_id
    ).offset(skip).limit(limit).all()

    result = []
    for dest in destinations:
        result.append({
            "id": dest.id,
            "public_id": str(dest.public_id),
            "name": dest.name,
            "description": dest.description,
            "destination_type": dest.destination_type.value,
            "is_active": dest.is_active,
            "created_at": dest.created_at.isoformat(),
            # NOTE: config is NOT exposed for security
        })

    return {
        "organization_id": org_id,
        "organization_name": org.name,
        "destinations": result,
        "total": len(result),
    }


@router.get("/organizations/{org_id}/team")
async def list_organization_team(
    request: Request,
    org_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    List all team members for a specific organization.

    **Super Admin Only** - READ ONLY
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Log access
    log_super_admin_access(
        db=db,
        super_admin=current_user,
        target_org_id=org_id,
        action="view_org_team",
        resource_type="user",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    users = db.query(User).filter(
        User.organization_id == org_id
    ).offset(skip).limit(limit).all()

    result = []
    for user in users:
        result.append({
            "id": user.id,
            "public_id": str(user.public_id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "roles": user.role_names,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat(),
        })

    return {
        "organization_id": org_id,
        "organization_name": org.name,
        "team": result,
        "total": len(result),
    }


# ==================== IMPERSONATION ENDPOINTS ====================

IMPERSONATION_TOKEN_EXPIRY_MINUTES = 15


@router.post("/impersonate/{org_id}", response_model=ImpersonationResponse)
async def start_impersonation(
    request: Request,
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Start an impersonation session for a specific organization.

    **Super Admin Only**

    Creates a temporary token that allows viewing the dashboard as if
    logged in as that organization. Token expires in 15 minutes.

    IMPORTANT: Impersonation is READ-ONLY. No modifications can be made.
    All impersonation access is fully logged.
    """
    from datetime import datetime, timezone as tz

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Cannot impersonate the platform organization
    if org.slug == "platform":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate the platform organization"
        )

    # End any existing active sessions for this admin
    db.query(ImpersonationSession).filter(
        ImpersonationSession.super_admin_id == current_user.id,
        ImpersonationSession.is_active,
    ).update({"is_active": False, "ended_at": datetime.now(tz.utc)})

    # Generate impersonation token
    raw_token = secrets.token_urlsafe(32)
    impersonation_token = f"imp_{raw_token}"
    token_hash = hashlib.sha256(impersonation_token.encode()).hexdigest()

    # Create session
    expires_at = datetime.now(tz.utc) + timedelta(minutes=IMPERSONATION_TOKEN_EXPIRY_MINUTES)

    session = ImpersonationSession(
        super_admin_id=current_user.id,
        target_org_id=org_id,
        token_hash=token_hash,
        expires_at=expires_at,
        is_active=True,
        ip_address=request.client.host if request.client else None,
    )
    db.add(session)
    db.commit()

    # Log impersonation start
    log_super_admin_access(
        db=db,
        super_admin=current_user,
        target_org_id=org_id,
        action="impersonation_started",
        resource_type="organization",
        resource_id=str(org_id),
        details={"session_id": session.id, "expires_at": expires_at.isoformat()},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Log organization action
    log_organization_action(
        db=db,
        user=current_user,
        action="impersonation.started",
        organization_id=org_id,
        details={
            "admin_email": current_user.email,
            "expires_at": expires_at.isoformat(),
        },
        ip_address=request.client.host if request.client else None,
    )

    return ImpersonationResponse(
        impersonation_token=impersonation_token,
        target_org_id=org_id,
        target_org_name=org.name,
        expires_at=expires_at.isoformat(),
        message=f"Impersonation session started for '{org.name}'. Token expires in {IMPERSONATION_TOKEN_EXPIRY_MINUTES} minutes.",
    )


@router.post("/stop-impersonate")
async def stop_impersonation(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    End the current impersonation session.

    **Super Admin Only**

    Ends all active impersonation sessions for the current admin.
    """
    from datetime import datetime, timezone as tz

    # Find and end active sessions
    active_sessions = db.query(ImpersonationSession).filter(
        ImpersonationSession.super_admin_id == current_user.id,
        ImpersonationSession.is_active,
    ).all()

    ended_count = 0
    for session in active_sessions:
        session.is_active = False
        session.ended_at = datetime.now(tz.utc)
        ended_count += 1

        # Log impersonation end
        log_super_admin_access(
            db=db,
            super_admin=current_user,
            target_org_id=session.target_org_id,
            action="impersonation_ended",
            resource_type="organization",
            resource_id=str(session.target_org_id),
            details={"session_id": session.id},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    db.commit()

    return {
        "message": f"Ended {ended_count} impersonation session(s)",
        "sessions_ended": ended_count,
    }


@router.get("/impersonation/current")
async def get_current_impersonation(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Get the current active impersonation session if any.

    **Super Admin Only**
    """
    from datetime import datetime, timezone as tz

    session = db.query(ImpersonationSession).filter(
        ImpersonationSession.super_admin_id == current_user.id,
        ImpersonationSession.is_active,
        ImpersonationSession.expires_at > datetime.now(tz.utc),
    ).first()

    if not session:
        return {"active": False, "session": None}

    org = db.query(Organization).filter(Organization.id == session.target_org_id).first()

    return {
        "active": True,
        "session": {
            "target_org_id": session.target_org_id,
            "target_org_name": org.name if org else None,
            "target_org_slug": org.slug if org else None,
            "target_org_logo": org.logo_url if org else None,
            "started_at": session.started_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
        },
    }


@router.get("/access-logs")
async def get_super_admin_access_logs(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    target_org_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Get super admin cross-org access logs.

    **Super Admin Only**

    View audit trail of all cross-organization access by super admins.
    """
    from backend.models.audit import SuperAdminAccessLog

    query = db.query(SuperAdminAccessLog)

    if target_org_id:
        query = query.filter(SuperAdminAccessLog.target_org_id == target_org_id)

    logs = query.order_by(SuperAdminAccessLog.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "super_admin_id": log.super_admin_id,
            "super_admin_email": log.super_admin.email if log.super_admin else None,
            "target_org_id": log.target_org_id,
            "target_org_name": log.target_organization.name if log.target_organization else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        })

    return {
        "logs": result,
        "total": len(result),
    }
