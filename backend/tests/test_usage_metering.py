"""Tests for usage metering utility and billing usage endpoints."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes.billing import router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    user = MagicMock()
    user.id = 1
    user.organization_id = 42
    return user


def _make_usage_record(**overrides):
    rec = MagicMock()
    rec.rows_synced = overrides.get("rows_synced", 0)
    rec.api_calls = overrides.get("api_calls", 0)
    rec.pipeline_runs = overrides.get("pipeline_runs", 0)
    rec.storage_bytes = overrides.get("storage_bytes", 0)
    rec.active_connectors = overrides.get("active_connectors", 0)
    rec.rows_limit = overrides.get("rows_limit", 10000)
    rec.api_calls_limit = overrides.get("api_calls_limit", 5000)
    rec.rows_overage = overrides.get("rows_overage", 0)
    rec.period_year = overrides.get("period_year", 2025)
    rec.period_month = overrides.get("period_month", 1)
    return rec


def _make_subscription(plan_value="starter"):
    from backend.models.billing import SubscriptionPlan
    sub = MagicMock()
    sub.plan = SubscriptionPlan(plan_value)
    return sub


# ---------------------------------------------------------------------------
# Unit tests for record_usage
# ---------------------------------------------------------------------------

class TestRecordUsageCreatesRecord:
    @patch("backend.utils.usage.BillingService")
    def test_record_usage_creates_record(self, mock_bs, mock_db):
        rec = _make_usage_record()
        mock_bs.get_or_create_usage_record.return_value = rec
        mock_db.query.return_value.filter.return_value.first.return_value = _make_subscription()

        from backend.utils.usage import record_usage
        result = record_usage(mock_db, organization_id=42, rows=100)

        mock_bs.get_or_create_usage_record.assert_called_once_with(mock_db, 42)
        assert result["record"] is rec
        mock_db.commit.assert_called_once()


class TestRecordUsageIncrements:
    @patch("backend.utils.usage.BillingService")
    def test_record_usage_increments(self, mock_bs, mock_db):
        rec = _make_usage_record(rows_synced=50, api_calls=10, pipeline_runs=2)
        mock_bs.get_or_create_usage_record.return_value = rec
        mock_db.query.return_value.filter.return_value.first.return_value = _make_subscription()

        from backend.utils.usage import record_usage
        record_usage(mock_db, organization_id=42, rows=25, api_calls=5, pipeline_runs=1)

        assert rec.rows_synced == 75
        assert rec.api_calls == 15
        assert rec.pipeline_runs == 3


class TestRecordUsageWarnsNearLimit:
    @patch("backend.utils.usage.BillingService")
    def test_record_usage_warns_near_limit(self, mock_bs, mock_db):
        rec = _make_usage_record(rows_synced=8500, rows_limit=10000)
        mock_bs.get_or_create_usage_record.return_value = rec
        mock_db.query.return_value.filter.return_value.first.return_value = _make_subscription()

        from backend.utils.usage import record_usage
        result = record_usage(mock_db, organization_id=42, rows=500)

        warnings = result["warnings"]
        row_warnings = [w for w in warnings if w["metric"] == "rows_synced"]
        assert len(row_warnings) == 1
        assert row_warnings[0]["status"] == "near_limit"


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

class TestGetUsageEndpoint:
    @patch("backend.api.routes.billing.BillingService")
    def test_get_usage_endpoint(self, mock_bs, mock_db, mock_user):

        rec = _make_usage_record(rows_synced=500, api_calls=100, pipeline_runs=3, active_connectors=2)
        mock_bs.get_or_create_usage_record.return_value = rec
        mock_bs.get_subscription.return_value = _make_subscription()

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)

        resp = client.get("/billing/usage")
        assert resp.status_code == 200
        body = resp.json()
        assert "rows_synced" in body
        assert body["rows_synced"]["current"] == 500


class TestUsageHistoryEndpoint:
    @patch("backend.api.routes.billing.BillingService")
    def test_usage_history_endpoint(self, mock_bs, mock_db, mock_user):
        rec = _make_usage_record(rows_synced=200)
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = [rec]

        mock_bs.get_subscription.return_value = _make_subscription()

        app = _make_app(mock_db, mock_user)
        client = TestClient(app)

        resp = client.get("/billing/usage/history", params={"months": 3})
        assert resp.status_code == 200
        body = resp.json()
        assert "records" in body
        assert len(body["records"]) == 1
