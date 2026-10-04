"""Async smoke tests for the SME insights router (empty org)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.api.main import app
from backend.auth import get_current_user
from backend.async_database import get_async_db
from backend.tests.async_helpers import AuthUser, override_async_db, seeded_org_user

BASE = "/api/v1/insights"


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
async def test_dashboard_empty(as_user, aclient):
    resp = await aclient.get(f"{BASE}/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["pipeline_runs"] == 0
    assert body["data_health"]["healthy_pipelines"] == 0


@pytest.mark.asyncio
async def test_roi_empty(as_user, aclient):
    resp = await aclient.get(f"{BASE}/roi")
    assert resp.status_code == 200
    body = resp.json()
    assert body["time_saved"]["hours"] == 0
    assert body["automation"]["active_pipelines"] == 0


@pytest.mark.asyncio
async def test_static_cash_flow(as_user, aclient):
    # static handler (no DB) still served correctly
    resp = await aclient.get(f"{BASE}/cash-flow?days=30")
    assert resp.status_code == 200
    assert "open_banking" in resp.json()["available_when_connected"]
