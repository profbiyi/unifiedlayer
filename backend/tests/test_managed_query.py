"""
Tests for managed-warehouse query execution (phase 4).

Covers the EngineResult→QueryResult adaptation (the field mapping the AI path
relies on) and the graceful failure when managed storage isn't configured.
"""
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


def test_execute_returns_failed_result_when_no_managed_warehouse(db, test_org):
    # No managed destination for this org -> resolve raises -> clean failed result.
    qr = managed_query.execute(db, test_org.id, "SELECT 1")
    assert qr.success is False
    assert qr.error  # never raises; surfaces as a query error
