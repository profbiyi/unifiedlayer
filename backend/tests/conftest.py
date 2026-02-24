"""
Pytest configuration and fixtures.

Provides comprehensive fixtures for testing the UnifiedLayer platform.
"""
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.api.main import app
from backend.database import Base, get_db
from backend.config import settings
from backend.models.rbac import Role, Permission, RolePermission, UserRole
from backend.models.pipeline import (
    Organization, User, Pipeline, DataSource, Destination,
    PipelineRun, PipelineStatus, SourceType, DestinationType
)
from backend.models.billing import (
    Subscription, Invoice, UsageRecord, SubscriptionPlan,
    SubscriptionStatus, PaymentProvider, InvoiceStatus
)
from backend.models.notification import Notification
from backend.models.api_key import APIKey
from backend.auth import get_password_hash, create_access_token


# Test database - use PostgreSQL to match production (supports UUID, etc.)
def get_test_database_url():
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    if settings.DATABASE_URL:
        # Replace only the last path segment (database name)
        base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
        return f"{base_url}/dataplatform_test"
    return "postgresql://dataplatform:dataplatform_pass@postgres:5432/dataplatform_test"


TEST_DATABASE_URL = get_test_database_url()
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Database Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once at session start, drop at end."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Create a fresh database session for each test with transaction rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# ---------------------------------------------------------------------------
# RBAC Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_rbac(db: Session) -> Dict[str, Any]:
    """Set up RBAC roles and permissions for testing."""
    # Create SUPER_ADMIN role
    super_admin_role = Role(
        name="SUPER_ADMIN",
        slug="super_admin",
        description="Super Administrator",
        scope="global"
    )
    db.add(super_admin_role)

    # Create ORG_ADMIN role
    org_admin_role = Role(
        name="ORG_ADMIN",
        slug="org_admin",
        description="Organization Admin",
        scope="organization"
    )
    db.add(org_admin_role)

    # Create ORG_USER role
    org_user_role = Role(
        name="ORG_USER",
        slug="org_user",
        description="Organization User",
        scope="organization"
    )
    db.add(org_user_role)
    db.flush()

    # Define permissions
    permission_defs = [
        ("pipeline", "read"), ("pipeline", "create"), ("pipeline", "update"),
        ("pipeline", "delete"), ("pipeline", "execute"),
        ("source", "read"), ("source", "create"), ("source", "update"), ("source", "delete"),
        ("destination", "read"), ("destination", "create"), ("destination", "update"), ("destination", "delete"),
        ("user", "read"), ("user", "create"), ("user", "update"), ("user", "delete"),
        ("organization", "read"), ("organization", "update"),
        ("billing", "read"), ("billing", "manage"),
        ("admin", "access"),
    ]

    permissions = []
    for resource, action in permission_defs:
        perm = Permission(resource=resource, action=action)
        db.add(perm)
        permissions.append(perm)
    db.flush()

    # Assign all permissions to super admin
    for perm in permissions:
        db.add(RolePermission(role_id=super_admin_role.id, permission_id=perm.id))

    # Assign org-level permissions to org admin
    org_admin_perms = [p for p in permissions if p.resource != "admin"]
    for perm in org_admin_perms:
        db.add(RolePermission(role_id=org_admin_role.id, permission_id=perm.id))

    # Assign basic permissions to org user
    org_user_perm_defs = [
        ("pipeline", "read"), ("pipeline", "create"), ("pipeline", "update"),
        ("pipeline", "delete"), ("pipeline", "execute"),
        ("source", "read"), ("source", "create"), ("source", "update"), ("source", "delete"),
        ("destination", "read"), ("destination", "create"), ("destination", "update"), ("destination", "delete"),
        ("user", "read"),
    ]
    for perm in permissions:
        if (perm.resource, perm.action) in org_user_perm_defs:
            db.add(RolePermission(role_id=org_user_role.id, permission_id=perm.id))
    db.flush()

    return {
        "super_admin_role": super_admin_role,
        "org_admin_role": org_admin_role,
        "org_user_role": org_user_role,
        "permissions": permissions,
    }


# ---------------------------------------------------------------------------
# Organization Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_org(db: Session) -> Organization:
    """Create a test organization."""
    org = Organization(
        name="Test Organization",
        slug="test-org",
        description="A test organization",
        subscription_plan="professional",
        max_users=10,
        is_active=True,
        can_sync_data=True,
    )
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


@pytest.fixture
def second_org(db: Session) -> Organization:
    """Create a second test organization for multi-tenancy tests."""
    org = Organization(
        name="Second Organization",
        slug="second-org",
        description="Another test organization",
        subscription_plan="starter",
        max_users=5,
        is_active=True,
    )
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


@pytest.fixture
def inactive_org(db: Session) -> Organization:
    """Create an inactive organization."""
    org = Organization(
        name="Inactive Organization",
        slug="inactive-org",
        is_active=False,
        can_sync_data=False,
    )
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


# ---------------------------------------------------------------------------
# User Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_user(db: Session, test_org: Organization, setup_rbac: Dict) -> User:
    """Create a test user with ORG_USER role."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        organization_id=test_org.id,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    # Assign ORG_USER role
    user_role = UserRole(
        user_id=user.id,
        role_id=setup_rbac["org_user_role"].id,
        organization_id=test_org.id,
    )
    db.add(user_role)
    db.flush()

    return user


@pytest.fixture
def admin_user(db: Session, test_org: Organization, setup_rbac: Dict) -> User:
    """Create an organization admin user."""
    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        organization_id=test_org.id,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    # Assign ORG_ADMIN role
    user_role = UserRole(
        user_id=user.id,
        role_id=setup_rbac["org_admin_role"].id,
        organization_id=test_org.id,
    )
    db.add(user_role)
    db.flush()

    return user


@pytest.fixture
def super_admin_user(db: Session, test_org: Organization, setup_rbac: Dict) -> User:
    """Create a super admin user."""
    user = User(
        username="superadmin",
        email="superadmin@platform.com",
        hashed_password=get_password_hash("superadminpass"),
        organization_id=test_org.id,
        is_active=True,
        is_superuser=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    # Assign SUPER_ADMIN role
    user_role = UserRole(
        user_id=user.id,
        role_id=setup_rbac["super_admin_role"].id,
        organization_id=test_org.id,
    )
    db.add(user_role)
    db.flush()

    return user


@pytest.fixture
def user_with_2fa(db: Session, test_org: Organization, setup_rbac: Dict) -> User:
    """Create a user with 2FA enabled."""
    import pyotp

    user = User(
        username="user2fa",
        email="user2fa@example.com",
        hashed_password=get_password_hash("password123"),
        organization_id=test_org.id,
        is_active=True,
        email_verified=True,
        totp_secret=pyotp.random_base32(),
        two_factor_enabled=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    user_role = UserRole(
        user_id=user.id,
        role_id=setup_rbac["org_user_role"].id,
        organization_id=test_org.id,
    )
    db.add(user_role)
    db.flush()

    return user


@pytest.fixture
def inactive_user(db: Session, test_org: Organization, setup_rbac: Dict) -> User:
    """Create an inactive user."""
    user = User(
        username="inactiveuser",
        email="inactive@example.com",
        hashed_password=get_password_hash("password123"),
        organization_id=test_org.id,
        is_active=False,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Data Source Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_source(db: Session, test_org: Organization) -> DataSource:
    """Create a test data source."""
    source = DataSource(
        name="Test PostgreSQL Source",
        source_type=SourceType.POSTGRES,
        organization_id=test_org.id,
        config={"host": "localhost", "port": 5432, "database": "test"},
        is_active=True,
    )
    db.add(source)
    db.flush()
    db.refresh(source)
    return source


@pytest.fixture
def mpesa_source(db: Session, test_org: Organization) -> DataSource:
    """Create an M-Pesa data source."""
    source = DataSource(
        name="M-Pesa Source",
        source_type=SourceType.MPESA,
        organization_id=test_org.id,
        config={"api_key": "test_key", "environment": "sandbox"},
        is_active=True,
    )
    db.add(source)
    db.flush()
    db.refresh(source)
    return source


@pytest.fixture
def rest_api_source(db: Session, test_org: Organization) -> DataSource:
    """Create a REST API data source."""
    source = DataSource(
        name="REST API Source",
        source_type=SourceType.REST_API,
        organization_id=test_org.id,
        config={"base_url": "https://api.example.com", "auth_type": "bearer"},
        is_active=True,
    )
    db.add(source)
    db.flush()
    db.refresh(source)
    return source


# ---------------------------------------------------------------------------
# Destination Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_destination(db: Session, test_org: Organization) -> Destination:
    """Create a test destination."""
    dest = Destination(
        name="Test S3 Destination",
        destination_type=DestinationType.S3,
        organization_id=test_org.id,
        config={"bucket_url": "s3://test-bucket", "file_format": "parquet"},
        is_active=True,
    )
    db.add(dest)
    db.flush()
    db.refresh(dest)
    return dest


@pytest.fixture
def postgres_destination(db: Session, test_org: Organization) -> Destination:
    """Create a PostgreSQL destination."""
    dest = Destination(
        name="PostgreSQL Destination",
        destination_type=DestinationType.POSTGRES,
        organization_id=test_org.id,
        config={"host": "localhost", "port": 5432, "database": "warehouse"},
        is_active=True,
    )
    db.add(dest)
    db.flush()
    db.refresh(dest)
    return dest


# ---------------------------------------------------------------------------
# Pipeline Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_pipeline(
    db: Session,
    test_org: Organization,
    test_source: DataSource,
    test_destination: Destination,
) -> Pipeline:
    """Create a test pipeline."""
    pipeline = Pipeline(
        name="Test Pipeline",
        description="A test pipeline",
        organization_id=test_org.id,
        source_id=test_source.id,
        destination_id=test_destination.id,
        is_active=True,
        schedule="0 * * * *",
        schedule_enabled=False,
    )
    db.add(pipeline)
    db.flush()
    db.refresh(pipeline)
    return pipeline


@pytest.fixture
def scheduled_pipeline(
    db: Session,
    test_org: Organization,
    test_source: DataSource,
    test_destination: Destination,
) -> Pipeline:
    """Create a pipeline with scheduling enabled."""
    pipeline = Pipeline(
        name="Scheduled Pipeline",
        organization_id=test_org.id,
        source_id=test_source.id,
        destination_id=test_destination.id,
        is_active=True,
        schedule="0 0 * * *",
        schedule_enabled=True,
        schedule_timezone="UTC",
    )
    db.add(pipeline)
    db.flush()
    db.refresh(pipeline)
    return pipeline


@pytest.fixture
def pipeline_with_retries(
    db: Session,
    test_org: Organization,
    test_source: DataSource,
    test_destination: Destination,
) -> Pipeline:
    """Create a pipeline with retry configuration."""
    pipeline = Pipeline(
        name="Retry Pipeline",
        organization_id=test_org.id,
        source_id=test_source.id,
        destination_id=test_destination.id,
        is_active=True,
        max_retries=3,
        retry_delay_seconds=60,
        exponential_backoff_enabled=True,
    )
    db.add(pipeline)
    db.flush()
    db.refresh(pipeline)
    return pipeline


@pytest.fixture
def inactive_pipeline(
    db: Session,
    test_org: Organization,
    test_source: DataSource,
    test_destination: Destination,
) -> Pipeline:
    """Create an inactive pipeline."""
    pipeline = Pipeline(
        name="Inactive Pipeline",
        organization_id=test_org.id,
        source_id=test_source.id,
        destination_id=test_destination.id,
        is_active=False,
    )
    db.add(pipeline)
    db.flush()
    db.refresh(pipeline)
    return pipeline


# ---------------------------------------------------------------------------
# Pipeline Run Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def completed_run(db: Session, test_pipeline: Pipeline) -> PipelineRun:
    """Create a completed pipeline run."""
    run = PipelineRun(
        pipeline_id=test_pipeline.id,
        status=PipelineStatus.COMPLETED,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        completed_at=datetime.now(timezone.utc),
        rows_read=1000,
        rows_written=1000,
        duration_seconds=300,
    )
    db.add(run)
    db.flush()
    db.refresh(run)
    return run


@pytest.fixture
def failed_run(db: Session, test_pipeline: Pipeline) -> PipelineRun:
    """Create a failed pipeline run."""
    run = PipelineRun(
        pipeline_id=test_pipeline.id,
        status=PipelineStatus.FAILED,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        completed_at=datetime.now(timezone.utc),
        error_message="Connection timeout",
        error_traceback="Traceback: ...",
    )
    db.add(run)
    db.flush()
    db.refresh(run)
    return run


@pytest.fixture
def running_run(db: Session, test_pipeline: Pipeline) -> PipelineRun:
    """Create a running pipeline run."""
    run = PipelineRun(
        pipeline_id=test_pipeline.id,
        status=PipelineStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    db.refresh(run)
    return run


# ---------------------------------------------------------------------------
# Billing Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_subscription(db: Session, test_org: Organization) -> Subscription:
    """Create a test subscription."""
    sub = Subscription(
        organization_id=test_org.id,
        plan=SubscriptionPlan.PROFESSIONAL,
        status=SubscriptionStatus.ACTIVE,
        payment_provider=PaymentProvider.STRIPE,
        currency="GBP",
        billing_email="billing@example.com",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)
    db.flush()
    db.refresh(sub)
    return sub


@pytest.fixture
def trial_subscription(db: Session, second_org: Organization) -> Subscription:
    """Create a trial subscription."""
    sub = Subscription(
        organization_id=second_org.id,
        plan=SubscriptionPlan.PROFESSIONAL,
        status=SubscriptionStatus.TRIALING,
        currency="GBP",
        trial_end=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db.add(sub)
    db.flush()
    db.refresh(sub)
    return sub


@pytest.fixture
def usage_record(db: Session, test_org: Organization) -> UsageRecord:
    """Create a usage record for the current month."""
    now = datetime.now(timezone.utc)
    record = UsageRecord(
        organization_id=test_org.id,
        period_year=now.year,
        period_month=now.month,
        rows_synced=5000,
        pipeline_runs=50,
        api_calls=100,
        rows_limit=500000,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    return record


@pytest.fixture
def paid_invoice(db: Session, test_subscription: Subscription, test_org: Organization) -> Invoice:
    """Create a paid invoice."""
    invoice = Invoice(
        subscription_id=test_subscription.id,
        organization_id=test_org.id,
        status=InvoiceStatus.PAID,
        currency="GBP",
        amount_due=3500,  # 35.00 GBP in pence
        amount_paid=3500,
        amount_remaining=0,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(invoice)
    db.flush()
    db.refresh(invoice)
    return invoice


# ---------------------------------------------------------------------------
# Notification Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_notification(db: Session, test_user: User, test_org: Organization) -> Notification:
    """Create a test notification."""
    notif = Notification(
        user_id=test_user.id,
        organization_id=test_org.id,
        type="pipeline_success",
        title="Pipeline completed",
        message="Your pipeline has completed successfully.",
        link="/pipelines/123",
        is_read=False,
    )
    db.add(notif)
    db.flush()
    db.refresh(notif)
    return notif


@pytest.fixture
def read_notification(db: Session, test_user: User, test_org: Organization) -> Notification:
    """Create a read notification."""
    notif = Notification(
        user_id=test_user.id,
        organization_id=test_org.id,
        type="billing_alert",
        title="Payment received",
        message="Your payment has been processed.",
        is_read=True,
    )
    db.add(notif)
    db.flush()
    db.refresh(notif)
    return notif


# ---------------------------------------------------------------------------
# API Key Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_api_key(db: Session, test_user: User, test_org: Organization) -> tuple:
    """Create a test API key. Returns (plain_key, APIKey model)."""
    import hashlib

    plain_key = "dp_live_" + secrets.token_hex(16)
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()

    api_key = APIKey(
        user_id=test_user.id,
        organization_id=test_org.id,
        name="Test API Key",
        key_prefix=plain_key[:12],
        key_hash=key_hash,
        is_active=True,
    )
    db.add(api_key)
    db.flush()
    db.refresh(api_key)

    return plain_key, api_key


@pytest.fixture
def expired_api_key(db: Session, test_user: User, test_org: Organization) -> APIKey:
    """Create an expired API key."""
    import hashlib

    plain_key = "dp_live_" + secrets.token_hex(16)
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()

    api_key = APIKey(
        user_id=test_user.id,
        organization_id=test_org.id,
        name="Expired API Key",
        key_prefix=plain_key[:12],
        key_hash=key_hash,
        is_active=True,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(api_key)
    db.flush()
    db.refresh(api_key)

    return api_key


# ---------------------------------------------------------------------------
# Test Client Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db: Session, setup_rbac: Dict) -> Generator[TestClient, None, None]:
    """Create test client with database override."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client: TestClient, test_user: User) -> TestClient:
    """Create authenticated test client."""
    token = create_access_token(data={"sub": str(test_user.id)})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def admin_client(client: TestClient, admin_user: User) -> TestClient:
    """Create authenticated test client with admin user."""
    token = create_access_token(data={"sub": str(admin_user.id)})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def super_admin_client(client: TestClient, super_admin_user: User) -> TestClient:
    """Create authenticated test client with super admin user."""
    token = create_access_token(data={"sub": str(super_admin_user.id)})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ---------------------------------------------------------------------------
# Mock Fixtures for External Services
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_stripe():
    """Mock Stripe API calls."""
    with patch("stripe.Customer.create") as mock_customer, \
         patch("stripe.checkout.Session.create") as mock_checkout, \
         patch("stripe.billing_portal.Session.create") as mock_portal:

        mock_customer.return_value = MagicMock(id="cus_test123")
        mock_checkout.return_value = MagicMock(url="https://checkout.stripe.com/test")
        mock_portal.return_value = MagicMock(url="https://billing.stripe.com/test")

        yield {
            "customer": mock_customer,
            "checkout": mock_checkout,
            "portal": mock_portal,
        }


@pytest.fixture
def mock_paystack():
    """Mock Paystack API calls."""
    with patch("requests.post") as mock_post, \
         patch("requests.get") as mock_get:

        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "status": True,
                "data": {
                    "customer_code": "CUS_test123",
                    "authorization_url": "https://paystack.com/checkout/test",
                    "access_code": "test_access",
                    "reference": "ref_123",
                }
            }
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "status": True,
                "data": {"status": "success", "amount": 1500000}
            }
        )

        yield {"post": mock_post, "get": mock_get}


@pytest.fixture
def mock_sendgrid():
    """Mock SendGrid email sending."""
    with patch("backend.notifications.email_notifier.send_email") as mock_send:
        mock_send.return_value = True
        yield mock_send


@pytest.fixture
def mock_smtp():
    """Mock SMTP email sending."""
    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_instance = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=None)
        yield mock_instance


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_auth_headers(user: User) -> dict:
    """Get authorization headers for a user."""
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def create_temp_2fa_token(user: User) -> str:
    """Create a temporary 2FA pending token."""
    return create_access_token(
        data={"sub": str(user.id), "email": user.email, "2fa_pending": True},
        expires_delta=timedelta(minutes=5),
    )
