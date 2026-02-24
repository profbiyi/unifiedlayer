"""
RBAC (Role-Based Access Control) Models

This module defines models for the role-based access control system including:
- Roles: Define user roles (SUPER_ADMIN, ORG_ADMIN, ORG_USER)
- Permissions: Granular permissions (resource:action pairs)
- User Roles: Assignment of roles to users
- User Invitations: Invitation system for adding users to organizations
- Audit Logs: Track all user actions for security and compliance
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from backend.database import Base


class Role(Base):
    """
    Roles define what a user can do.

    Scopes:
    - 'global': Platform-wide role (SUPER_ADMIN)
    - 'organization': Organization-scoped role (ORG_ADMIN, ORG_USER)
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # SUPER_ADMIN, ORG_ADMIN, ORG_USER
    slug = Column(String(50), unique=True, nullable=False)  # super_admin, org_admin, org_user
    description = Column(Text, nullable=True)
    scope = Column(String(20), nullable=False)  # 'global' or 'organization'
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    invitations = relationship("UserInvitation", back_populates="role")

    def __repr__(self):
        return f"<Role {self.name}>"


class Permission(Base):
    """
    Permissions define granular actions on resources.

    Examples:
    - resource='pipeline', action='create'
    - resource='user', action='delete'
    - resource='organization', action='manage_users'
    """
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint('resource', 'action', name='uq_resource_action'),
    )

    id = Column(Integer, primary_key=True, index=True)
    resource = Column(String(50), nullable=False)  # pipeline, source, destination, user, etc.
    action = Column(String(50), nullable=False)    # create, read, update, delete, execute, etc.
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Permission {self.resource}:{self.action}>"


class RolePermission(Base):
    """
    Junction table mapping roles to permissions.
    Defines which permissions each role has.
    """
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="role_permissions")

    def __repr__(self):
        return f"<RolePermission role_id={self.role_id} permission_id={self.permission_id}>"


class UserRole(Base):
    """
    Assigns roles to users within organizations.

    - Super admins have organization_id=None (global scope)
    - Org admins and users have organization_id set (organization scope)
    """
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', 'organization_id', name='uq_user_role_org'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    assigned_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    organization = relationship("Organization")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])

    def __repr__(self):
        return f"<UserRole user_id={self.user_id} role={self.role.name if self.role else None}>"


class UserInvitation(Base):
    """
    Manages user invitations to organizations.

    Flow:
    1. Org admin creates invitation with email and role
    2. System generates unique token and sends email
    3. User clicks link and accepts invitation
    4. User account created and role assigned
    """
    __tablename__ = "user_invitations"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, nullable=False)  # UUID for public reference
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    token = Column(String(255), unique=True, nullable=False)  # Secure token for invitation link
    expires_at = Column(DateTime, nullable=False)  # Token expiration (typically 7 days)
    accepted_at = Column(DateTime, nullable=True)  # When invitation was accepted
    status = Column(String(20), nullable=False, default='pending', index=True)  # pending, accepted, expired, cancelled
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    role = relationship("Role", back_populates="invitations")
    invited_by = relationship("User")

    def __repr__(self):
        return f"<UserInvitation {self.email} -> {self.organization.name if self.organization else None} ({self.status})>"

    @property
    def is_expired(self):
        """Check if invitation has expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self):
        """Check if invitation can still be accepted"""
        return self.status == 'pending' and not self.is_expired


# APIKey model moved to backend.models.api_key
from backend.models.api_key import APIKey  # noqa: F401 - re-export for backward compatibility


# AuditLog model moved to backend.models.audit
from backend.models.audit import AuditLog  # noqa: F401 - re-export for backward compatibility
