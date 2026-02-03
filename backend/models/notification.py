"""
Notification ORM Model.

Defines the database model for in-app notifications.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class Notification(Base):
    """
    Notification model.

    Represents an in-app notification sent to a user.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    type = Column(String(50), nullable=False)  # pipeline_success, pipeline_failure, usage_warning, stale_data, billing_alert, team_invite
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(500), nullable=True)  # e.g. "/pipelines/uuid"

    is_read = Column(Boolean, default=False, nullable=False, server_default="false")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
    )

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.type}', user_id={self.user_id})>"
