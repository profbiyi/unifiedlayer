"""Async tests for the users router (exercises eager-loaded roles serialization)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.api.main import app
from backend.auth import get_current_user
from backend.async_database import get_async_db
from backend.tests.async_helpers import AuthUser, override_async_db, seeded_org_user

BASE = "/api/v1/users"


@pytest_asyncio.fixture
async def aclient():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


@pytest_asyncio.fixture
async def as_user():
    with seeded_org_user() as (user_id, org_id):
        au = AuthUser(user_id, org_id)
        app.dependency_overrides[get_current_user] = lambda: au
        app.dependency_overrides[get_async_db] = override_async_db
        try:
            yield au
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_async_db, None)


@pytest.mark.asyncio
async def test_list_users(as_user, aclient):
    resp = await aclient.get(BASE)
    assert resp.status_code == 200
    users = resp.json()
    assert any(u["id"] == as_user.id for u in users)
    # roles serialization (eager-loaded) resolves to an empty list, no lazy-load crash
    assert all(isinstance(u["roles"], list) for u in users)


@pytest.mark.asyncio
async def test_get_own_user(as_user, aclient):
    resp = await aclient.get(f"{BASE}/{as_user.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == as_user.id
    assert body["roles"] == []


@pytest.mark.asyncio
async def test_get_missing_user_404(as_user, aclient):
    resp = await aclient.get(f"{BASE}/999999")
    assert resp.status_code == 404
