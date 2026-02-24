"""
Billing ORM Models.

Defines database models for subscriptions, usage tracking, and payment history.
"""
from datetime import datetime, timezone
import uuid
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    BigInteger,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class SubscriptionPlan(str, enum.Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"


class PaymentProvider(str, enum.Enum):
    STRIPE = "stripe"
    PAYSTACK = "paystack"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


# Plan limits configuration
PLAN_LIMITS = {
    SubscriptionPlan.STARTER: {
        "max_connectors": 3,
        "max_rows_per_month": 10_000,
        "max_pipelines": 3,
        "max_users": 1,
        "quality_checks": False,
        "lineage": False,
        "analytics": False,
        "price_gbp": 0,
        "price_id_stripe": None,  # Free tier
    },
    SubscriptionPlan.PROFESSIONAL: {
        "max_connectors": -1,  # Unlimited
        "max_rows_per_month": 500_000,
        "max_pipelines": -1,
        "max_users": 5,
        "quality_checks": True,
        "lineage": True,
        "analytics": True,
        "price_gbp": 35,
        "price_id_stripe": None,  # Set via env var
    },
    SubscriptionPlan.ENTERPRISE: {
        "max_connectors": -1,
        "max_rows_per_month": -1,  # Unlimited
        "max_pipelines": -1,
        "max_users": -1,
        "quality_checks": True,
        "lineage": True,
        "analytics": True,
        "price_gbp": None,  # Custom pricing
        "price_id_stripe": None,
    },
}


class Subscription(Base):
    """Tracks an organization's subscription and links to payment provider."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    plan = Column(SQLEnum(SubscriptionPlan), nullable=False, default=SubscriptionPlan.STARTER)
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    payment_provider = Column(SQLEnum(PaymentProvider), nullable=True)

    # Stripe fields
    stripe_customer_id = Column(String(255), nullable=True, unique=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True, index=True)
    stripe_price_id = Column(String(255), nullable=True)

    # Paystack fields
    paystack_customer_code = Column(String(255), nullable=True, unique=True)
    paystack_subscription_code = Column(String(255), nullable=True, unique=True)

    # Billing details
    currency = Column(String(3), nullable=False, default="GBP")
    billing_email = Column(String(255), nullable=True)

    # Period
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", backref="subscription", uselist=False)
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")


class Invoice(Base):
    """Payment history / invoices."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Provider reference
    stripe_invoice_id = Column(String(255), nullable=True, unique=True)
    paystack_reference = Column(String(255), nullable=True, unique=True)

    status = Column(SQLEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    currency = Column(String(3), nullable=False, default="GBP")
    amount_due = Column(Integer, nullable=False, default=0)  # In smallest currency unit (pence/kobo)
    amount_paid = Column(Integer, nullable=False, default=0)
    amount_remaining = Column(Integer, nullable=False, default=0)

    # Period this invoice covers
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

    # Payment details
    paid_at = Column(DateTime, nullable=True)
    hosted_invoice_url = Column(Text, nullable=True)
    invoice_pdf_url = Column(Text, nullable=True)

    # Line items as JSON
    line_items = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")


class UsageRecord(Base):
    """Monthly usage tracking per organization for metered billing."""
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Period (year-month)
    period_year = Column(Integer, nullable=False)
    period_month = Column(Integer, nullable=False)

    # Usage counters
    rows_synced = Column(BigInteger, nullable=False, default=0)
    api_calls = Column(Integer, nullable=False, default=0)
    pipeline_runs = Column(Integer, nullable=False, default=0)
    storage_bytes = Column(BigInteger, nullable=False, default=0)
    active_connectors = Column(Integer, nullable=False, default=0)

    # Limits for this period (snapshot from plan at start of period)
    rows_limit = Column(BigInteger, nullable=False, default=10_000)
    api_calls_limit = Column(Integer, nullable=False, default=1_000)

    # Overage tracking
    rows_overage = Column(BigInteger, nullable=False, default=0)
    overage_charged = Column(Boolean, default=False, nullable=False)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint('organization_id', 'period_year', 'period_month',
                         name='uq_usage_org_period'),
        Index('ix_usage_period', 'period_year', 'period_month'),
    )
