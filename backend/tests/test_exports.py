"""Tests for data export routes."""
import json
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes.exports import router


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
    session = MagicMock()
    return session


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.organization_id = 42
    return user


def _make_run():
    run = MagicMock()
    run.id = 10
    run.public_id = "abc-123"
    run.pipeline_id = 5
    run.pipeline.name = "My Pipeline"
    run.status.value = "completed"
    run.started_at.isoformat.return_value = "2025-01-01T00:00:00"
    run.completed_at.isoformat.return_value = "2025-01-01T00:05:00"
    run.rows_read = 100
    run.rows_written = 95
    run.bytes_read = 2048
    run.bytes_written = 1900
    run.duration_seconds = 300
    run.error_message = ""
    run.retry_count = 0
    run.is_retry = False
    run.created_at.isoformat.return_value = "2025-01-01T00:00:00"
    return run


def _setup_query_chain(mock_db, results):
    q = MagicMock()
    mock_db.query.return_value = q
    q.join.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value = results
    return q


class TestExportRunsCsv:
    def test_export_runs_csv(self, mock_db, mock_user):
        _setup_query_chain(mock_db, [_make_run()])
        app = _make_app(mock_db, mock_user)
        client = TestClient(app)

        resp = client.get("/exports/runs", params={"format": "csv"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "pipeline_runs.csv" in resp.headers["content-disposition"]
        assert "My Pipeline" in resp.text


class TestExportRunsJson:
    def test_export_runs_json(self, mock_db, mock_user):
        _setup_query_chain(mock_db, [_make_run()])
        app = _make_app(mock_db, mock_user)
        client = TestClient(app)

        resp = client.get("/exports/runs", params={"format": "json"})
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        data = json.loads(resp.text)
        assert isinstance(data, list)
        assert data[0]["pipeline_name"] == "My Pipeline"


class TestExportAuditLogsCsv:
    def test_export_audit_logs_csv(self, mock_db, mock_user):
        log = MagicMock()
        log.public_id = "log-uuid-1"
        log.user_id = 1
        log.action = "create"
        log.resource_type = "pipeline"
        log.resource_id = "5"
        log.changes = {"name": "new"}
        log.ip_address = "127.0.0.1"
        log.user_agent = "test-agent"
        log.created_at.isoformat.return_value = "2025-01-01T00:00:00"

        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value = [log]

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)

        resp = client.get("/exports/audit-logs", params={"format": "csv"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "audit_logs.csv" in resp.headers["content-disposition"]
        assert "create" in resp.text


class TestExportRequiresAuth:
    def test_export_requires_auth(self, mock_db):
        app = _make_app(mock_db)  # no current_user
        client = TestClient(app)
        resp = client.get("/exports/runs")
        assert resp.status_code in (401, 403, 422, 500)
