"""
Webhook Event ORM Models.

Defines database models for storing incoming webhook events
from payment providers (Paystack, Flutterwave, GoCardless, M-Pesa, Stripe).
"""
from datetime import datetime, timezone
import uuid
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class WebhookEventStatus(str, enum.Enum):
    """Webhook event processing status."""
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"


class WebhookEvent(Base):
    """
    Webhook Event model.

    Stores incoming webhook payloads from payment providers for
    async processing and audit trail.
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    source_type = Column(String(50), nullable=False, index=True)  # paystack, flutterwave, gocardless, mpesa, stripe
    event_type = Column(String(255), nullable=False)  # e.g. charge.success, payment.completed
    payload = Column(JSON, nullable=False)
    signature = Column(String(512), nullable=True)
    status = Column(SQLEnum(WebhookEventStatus), default=WebhookEventStatus.RECEIVED, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])

    __table_args__ = (
        Index("ix_webhook_events_org_source_created", "organization_id", "source_type", "created_at"),
    )

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, source='{self.source_type}', event='{self.event_type}', status='{self.status}')>"
