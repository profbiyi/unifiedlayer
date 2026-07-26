"""
Managed-warehouse schema context (phase 3).

Builds the LLM schema context for a managed org from its **actual** synced
tables in the bucket — via the DuckDB engine — instead of the hardcoded
per-connector map in ``ai_schema_context``. This is what lets Ask AI and model
generation work for any connector a real user syncs.

Returns the same shape as ``ai_schema_context.get_org_schema`` so phase 4 can
swap it in with no changes at the call sites:

    {table_name: {"columns": [{"name","type","description"}],
                  "source": "managed", "description": ...}}
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.services import managed_storage
from backend.services.duckdb_engine import DuckDBAnalyticsEngine

logger = logging.getLogger(__name__)

# org_id -> (fetched_at, schema)
_cache: Dict[int, tuple] = {}
CACHE_TTL_SECONDS = 300


# Cap profiling work on very wide tables.
_MAX_PROFILE_COLUMNS = 40
_LOW_CARDINALITY_MAX = 20
_NUMERIC_TYPES = ("INT", "DECIMAL", "DOUBLE", "FLOAT", "NUMERIC", "REAL", "HUGEINT")
_TEXT_TYPES = ("VARCHAR", "CHAR", "TEXT", "STRING", "BOOL", "ENUM")


def _q(ident: str) -> str:
    """Quote a DuckDB identifier."""
    return '"' + ident.replace('"', '""') + '"'


def _profile_column(engine: DuckDBAnalyticsEngine, table: str, name: str, col_type: str) -> str:
    """
    A short semantic hint for a column, so the LLM stops guessing: the distinct
    values of a low-cardinality category (e.g. status), or the numeric range
    (helps it infer scale/units). Empty string when nothing useful applies.

    Uses read-only SELECTs on the already-materialised, sandboxed table.
    """
    upper = col_type.upper()
    tq, cq = _q(table), _q(name)
    try:
        if any(k in upper for k in _NUMERIC_TYPES):
            r = engine.execute(f"SELECT MIN({cq}) AS lo, MAX({cq}) AS hi FROM {tq}")
            if r.success and r.rows and r.rows[0].get("lo") is not None:
                return f"range {r.rows[0]['lo']}–{r.rows[0]['hi']}"
        elif any(k in upper for k in _TEXT_TYPES):
            r = engine.execute(
                f"SELECT DISTINCT {cq} AS v FROM {tq} "
                f"WHERE {cq} IS NOT NULL LIMIT {_LOW_CARDINALITY_MAX + 1}"
            )
            if r.success and 0 < len(r.rows) <= _LOW_CARDINALITY_MAX:
                return "values: " + ", ".join(str(row["v"]) for row in r.rows)
    except Exception:  # noqa: BLE001 — profiling is best-effort, never fatal
        pass
    return ""


def schema_from_engine(engine: DuckDBAnalyticsEngine) -> Dict[str, Any]:
    """
    Convert the engine's introspection into the LLM schema shape, enriched with
    per-column hints (distinct values / numeric ranges) so generated SQL uses
    real category values and correct scale.
    """
    raw = engine.introspect()
    schema: Dict[str, Any] = {}
    for table, cols in raw.items():
        columns: List[Dict[str, str]] = []
        for c in cols[:_MAX_PROFILE_COLUMNS]:
            columns.append({
                "name": c["name"],
                "type": c["type"],
                "description": _profile_column(engine, table, c["name"], c["type"]),
            })
        schema[table] = {
            "columns": columns,
            "source": "managed",
            "description": f"Synced table '{table}' in the managed warehouse",
        }
    return schema


def is_managed(db: Session, organization_id: int) -> bool:
    """
    True when this org has a usable managed warehouse — internal (needs the
    platform storage configured) or external (self-contained: the destination
    carries its own bucket credentials).
    """
    dest = managed_storage.get_managed_destination(db, organization_id)
    if not dest:
        return False
    if (dest.config or {}).get("aws_access_key_id"):
        return True  # external bucket, self-contained
    return managed_storage.is_configured()  # internal needs platform creds


def get_org_schema(db: Session, organization_id: int) -> Dict[str, Any]:
    """
    Real schema for a managed org, read live from its bucket. Returns {} when the
    org isn't managed, storage isn't configured, or the bucket can't be read —
    callers fall back to the legacy schema source in that case.
    """
    if not is_managed(db, organization_id):
        return {}

    cached = _cache.get(organization_id)
    if cached and datetime.now(timezone.utc) - cached[0] < timedelta(seconds=CACHE_TTL_SECONDS):
        return cached[1]

    try:
        s3 = managed_storage.resolve_engine_config(db, organization_id)
        with DuckDBAnalyticsEngine(s3=s3) as engine:
            engine.register_all()
            schema = schema_from_engine(engine)
    except Exception as exc:  # noqa: BLE001 — never let schema-read break Ask AI
        logger.warning("Managed schema read failed for org %s: %s", organization_id, exc)
        return {}

    _cache[organization_id] = (datetime.now(timezone.utc), schema)
    return schema


def invalidate(organization_id: int) -> None:
    """Drop the cached schema (e.g. after a sync writes new tables)."""
    _cache.pop(organization_id, None)
