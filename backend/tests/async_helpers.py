"""Shared helpers for testing async routers.

Reused by every async-router test so the NullPool engine, app overrides, and
committed-seed/cleanup pattern live in one place.

Why NullPool: pytest-asyncio runs each test on its own event loop, and an asyncpg
connection is bound to the loop it was opened on; a pooled connection reused on a
different test's loop raises a greenlet/loop error. NullPool opens a fresh
connection per session (on the current loop) and closes it on exit.
"""
import uuid
from contextlib import contextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.async_database import ASYNC_DATABASE_URL
from backend.database import SessionLocal
from backend.models.pipeline import User, Organization

test_async_engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
TestAsyncSessionLocal = async_sessionmaker(
    test_async_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_async_db():
    """FastAPI dependency override yielding a NullPool-backed AsyncSession."""
    async with TestAsyncSessionLocal() as session:
        yield session


class AuthUser:
    """Minimal stand-in for the authenticated user (overrides get_current_user)."""
    def __init__(self, user_id, org_id, is_superuser=False):
        self.id = user_id
        self.organization_id = org_id
        self.is_superuser = is_superuser


@contextmanager
def seeded_org_user():
    """Create a committed throwaway org + user (so the async connection sees them);
    yield (user_id, org_id); delete them afterwards."""
    uid = uuid.uuid4().hex[:8]
    sync = SessionLocal()
    try:
        org = Organization(name=f"t-{uid}", slug=f"t-{uid}", is_active=True, can_sync_data=True)
        sync.add(org)
        sync.flush()
        user = User(
            username=f"tu-{uid}",
            email=f"tu-{uid}@example.com",
            hashed_password="x",
            organization_id=org.id,
            is_active=True,
            email_verified=True,
        )
        sync.add(user)
        sync.flush()
        sync.commit()
        user_id, org_id = user.id, org.id
    finally:
        sync.close()
    try:
        yield user_id, org_id
    finally:
        cleanup = SessionLocal()
        try:
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.query(Organization).filter(Organization.id == org_id).delete()
            cleanup.commit()
        finally:
            cleanup.close()
