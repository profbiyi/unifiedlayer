"""Async smoke tests for the analytics router (empty org → zeros/empty lists)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.api.main import app
from backend.auth import get_current_user
from backend.async_database import get_async_db
from backend.tests.async_helpers import AuthUser, override_async_db, seeded_org_user

BASE = "/api/v1/analytics"


@pytest_asyncio.fixture
async def aclient():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


@pytest_asyncio.fixture
async def as_user():
    with seeded_org_user() as (user_id, org_id):
        app.dependency_overrides[get_current_user] = lambda: AuthUser(user_id, org_id)
        app.dependency_overrides[get_async_db] = override_async_db
        try:
            yield AuthUser(user_id, org_id)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_async_db, None)


@pytest.mark.asyncio
async def test_overview_empty(as_user, aclient):
    resp = await aclient.get(f"{BASE}/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pipelines"]["total"] == 0
    assert body["runs"]["total"] == 0
    assert body["runs"]["success_rate"] == 0


@pytest.mark.asyncio
async def test_runs_timeline_empty(as_user, aclient):
    resp = await aclient.get(f"{BASE}/runs/timeline?days=7")
    assert resp.status_code == 200
    assert resp.json()["timeline"] == []


@pytest.mark.asyncio
async def test_pipelines_performance_empty(as_user, aclient):
    resp = await aclient.get(f"{BASE}/pipelines/performance")
    assert resp.status_code == 200
    assert resp.json()["pipelines"] == []


@pytest.mark.asyncio
async def test_usage_history_empty(as_user, aclient):
    resp = await aclient.get(f"{BASE}/usage/history?months=6")
    assert resp.status_code == 200
    assert resp.json()["usage_history"] == []
