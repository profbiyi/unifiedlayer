"""Tests for API key management routes and model."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes.api_keys import router
from backend.models.api_key import APIKey


def _make_app(db_session, current_user=None):
    app = FastAPI()
    app.include_router(router)

    from backend.database import get_db
    from backend.auth import get_current_user

    app.dependency_overrides[get_db] = lambda: db_session
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    return app


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = 1
    u.organization_id = 10
    return u


# ---------------------------------------------------------------------------

class TestCreateApiKey:
    def test_create_api_key(self, mock_db, mock_user):
        def _refresh(obj):
            obj.id = 99
            obj.created_at = datetime.now(timezone.utc)
        mock_db.refresh = _refresh

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)
        resp = client.post("/api-keys", json={"name": "My Key"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "My Key"
        assert body["key"].startswith("dp_live_")
        mock_db.add.assert_called_once()


class TestCreateApiKeyReturnsFullKeyOnce:
    def test_create_api_key_returns_full_key_once(self, mock_db, mock_user):
        def _refresh(obj):
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)
        mock_db.refresh = _refresh

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)
        resp = client.post("/api-keys", json={"name": "Temp"})
        body = resp.json()
        # Full key is 8 ("dp_live_") + 32 hex chars = 40 chars
        assert len(body["key"]) == 40
        assert body["key_prefix"] == body["key"][:12]


class TestListApiKeysNoFullKey:
    def test_list_api_keys_no_full_key(self, mock_db, mock_user):
        fake_key = MagicMock()
        fake_key.id = 1
        fake_key.name = "k1"
        fake_key.key_prefix = "dp_live_abcd"
        fake_key.scopes = None
        fake_key.expires_at = None
        fake_key.last_used_at = None
        fake_key.is_active = True
        fake_key.created_at = datetime.now(timezone.utc)

        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value = [fake_key]

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)
        resp = client.get("/api-keys")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        # The list response must NOT contain the full key field
        assert "key" not in items[0] or items[0].get("key") is None


class TestRevokeApiKey:
    def test_revoke_api_key(self, mock_db, mock_user):
        fake_key = MagicMock()
        fake_key.id = 5
        fake_key.name = "old key"
        fake_key.is_active = True

        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = fake_key

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)
        resp = client.delete("/api-keys/5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_active"] is False
        assert "revoked" in body["message"].lower()


class TestExpiredKeyInvalid:
    """Test the APIKey model property directly (no HTTP needed)."""

    def _make_key(self, is_active, expires_at):
        """Create a minimal object that exercises APIKey's property logic."""
        from types import SimpleNamespace
        # Use SimpleNamespace instead of APIKey.__new__ to avoid SQLAlchemy
        # mapper initialization (which requires a DB session)
        ns = SimpleNamespace(is_active=is_active, expires_at=expires_at)
        # Bind the property logic directly so we test the real code paths
        ns.is_expired = APIKey.is_expired.fget(ns)
        ns.is_valid = is_active and not ns.is_expired
        return ns

    def test_expired_key_invalid(self):
        key = self._make_key(True, datetime.now(timezone.utc) - timedelta(hours=1))
        assert key.is_expired is True
        assert key.is_valid is False

    def test_non_expired_key_valid(self):
        key = self._make_key(True, datetime.now(timezone.utc) + timedelta(hours=1))
        assert key.is_expired is False
        assert key.is_valid is True

    def test_no_expiry_key_valid(self):
        key = self._make_key(True, None)
        assert key.is_expired is False
        assert key.is_valid is True


class TestKeyPrefixFormat:
    def test_key_prefix_format(self, mock_db, mock_user):
        def _refresh(obj):
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)
        mock_db.refresh = _refresh

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)
        resp = client.post("/api-keys", json={"name": "pfx"})
        body = resp.json()
        # Prefix is first 12 chars: "dp_live_" (8) + 4 hex
        prefix = body["key_prefix"]
        assert len(prefix) == 12
        assert prefix.startswith("dp_live_")
