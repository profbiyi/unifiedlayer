"""
Pytest configuration and fixtures.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.main import app
from backend.database import Base, get_db
from backend.config import settings
from backend.models.rbac import Role, Permission, RolePermission, UserRole

# Test database - use PostgreSQL to match production (supports UUID, etc.)
# Replace only the database name at the end of the URL
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


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once at session start, drop at end."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
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


@pytest.fixture
def setup_rbac(db):
    """Set up RBAC roles and permissions for testing."""
    # Create ORG_USER role
    org_user_role = Role(
        name="ORG_USER",
        slug="org_user",
        description="Organization User",
        scope="organization"
    )
    db.add(org_user_role)

    # Create ORG_ADMIN role
    org_admin_role = Role(
        name="ORG_ADMIN",
        slug="org_admin",
        description="Organization Admin",
        scope="organization"
    )
    db.add(org_admin_role)
    db.flush()

    # Define permissions
    permission_defs = [
        ("pipeline", "read"), ("pipeline", "create"), ("pipeline", "update"),
        ("pipeline", "delete"), ("pipeline", "execute"),
        ("source", "read"), ("source", "create"), ("source", "update"), ("source", "delete"),
        ("destination", "read"), ("destination", "create"), ("destination", "update"), ("destination", "delete"),
        ("user", "read"),
    ]

    permissions = []
    for resource, action in permission_defs:
        perm = Permission(resource=resource, action=action)
        db.add(perm)
        permissions.append(perm)
    db.flush()

    # Assign all permissions to both roles
    for perm in permissions:
        db.add(RolePermission(role_id=org_user_role.id, permission_id=perm.id))
        db.add(RolePermission(role_id=org_admin_role.id, permission_id=perm.id))
    db.flush()

    return {"org_user_role": org_user_role, "org_admin_role": org_admin_role}


@pytest.fixture
def client(db, setup_rbac):
    """Create test client with RBAC setup."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
