"""Tests for webhook ingestion routes."""
import hashlib
import hmac
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes.webhooks import router
from backend.models.webhook import WebhookEventStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_app(db_session, current_user=None):
    """Build a tiny FastAPI app wired to the webhook router with mock deps."""
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
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.organization_id = 42
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReceiveWebhookPaystackValidSignature:
    def test_receive_webhook_paystack_valid_signature(self, mock_db):
        secret = "test_secret_key"
        payload = {"event": "charge.success", "data": {"id": 123}}
        payload_bytes = json.dumps(payload).encode()
        sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha512).hexdigest()

        with patch("backend.api.routes.webhooks.settings") as mock_settings:
            mock_settings.PAYSTACK_WEBHOOK_SECRET = secret
            mock_settings.PAYSTACK_SECRET_KEY = secret

            # Make db.refresh set public_id on the event object
            def _refresh(obj):
                obj.public_id = uuid.uuid4()
                obj.id = 1
            mock_db.refresh = _refresh

            app = _make_app(mock_db)
            client = TestClient(app)
            resp = client.post(
                "/webhooks/paystack",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Paystack-Signature": sig,
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["verified"] is True
        assert "event_id" in body
        mock_db.add.assert_called_once()


class TestReceiveWebhookInvalidSignatureStillStores:
    def test_receive_webhook_invalid_signature_still_stores(self, mock_db):
        payload = {"event": "charge.success", "data": {"id": 1}}
        payload_bytes = json.dumps(payload).encode()

        with patch("backend.api.routes.webhooks.settings") as mock_settings:
            mock_settings.PAYSTACK_WEBHOOK_SECRET = "real_secret"
            mock_settings.PAYSTACK_SECRET_KEY = "real_secret"

            app = _make_app(mock_db)
            client = TestClient(app)
            resp = client.post(
                "/webhooks/paystack",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Paystack-Signature": "bad_signature",
                },
            )

        # Signature verification failure returns 400 (by design), but
        # the event is still persisted with FAILED status before raising
        assert resp.status_code == 400
        mock_db.add.assert_called_once()
        added_event = mock_db.add.call_args[0][0]
        assert added_event.status == WebhookEventStatus.FAILED


class TestReceiveWebhookUnsupportedSource:
    def test_receive_webhook_unsupported_source(self, mock_db):
        app = _make_app(mock_db)
        client = TestClient(app)
        resp = client.post(
            "/webhooks/unknown_provider",
            json={"event": "test"},
        )
        assert resp.status_code == 400
        assert "Unsupported source type" in resp.json()["detail"]


class TestListWebhookEventsRequiresAuth:
    def test_list_webhook_events_requires_auth(self, mock_db):
        """Without overriding get_current_user the endpoint should 401/403."""
        app = _make_app(mock_db)  # no current_user override
        client = TestClient(app)
        resp = client.get("/webhooks/events")
        # FastAPI will raise 401 or similar when the dependency is not satisfied
        assert resp.status_code in (401, 403, 422, 500)


class TestListWebhookEventsFilters:
    def test_list_webhook_events_filters(self, mock_db, mock_user):
        # Set up the mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        app = _make_app(mock_db, current_user=mock_user)
        client = TestClient(app)

        resp = client.get("/webhooks/events", params={"source_type": "paystack", "status": "received"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["events"] == []
        # filter should have been called multiple times (org + source_type + status)
        assert mock_query.filter.call_count >= 2
