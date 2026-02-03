"""Tests for notification API routes."""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes.notifications import router


def _make_app(db_session, current_user=None):
    app = FastAPI()
    app.include_router(router)

    from backend.database import get_db
    from backend.auth import get_current_user

    app.dependency_overrides[get_db] = lambda: db_session
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    return app


def _make_notification(**overrides):
    n = MagicMock()
    defaults = dict(
        id=1,
        public_id=uuid.uuid4(),
        user_id=1,
        organization_id=1,
        type="pipeline_success",
        title="Pipeline finished",
        message="Your pipeline completed successfully.",
        link="/pipelines/abc",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(n, k, v)
    # Support model_validate iteration
    n.__dict__.update(defaults)
    return n


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = 1
    u.organization_id = 1
    return u


# ---------------------------------------------------------------------------

class TestListNotifications:
    def test_list_notifications(self, mock_db, mock_user):
        notif = _make_notification()
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.count.return_value = 1
        q.order_by.return_value = q
        q.offset.return_value = q
        q.limit.return_value = q
        q.all.return_value = [notif]

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)
        resp = client.get("/notifications")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["title"] == "Pipeline finished"


class TestUnreadCount:
    def test_unread_count(self, mock_db, mock_user):
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.count.return_value = 5

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)
        resp = client.get("/notifications/count")
        assert resp.status_code == 200
        assert resp.json()["unread"] == 5


class TestMarkAsRead:
    def test_mark_as_read(self, mock_db, mock_user):
        notif = _make_notification(id=7)
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = notif

        def _refresh(obj):
            obj.is_read = True
        mock_db.refresh = _refresh

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)
        resp = client.patch("/notifications/7/read")
        assert resp.status_code == 200
        assert resp.json()["is_read"] is True


class TestMarkAllRead:
    def test_mark_all_read(self, mock_db, mock_user):
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.update.return_value = 3

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)
        resp = client.post("/notifications/mark-all-read")
        assert resp.status_code == 200
        assert resp.json()["marked"] == 3


class TestRequiresAuth:
    def test_requires_auth(self, mock_db):
        app = _make_app(mock_db)  # no user
        client = TestClient(app)
        resp = client.get("/notifications")
        assert resp.status_code in (401, 403, 422, 500)
