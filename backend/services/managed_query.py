"""
Managed-warehouse query execution (phase 4).

Runs a validated, read-only SELECT for a managed org against its bucket via the
sandboxed DuckDB engine, and adapts the result to the ``QueryResult`` shape the
AI assistant already consumes — so wiring it in is a drop-in alongside the
existing Postgres ``QueryExecutor``.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from backend.services import managed_storage
from backend.services.duckdb_engine import EngineResult
from backend.services.duckdb_engine import DuckDBAnalyticsEngine
from backend.services.query_executor import QueryResult

logger = logging.getLogger(__name__)


def to_query_result(result: EngineResult) -> QueryResult:
    """Adapt an engine EngineResult to the QueryResult the AI path expects."""
    return QueryResult(
        success=result.success,
        data=result.rows,
        columns=result.columns,
        row_count=result.row_count,
        execution_time_ms=result.execution_time_ms,
        error=result.error,
        truncated=result.truncated,
    )


def execute(
    db: Session,
    organization_id: int,
    sql: str,
    *,
    max_rows: int = 1000,
    timeout_seconds: int = 30,
) -> QueryResult:
    """
    Execute read-only SQL for a managed org against its warehouse bucket
    (internal or the customer's own external bucket). Returns a failed
    QueryResult (never raises) so the AI path can surface a clean error.
    """
    try:
        s3 = managed_storage.resolve_engine_config(db, organization_id)
        with DuckDBAnalyticsEngine(s3=s3) as engine:
            engine.register_all()
            result = engine.execute(sql, max_rows=max_rows, timeout_seconds=timeout_seconds)
        return to_query_result(result)
    except Exception as exc:  # noqa: BLE001 — surface as a query error, don't 500
        logger.warning("Managed query failed for org %s: %s", organization_id, exc)
        return QueryResult(
            success=False,
            data=[],
            columns=[],
            row_count=0,
            execution_time_ms=0,
            error=f"Managed warehouse query failed: {str(exc)[:200]}",
        )
