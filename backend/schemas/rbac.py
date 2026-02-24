"""
Pydantic schemas for RBAC system.

These schemas define request/response models for:
- Roles and permissions
- User role assignments
- User invitations
- Audit logs
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


# ==================== ROLE SCHEMAS ====================

class PermissionResponse(BaseModel):
    """Permission response schema"""
    id: int
    resource: str
    action: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """Role response schema"""
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    scope: str
    created_at: datetime
    permissions: Optional[List[PermissionResponse]] = None

    class Config:
        from_attributes = True


class RoleWithPermissions(BaseModel):
    """Role with detailed permissions"""
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    scope: str
    permission_count: int
    permissions: List[PermissionResponse]

    class Config:
        from_attributes = True


# ==================== USER ROLE SCHEMAS ====================

class UserRoleResponse(BaseModel):
    """User role assignment response"""
    id: int
    user_id: int
    role_id: int
    role_name: str
    role_slug: str
    organization_id: Optional[int] = None
    assigned_by_id: Optional[int] = None
    assigned_at: datetime

    class Config:
        from_attributes = True


class AssignRoleRequest(BaseModel):
    """Request to assign role to user"""
    role_slug: str = Field(..., description="Role slug: super_admin, org_admin, or org_user")
    organization_id: Optional[int] = Field(None, description="Organization ID (required for org-scoped roles)")

    @field_validator('role_slug')
    @classmethod
    def validate_role_slug(cls, v):
        valid_roles = ['super_admin', 'org_admin', 'org_user']
        if v not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        return v


class ChangeUserRoleRequest(BaseModel):
    """Request to change a user's role"""
    role_slug: str = Field(..., description="New role: org_admin or org_user")

    @field_validator('role_slug')
    @classmethod
    def validate_role_slug(cls, v):
        valid_roles = ['org_admin', 'org_user']
        if v not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        return v


# ==================== INVITATION SCHEMAS ====================

class CreateInvitationRequest(BaseModel):
    """Request to invite a user"""
    email: EmailStr = Field(..., description="Email address of the person to invite")
    role_slug: str = Field(..., description="Role to assign: org_admin or org_user")

    @field_validator('role_slug')
    @classmethod
    def validate_role_slug(cls, v):
        valid_roles = ['org_admin', 'org_user']
        if v not in valid_roles:
            raise ValueError("Can only invite as org_admin or org_user")
        return v


class InvitationResponse(BaseModel):
    """Invitation response"""
    id: int
    public_id: str
    organization_id: int
    organization_name: Optional[str] = None
    email: str
    role_id: int
    role_name: str
    invited_by_id: int
    invited_by_name: Optional[str] = None
    token: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    status: str
    created_at: datetime
    is_expired: bool
    is_valid: bool

    class Config:
        from_attributes = True


class InvitationPublicResponse(BaseModel):
    """Public invitation response (for accept page, no sensitive data)"""
    public_id: str
    organization_name: str
    role_name: str
    email: str
    invited_by_name: Optional[str] = None
    expires_at: datetime
    is_valid: bool
    is_expired: bool


class AcceptInvitationRequest(BaseModel):
    """Request to accept invitation"""
    token: str = Field(..., description="Invitation token from email")
    username: str = Field(..., min_length=3, max_length=50, description="Choose a username")
    password: str = Field(..., min_length=8, description="Choose a strong password")
    full_name: Optional[str] = Field(None, max_length=255, description="Your full name")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v and '-' not in v:
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v.lower()


class ResendInvitationRequest(BaseModel):
    """Request to resend invitation email"""
    invitation_id: int


# ==================== AUDIT LOG SCHEMAS ====================

class AuditLogResponse(BaseModel):
    """Audit log response"""
    id: int
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogFilters(BaseModel):
    """Filters for audit log queries"""
    user_id: Optional[int] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


# ==================== ORGANIZATION SCHEMAS (EXTENDED) ====================

class OrganizationSubscriptionUpdate(BaseModel):
    """Update organization subscription"""
    subscription_plan: str = Field(..., description="Plan: starter, professional, or enterprise")
    max_users: Optional[int] = Field(None, ge=1, le=1000, description="Maximum users allowed")

    @field_validator('subscription_plan')
    @classmethod
    def validate_plan(cls, v):
        valid_plans = ['starter', 'professional', 'enterprise']
        if v not in valid_plans:
            raise ValueError(f"Invalid plan. Must be one of: {', '.join(valid_plans)}")
        return v


class OrganizationBrandingUpdate(BaseModel):
    """Update organization branding"""
    logo_url: Optional[str] = Field(None, max_length=500, description="Logo image URL")
    brand_primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="Primary brand color (hex)")
    brand_secondary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="Secondary brand color (hex)")

    @field_validator('logo_url')
    @classmethod
    def validate_logo_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Logo URL must start with http:// or https://")
        return v


class OrganizationWithStats(BaseModel):
    """Organization with usage statistics"""
    id: int
    public_id: str
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    can_sync_data: bool
    subscription_plan: str
    max_users: int
    current_user_count: int
    subscription_status: str
    trial_ends_at: Optional[datetime] = None
    billing_email: Optional[str] = None
    admin_onboarded: bool = False  # Has admin logged in?
    admin_onboarded_at: Optional[datetime] = None  # When admin first logged in
    logo_url: Optional[str] = None
    brand_primary_color: Optional[str] = None
    brand_secondary_color: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    can_add_users: bool

    class Config:
        from_attributes = True


# ==================== USER SCHEMAS (EXTENDED) ====================

class UserWithRoles(BaseModel):
    """User with their roles"""
    id: int
    public_id: str
    organization_id: int
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    email_verified: bool
    roles: List[str]  # List of role names
    invited_by_id: Optional[int] = None
    invitation_status: Optional[str] = None  # pending, accepted, cancelled, expired
    invitation_accepted_at: Optional[datetime] = None
    invitation_expires_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserListItem(BaseModel):
    """Simplified user for list views"""
    id: int
    public_id: str
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    roles: List[str]
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== PERMISSION CHECK SCHEMAS ====================

class PermissionCheckRequest(BaseModel):
    """Request to check if user has permission"""
    resource: str
    action: str


class PermissionCheckResponse(BaseModel):
    """Response for permission check"""
    has_permission: bool
    reason: Optional[str] = None


class UserPermissionsResponse(BaseModel):
    """All permissions for a user"""
    user_id: int
    roles: List[str]
    permissions: List[PermissionResponse]
    is_super_admin: bool
    is_org_admin: bool


# ==================== ADMIN SCHEMAS ====================

class CreateOrganizationRequest(BaseModel):
    """Super admin request to create organization"""
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    subscription_plan: str = Field(default="starter")
    max_users: int = Field(default=3, ge=1)
    admin_email: EmailStr = Field(..., description="Email for the organization admin")
    admin_username: str = Field(..., min_length=3, max_length=50)
    admin_password: str = Field(..., min_length=8)
    admin_full_name: Optional[str] = None
    billing_email: Optional[EmailStr] = None

    @field_validator('subscription_plan')
    @classmethod
    def validate_plan(cls, v):
        valid_plans = ['starter', 'professional', 'enterprise']
        if v not in valid_plans:
            raise ValueError(f"Invalid plan. Must be one of: {', '.join(valid_plans)}")
        return v


class OrganizationCreatedResponse(BaseModel):
    """Response when organization is created"""
    organization: OrganizationWithStats
    admin_user: UserWithRoles
    message: str


# ==================== STATS & ANALYTICS SCHEMAS ====================

class OrganizationStats(BaseModel):
    """Organization usage statistics"""
    organization_id: int
    total_users: int
    active_users: int
    max_users: int
    usage_percentage: float
    total_pipelines: int
    active_pipelines: int
    total_runs: int
    successful_runs: int
    failed_runs: int
    subscription_plan: str


class PlatformStats(BaseModel):
    """Platform-wide statistics (super admin only)"""
    total_organizations: int
    active_organizations: int
    total_users: int
    active_users: int
    total_pipelines: int
    total_runs_today: int
    total_runs_this_week: int
    total_runs_this_month: int
    organizations_by_plan: Dict[str, int]
