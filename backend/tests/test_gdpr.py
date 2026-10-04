"""Async tests for the GDPR router."""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.api.main import app
from backend.auth import get_current_user
from backend.async_database import get_async_db
from backend.tests.async_helpers import override_async_db, seeded_org_user

BASE = "/api/v1/gdpr"


class _FullUser:
    """Stand-in with all the attributes export_my_data serializes."""
    def __init__(self, user_id, org_id):
        self.id = user_id
        self.organization_id = org_id
        self.is_superuser = False
        self.public_id = uuid.uuid4()
        self.email = "x@example.com"
        self.username = "x"
        self.full_name = None
        self.is_active = True
        self.email_verified = True
        self.last_login = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


@pytest_asyncio.fixture
async def aclient():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


@pytest_asyncio.fixture
async def as_user():
    with seeded_org_user() as (user_id, org_id):
        app.dependency_overrides[get_current_user] = lambda: _FullUser(user_id, org_id)
        app.dependency_overrides[get_async_db] = override_async_db
        try:
            yield (user_id, org_id)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_async_db, None)


@pytest.mark.asyncio
async def test_export_my_data(as_user, aclient):
    resp = await aclient.get(f"{BASE}/export-my-data")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert "user" in body and "organization" in body
    assert body["data_sources"] == []  # empty org


@pytest.mark.asyncio
async def test_data_processing_info_public(aclient):
    # static, no auth
    resp = await aclient.get(f"{BASE}/data-processing-info")
    assert resp.status_code == 200
    assert "data_collected" in resp.json()
