"""
Tests for managed-warehouse query execution (phase 4).

Covers the EngineResult→QueryResult adaptation (the field mapping the AI path
relies on) and the graceful failure when managed storage isn't configured.
"""
from backend.config import settings
from backend.services import managed_query
from backend.services.duckdb_engine import EngineResult


def test_to_query_result_maps_fields():
    er = EngineResult(
        success=True,
        columns=["a", "b"],
        rows=[{"a": 1, "b": 2}],
        row_count=1,
        execution_time_ms=7,
        truncated=True,
    )
    qr = managed_query.to_query_result(er)
    assert qr.success is True
    assert qr.data == [{"a": 1, "b": 2}]  # rows -> data
    assert qr.columns == ["a", "b"]
    assert qr.row_count == 1
    assert qr.execution_time_ms == 7
    assert qr.truncated is True


def test_to_query_result_carries_error():
    er = EngineResult(success=False, error="boom")
    qr = managed_query.to_query_result(er)
    assert qr.success is False
    assert qr.error == "boom"


def test_execute_returns_failed_result_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "MANAGED_STORAGE_BUCKET", None, raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_ACCESS_KEY", None, raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_SECRET_KEY", None, raising=False)
    qr = managed_query.execute(12, "SELECT 1")
    assert qr.success is False
    assert qr.error  # never raises; surfaces as a query error
