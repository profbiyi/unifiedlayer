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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

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
