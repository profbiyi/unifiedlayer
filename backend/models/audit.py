"""
Audit Log ORM Model.

Tracks user actions across the platform for security and compliance.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class AuditLog(Base):
    """
    Audit Log model.

    Records user actions for security auditing and compliance.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    # SET NULL to preserve audit trail even if user/org is deleted (compliance)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action details
    action = Column(String(50), nullable=False)  # create, update, delete, login, export, execute
    resource_type = Column(String(50), nullable=False)  # pipeline, source, destination, user, billing
    resource_id = Column(String(255), nullable=True)  # ID of the affected resource

    # Change tracking (also accessible as 'details' for backward compatibility)
    details = Column("changes", JSON, nullable=True)  # {field: {old: ..., new: ...}}

    # Request metadata
    ip_address = Column(String(45), nullable=True)  # Supports IPv6
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_org_created", "organization_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', resource_type='{self.resource_type}')>"


class SuperAdminAccessLog(Base):
    """
    Super Admin Access Log model.

    Tracks when super admins access another organization's data.
    This is critical for security auditing and compliance.
    """
    __tablename__ = "super_admin_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)

    # Who accessed (SET NULL to preserve audit trail)
    super_admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # What was accessed (SET NULL to preserve audit trail)
    target_org_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(50), nullable=False)  # view_pipelines, view_runs, view_sources, impersonate, etc.
    resource_type = Column(String(50), nullable=False)  # pipeline, run, source, destination, user
    resource_id = Column(String(255), nullable=True)  # Optional specific resource ID

    # Details and context
    details = Column(JSON, nullable=True)  # Additional context about the access

    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    super_admin = relationship("User", foreign_keys=[super_admin_id])
    target_organization = relationship("Organization", foreign_keys=[target_org_id])

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_super_admin_access_admin_created", "super_admin_id", "created_at"),
        Index("ix_super_admin_access_target_created", "target_org_id", "created_at"),
    )

    def __repr__(self):
        return f"<SuperAdminAccessLog(id={self.id}, admin={self.super_admin_id}, target_org={self.target_org_id}, action='{self.action}')>"


class ImpersonationSession(Base):
    """
    Impersonation Session model.

    Tracks active impersonation sessions for super admins.
    """
    __tablename__ = "impersonation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)

    # Session details (CASCADE: delete sessions when user/org is deleted)
    super_admin_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)  # Hashed impersonation token

    # Session timing
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=False)  # Short expiry (15 mins)
    ended_at = Column(DateTime, nullable=True)  # When session was explicitly ended

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Request metadata
    ip_address = Column(String(45), nullable=True)

    # Relationships
    super_admin = relationship("User", foreign_keys=[super_admin_id])
    target_organization = relationship("Organization", foreign_keys=[target_org_id])

    __table_args__ = (
        Index("ix_impersonation_session_admin", "super_admin_id", "is_active"),
    )

    def __repr__(self):
        return f"<ImpersonationSession(id={self.id}, admin={self.super_admin_id}, target_org={self.target_org_id})>"

    @property
    def is_expired(self):
        """Check if session has expired"""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self):
        """Check if session is still valid"""
        return self.is_active and not self.is_expired and self.ended_at is None
