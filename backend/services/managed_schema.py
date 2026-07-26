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


def schema_from_engine(engine: DuckDBAnalyticsEngine) -> Dict[str, Any]:
    """Convert the engine's raw introspection into the LLM schema shape."""
    raw = engine.introspect()
    schema: Dict[str, Any] = {}
    for table, cols in raw.items():
        columns: List[Dict[str, str]] = [
            {"name": c["name"], "type": c["type"], "description": ""} for c in cols
        ]
        schema[table] = {
            "columns": columns,
            "source": "managed",
            "description": f"Synced table '{table}' in the managed warehouse",
        }
    return schema


def is_managed(db: Session, organization_id: int) -> bool:
    """True when this org has a provisioned managed warehouse and storage is on."""
    return (
        managed_storage.is_configured()
        and managed_storage.get_managed_destination(db, organization_id) is not None
    )


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
        s3 = managed_storage.engine_s3_config(organization_id)
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
