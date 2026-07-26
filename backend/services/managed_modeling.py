"""
Managed-warehouse schema context for model generation (phase 4b).

The AI modeler's ``analyze_schema`` connects to a SQL warehouse to introspect
tables — which doesn't apply to a managed object-storage bucket. This module
builds the same ``SchemaContext`` from the org's real Parquet tables via the
DuckDB engine, so model generation works for managed orgs too.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.services import managed_storage
from backend.services.duckdb_engine import DuckDBAnalyticsEngine
from backend.services.schema_analyzer import ColumnInfo, SchemaContext, TableSchema

_DATASET = "main"


def schema_context_from_introspection(
    raw: Dict[str, List[Dict[str, str]]],
    tables: Optional[List[str]] = None,
) -> SchemaContext:
    """Map the engine's {table: [{name,type}]} introspection to a SchemaContext."""
    wanted = set(tables) if tables else None
    table_schemas: List[TableSchema] = []
    total_columns = 0
    for name, cols in raw.items():
        if wanted is not None and name not in wanted:
            continue
        columns = [
            ColumnInfo(name=c["name"], data_type=c["type"], nullable=True) for c in cols
        ]
        total_columns += len(columns)
        table_schemas.append(
            TableSchema(name=name, schema_name=_DATASET, columns=columns)
        )
    return SchemaContext(
        tables=table_schemas,
        destination_type="managed",
        dataset_name=_DATASET,
        detected_relationships=[],
        total_tables=len(table_schemas),
        total_columns=total_columns,
    )


def build_schema_context(
    db: Session,
    organization_id: int,
    tables: Optional[List[str]] = None,
) -> SchemaContext:
    """Read the org's managed bucket via DuckDB and build a modeling SchemaContext."""
    s3 = managed_storage.resolve_engine_config(db, organization_id)
    with DuckDBAnalyticsEngine(s3=s3) as engine:
        engine.register_all()
        raw: Dict[str, Any] = engine.introspect()
    return schema_context_from_introspection(raw, tables)
