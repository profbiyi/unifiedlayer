"""Async tests for the notifications router — the first router migrated to the
async request path (asyncpg + AsyncSession).

Harness notes (reusable template for subsequent async routers):
- Data is created via a *committed* sync session (SessionLocal) with uuid-unique
  keys, so the separate async connection sees it, then deleted in teardown.
- `get_current_user` and `get_async_db` are overridden on the app for the test.
- Requests go through httpx.AsyncClient + ASGITransport so the endpoint and the
  AsyncSession share one event loop (asyncpg connections are loop-bound).
"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.api.main import app
from backend.auth import get_current_user
from backend.async_database import get_async_db, ASYNC_DATABASE_URL
from backend.database import SessionLocal
from backend.models.notification import Notification
from backend.models.pipeline import User, Organization

# Async tests must NOT reuse pooled connections: pytest-asyncio runs each test on
# its own event loop, and an asyncpg connection is bound to the loop it was opened
# on — a pooled connection reused on another test's loop raises a greenlet/loop
# error. NullPool opens a fresh connection per session (on the current loop) and
# closes it on exit, so every test is loop-clean.
_test_async_engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
_TestAsyncSessionLocal = async_sessionmaker(
    _test_async_engine, class_=AsyncSession, expire_on_commit=False
)


class _AuthUser:
    def __init__(self, user_id, org_id):
        self.id = user_id
        self.organization_id = org_id


@pytest_asyncio.fixture
async def seeded():
    """Committed throwaway org+user with 2 unread + 1 read notification; overrides
    auth + async-db to it; cleans up afterwards."""
    uid = uuid.uuid4().hex[:8]
    sync = SessionLocal()
    try:
        org = Organization(name=f"n-{uid}", slug=f"n-{uid}", is_active=True, can_sync_data=True)
        sync.add(org)
        sync.flush()
        user = User(
            username=f"nu-{uid}",
            email=f"nu-{uid}@example.com",
            hashed_password="x",
            organization_id=org.id,
            is_active=True,
            email_verified=True,
        )
        sync.add(user)
        sync.flush()
        for i in range(2):
            sync.add(Notification(
                user_id=user.id, organization_id=org.id,
                type="pipeline_success", title=f"Unread {i}", message="m", is_read=False,
            ))
        sync.add(Notification(
            user_id=user.id, organization_id=org.id,
            type="pipeline_success", title="Read", message="m", is_read=True,
        ))
        sync.commit()
        user_id, org_id = user.id, org.id
    finally:
        sync.close()

    async def _override_async_db():
        async with _TestAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_current_user] = lambda: _AuthUser(user_id, org_id)
    app.dependency_overrides[get_async_db] = _override_async_db
    try:
        yield _AuthUser(user_id, org_id)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_async_db, None)
        cleanup = SessionLocal()
        try:
            cleanup.query(Notification).filter(Notification.user_id == user_id).delete()
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.query(Organization).filter(Organization.id == org_id).delete()
            cleanup.commit()
        finally:
            cleanup.close()


# Full paths (incl. the /api/v1 router prefix) against a bare host base_url, so
# there is no base_url-join ambiguity.
BASE = "/api/v1/notifications"


@pytest_asyncio.fixture
async def aclient():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_unread_count(seeded, aclient):
    resp = await aclient.get(f"{BASE}/count")
    assert resp.status_code == 200
    assert resp.json()["unread"] == 2


@pytest.mark.asyncio
async def test_unread_only_list(seeded, aclient):
    resp = await aclient.get(f"{BASE}?unread_only=true")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_list_all(seeded, aclient):
    resp = await aclient.get(BASE)
    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    assert len(resp.json()["items"]) == 3


@pytest.mark.asyncio
async def test_mark_all_read(seeded, aclient):
    resp = await aclient.post(f"{BASE}/mark-all-read")
    assert resp.status_code == 200
    assert resp.json()["marked"] == 2
    after = await aclient.get(f"{BASE}/count")
    assert after.json()["unread"] == 0


@pytest.mark.asyncio
async def test_requires_auth_when_not_overridden(aclient):
    # no `seeded` → no auth override → the endpoint's auth dependency rejects
    resp = await aclient.get(f"{BASE}/count")
    assert resp.status_code in (401, 403)
