"""
Pipeline ORM Models.

Defines database models for organizations, users, data sources,
destinations, pipelines, and pipeline runs.
"""
from datetime import datetime, timezone
from typing import Optional, Dict
import uuid
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
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from backend.database import Base
from backend.utils.encrypted_type import EncryptedJSON


class PipelineStatus(str, enum.Enum):
    """Pipeline run status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SourceType(str, enum.Enum):
    """Data source type enumeration."""
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    MPESA = "mpesa"
    WHATSAPP = "whatsapp"
    REST_API = "rest_api"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"
    SALESFORCE = "salesforce"
    SHOPIFY = "shopify"
    STRIPE = "stripe"
    PAYSTACK = "paystack"
    GOOGLE_SHEETS = "google_sheets"
    GOCARDLESS = "gocardless"
    XERO = "xero"
    OPEN_BANKING = "open_banking"
    HMRC_MTD = "hmrc_mtd"
    FLUTTERWAVE = "flutterwave"
    MTN_MOMO = "mtn_momo"


class DestinationType(str, enum.Enum):
    """Destination type enumeration."""
    POSTGRES = "postgres"
    DUCKDB = "duckdb"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    REDSHIFT = "redshift"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"
    GOOGLE_SHEETS = "google_sheets"


class Organization(Base):
    """
    Organization model.

    Represents a tenant/organization in a multi-tenant setup.
    """
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Organization control flags (Super Admin only)
    is_active = Column(Boolean, default=True, nullable=False)  # Hard shutdown: no login, no access
    can_sync_data = Column(Boolean, default=True, nullable=False)  # Soft warning: can login but no pipeline runs

    # Subscription and billing fields
    subscription_plan = Column(String(20), nullable=False, default='starter', server_default='starter')  # starter, professional, enterprise
    max_users = Column(Integer, nullable=False, default=3, server_default='3')  # User limit based on plan
    subscription_status = Column(String(20), nullable=False, default='active', server_default='active')  # active, trial, suspended, cancelled
    trial_ends_at = Column(DateTime, nullable=True)  # Trial expiration date
    billing_email = Column(String(255), nullable=True)  # Billing contact email

    # Onboarding tracking
    admin_onboarded = Column(Boolean, default=False, nullable=False, server_default='false')  # Has admin logged in?
    admin_onboarded_at = Column(DateTime, nullable=True)  # When admin first logged in

    # Branding
    logo_url = Column(String(500), nullable=True)  # Organization logo URL
    brand_primary_color = Column(String(7), nullable=True)  # Hex color code (e.g., #3B82F6)
    brand_secondary_color = Column(String(7), nullable=True)  # Hex color code

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    data_sources = relationship("DataSource", back_populates="organization", cascade="all, delete-orphan")
    destinations = relationship("Destination", back_populates="organization", cascade="all, delete-orphan")
    pipelines = relationship("Pipeline", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan", foreign_keys="[APIKey.organization_id]")

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"

    @property
    def current_user_count(self):
        """Get current number of active users"""
        return len([u for u in self.users if u.is_active])

    @property
    def can_add_users(self):
        """Check if organization can add more users"""
        return self.current_user_count < self.max_users


class User(Base):
    """
    User model.

    Represents users who can authenticate and manage pipelines.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)

    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)  # Kept for backward compatibility during migration

    # Invitation fields
    email_verified = Column(Boolean, default=False, nullable=False, server_default='false')
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    invitation_token = Column(String(255), nullable=True, unique=True)  # Unique token for invitation
    invitation_status = Column(String(20), nullable=True)  # pending, accepted, cancelled, expired
    invitation_accepted_at = Column(DateTime, nullable=True)
    invitation_expires_at = Column(DateTime, nullable=True)  # Invitation expiration (48 hours)

    # Email verification
    email_verification_token = Column(String(255), nullable=True, unique=True)

    # Two-Factor Authentication
    totp_secret = Column(String(255), nullable=True)
    two_factor_enabled = Column(Boolean, default=False, nullable=False, server_default='false')

    # Password reset fields
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)

    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    user_roles = relationship("UserRole", back_populates="user", foreign_keys="[UserRole.user_id]", cascade="all, delete-orphan")
    invited_by = relationship("User", remote_side=[id], foreign_keys=[invited_by_id])
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan", foreign_keys="[APIKey.user_id]")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

    @property
    def roles(self):
        """Get all roles assigned to this user"""
        return [ur.role for ur in self.user_roles]

    @property
    def role_names(self):
        """Get role names as a list"""
        return [role.name for role in self.roles]

    def has_role(self, role_name: str, organization_id: Optional[int] = None) -> bool:
        """Check if user has a specific role"""
        for ur in self.user_roles:
            if ur.role.slug == role_name:
                if organization_id is None or ur.organization_id == organization_id:
                    return True
        return False

    def is_super_admin(self) -> bool:
        """Check if user is a super admin"""
        return self.has_role('super_admin')

    def is_org_admin(self, organization_id: Optional[int] = None) -> bool:
        """Check if user is an organization admin"""
        org_id = organization_id or self.organization_id
        return self.has_role('org_admin', org_id)

    def is_org_user(self, organization_id: Optional[int] = None) -> bool:
        """Check if user is an organization user"""
        org_id = organization_id or self.organization_id
        return self.has_role('org_user', org_id)


class DataSource(Base):
    """
    Data Source model.

    Represents a source of data (database, API, etc.).
    """
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(SQLEnum(SourceType), nullable=False)

    # Encrypted JSON field for connection configuration (credentials at rest)
    config = Column(EncryptedJSON, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="data_sources")
    pipelines = relationship("Pipeline", back_populates="source", foreign_keys="Pipeline.source_id")

    def __repr__(self):
        return f"<DataSource(id={self.id}, name='{self.name}', type='{self.source_type}')>"


class Destination(Base):
    """
    Destination model.

    Represents a destination for data (warehouse, database, storage).
    """
    __tablename__ = "destinations"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    destination_type = Column(SQLEnum(DestinationType), nullable=False)

    # Encrypted JSON field for connection configuration (credentials at rest)
    config = Column(EncryptedJSON, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="destinations")
    pipelines = relationship("Pipeline", back_populates="destination", foreign_keys="Pipeline.destination_id")

    def __repr__(self):
        return f"<Destination(id={self.id}, name='{self.name}', type='{self.destination_type}')>"


class Pipeline(Base):
    """
    Pipeline model.

    Represents a data pipeline from source to destination.
    """
    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    destination_id = Column(Integer, ForeignKey("destinations.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Schedule in cron format (e.g., "0 0 * * *" for daily at midnight)
    schedule = Column(String(100), nullable=True)
    schedule_enabled = Column(Boolean, default=False, nullable=False, server_default='false')
    schedule_timezone = Column(String(50), nullable=True, default='UTC')  # e.g., 'America/New_York', 'UTC'
    last_scheduled_run = Column(DateTime, nullable=True)  # When was the last scheduled run triggered
    next_scheduled_run = Column(DateTime, nullable=True)  # When is the next scheduled run

    # Retry configuration
    max_retries = Column(Integer, nullable=False, default=0, server_default='0')  # Number of retry attempts (0 = no retries)
    retry_delay_seconds = Column(Integer, nullable=False, default=60, server_default='60')  # Delay between retries in seconds
    exponential_backoff_enabled = Column(Boolean, default=False, nullable=False, server_default='false')  # Use exponential backoff for retries

    # JSON field for pipeline configuration (transformations, mappings, etc.)
    config = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="pipelines")
    source = relationship("DataSource", back_populates="pipelines", foreign_keys=[source_id])
    destination = relationship("Destination", back_populates="pipelines", foreign_keys=[destination_id])
    runs = relationship("PipelineRun", back_populates="pipeline", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Pipeline(id={self.id}, name='{self.name}')>"


class PipelineRun(Base):
    """
    Pipeline Run model.

    Represents a single execution of a pipeline.
    """
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id"), nullable=False)

    status = Column(SQLEnum(PipelineStatus), default=PipelineStatus.PENDING, nullable=False, index=True)

    # Retry tracking
    retry_count = Column(Integer, nullable=False, default=0, server_default='0')  # Current retry attempt number (0 = first run)
    is_retry = Column(Boolean, default=False, nullable=False, server_default='false')  # Whether this run is a retry
    original_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)  # ID of the original failed run

    # Execution metadata
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Metrics
    rows_read = Column(Integer, nullable=True)
    rows_written = Column(Integer, nullable=True)
    bytes_read = Column(Integer, nullable=True)
    bytes_written = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Error information
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Additional metadata in JSON format
    run_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    pipeline = relationship("Pipeline", back_populates="runs")
    original_run = relationship("PipelineRun", remote_side=[id], foreign_keys=[original_run_id])

    def __repr__(self):
        return f"<PipelineRun(id={self.id}, pipeline_id={self.pipeline_id}, status='{self.status}')>"

    @property
    def duration(self) -> Optional[float]:
        """Calculate duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
