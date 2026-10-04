"""Async smoke tests for the metrics router (empty org → aggregations return zeros)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.api.main import app
from backend.auth import get_current_user
from backend.async_database import get_async_db
from backend.tests.async_helpers import AuthUser, override_async_db, seeded_org_user

BASE = "/api/v1/metrics"


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
async def test_overview_empty_org(as_user, aclient):
    resp = await aclient.get(f"{BASE}/overview?timerange=7d")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_runs"] == 0
    assert body["success_rate"] == 0
    assert body["active_pipelines"] == 0


@pytest.mark.asyncio
async def test_system_health(as_user, aclient):
    resp = await aclient.get(f"{BASE}/system-health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "healthy"
    assert body["sources"] == 0
    assert body["destinations"] == 0


@pytest.mark.asyncio
async def test_performance_missing_pipeline(as_user, aclient):
    resp = await aclient.get(f"{BASE}/pipeline/999999/performance")
    assert resp.status_code == 200
    assert resp.json() == {"error": "Pipeline not found"}
