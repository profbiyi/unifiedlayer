"""
Chunked backfill orchestration + execution (Celery).

``plan_and_dispatch_backfill`` fans out one ``run_backfill_chunk`` task per
``[start, end)`` window (from ``backfill_planner``) across the ``pipelines``-queue
workers, so a large historical load runs in parallel instead of one monolithic,
time-boxed job. Each chunk owns a disjoint slice and **appends**, so a chunk is
independently retryable and rows load exactly once.

Phase 2 supports **Postgres** sources (the connector that matters for a TB-scale
DB backfill). Other connectors get ranged extraction in a later phase, and
per-chunk run tracking / resume UI is layered on after that.
"""
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from backend.celery_app import celery_app

logger = logging.getLogger(__name__)

# A chunk is bounded, but a wide window can still be sizeable — keep the limits
# env-configurable, same idea as run_pipeline.
_CHUNK_SOFT = int(os.getenv("BACKFILL_CHUNK_SOFT_TIME_LIMIT", "3600"))
_CHUNK_HARD = int(os.getenv("BACKFILL_CHUNK_TIME_LIMIT", "3900"))


def _pipeline_context(pipeline_id: int) -> Dict[str, Any]:
    from backend.database import get_db_session
    from backend.models.pipeline import Pipeline

    db = get_db_session()
    try:
        pipe = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipe:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        return {
            "source_type": pipe.source.source_type.value,
            "source_config": dict(pipe.source.config or {}),
            "dest_type": pipe.destination.destination_type.value,
            "dest_config": dict(pipe.destination.config or {}),
            "pipeline_name": pipe.name,
        }
    finally:
        db.close()


def execute_backfill_chunk(
    pipeline_id: int, table: str, column: str, start: Any, end: Any
) -> Dict[str, Any]:
    """Extract one ``[start, end)`` slice from a Postgres source and load it.

    ``start``/``end`` arrive as JSON-safe values (ISO strings for time windows,
    ints for key windows) — Postgres casts them against the column type in the
    WHERE clause, so no explicit parsing is needed here.
    """
    from backend.prefect_flows.pipeline_flow import load_to_destination
    from backend.services.backfill_extract import postgres_ranged_source

    ctx = _pipeline_context(pipeline_id)
    if ctx["source_type"] != "postgres":
        raise NotImplementedError(
            f"Ranged backfill not yet supported for source type '{ctx['source_type']}'"
        )

    source = postgres_ranged_source(ctx["source_config"], table, column, start, end)
    name = f"backfill_{pipeline_id}_{table}".replace(".", "_")
    # Each chunk owns a disjoint slice → APPEND (not the pipeline's merge/replace
    # default) so chunks load exactly once with no cross-chunk merge coordination.
    dest_config = dict(ctx["dest_config"])
    dest_config["_dlt_options"] = {"write_disposition": "append"}
    stats = load_to_destination.fn(source, dest_config, ctx["dest_type"], name)
    logger.info(
        "backfill chunk pipeline=%s table=%s [%s, %s) rows=%s",
        pipeline_id, table, start, end, stats.get("rows_written"),
    )
    return {"table": table, "start": str(start), "end": str(end), "stats": stats}


@celery_app.task(
    bind=True,
    name="backend.tasks.backfill_tasks.run_backfill_chunk",
    soft_time_limit=_CHUNK_SOFT,
    time_limit=_CHUNK_HARD,
)
def run_backfill_chunk(self, pipeline_id: int, table: str, column: str, start: Any, end: Any):
    return execute_backfill_chunk(pipeline_id, table, column, start, end)


def _serialize_bound(value: Any) -> Any:
    """Make a chunk bound JSON-safe for Celery transport."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return int(value) if isinstance(value, bool) is False and isinstance(value, int) else value


def plan_and_dispatch_backfill(
    pipeline_id: int,
    table: str,
    column: str,
    *,
    strategy: Optional[str] = None,
    window_days: int = 30,
    chunk_size: int = 1_000_000,
    dispatch: bool = True,
) -> Dict[str, Any]:
    """Plan a table's backfill into chunks and (optionally) fan them out.

    ``strategy`` is inferred from the partition column's value type when omitted:
    a timestamp column -> ``time`` windows of ``window_days``; an integer column
    -> ``key`` windows of ``chunk_size`` ids. Set ``dispatch=False`` to just plan.
    """
    from backend.services.backfill_extract import get_range_bounds
    from backend.services.backfill_planner import plan_key_chunks, plan_time_chunks

    ctx = _pipeline_context(pipeline_id)
    if ctx["source_type"] != "postgres":
        raise NotImplementedError(
            f"Ranged backfill not yet supported for source type '{ctx['source_type']}'"
        )

    lo, hi, n = get_range_bounds(ctx["source_config"], table, column)
    if n == 0 or lo is None:
        return {"table": table, "chunks": 0, "dispatched": 0, "rows_estimate": 0, "note": "empty table"}

    if strategy is None:
        strategy = "time" if isinstance(lo, (datetime, date)) else "key"

    if strategy == "time":
        plan = plan_time_chunks(
            column, lo, hi + timedelta(days=window_days), timedelta(days=window_days)
        )
    else:
        plan = plan_key_chunks(column, int(lo), int(hi), chunk_size)

    dispatched = 0
    for chunk in plan.chunks:
        s, e = _serialize_bound(chunk.start), _serialize_bound(chunk.end)
        if dispatch:
            run_backfill_chunk.delay(pipeline_id, table, column, s, e)
            dispatched += 1

    return {
        "table": table,
        "column": column,
        "strategy": strategy,
        "chunks": plan.chunk_count,
        "dispatched": dispatched,
        "rows_estimate": n,
        "min": str(lo),
        "max": str(hi),
    }
