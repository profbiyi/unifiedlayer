"""
Tests for managed-warehouse model-generation schema context (phase 4b).

Covers the introspection→SchemaContext mapping the model generator consumes;
the live bucket read needs S3 and is exercised end-to-end once R2 is configured.
"""
from backend.services.managed_modeling import schema_context_from_introspection


def test_schema_context_from_introspection():
    raw = {
        "payments": [
            {"name": "id", "type": "BIGINT"},
            {"name": "amount", "type": "DECIMAL(18,2)"},
        ],
        "customers": [{"name": "id", "type": "BIGINT"}],
    }
    ctx = schema_context_from_introspection(raw)

    assert ctx.destination_type == "managed"
    assert ctx.dataset_name == "main"
    assert ctx.total_tables == 2
    assert ctx.total_columns == 3
    assert {t.name for t in ctx.tables} == {"payments", "customers"}

    payments = next(t for t in ctx.tables if t.name == "payments")
    assert payments.schema_name == "main"
    assert {c.name for c in payments.columns} == {"id", "amount"}
    assert payments.columns[0].nullable is True


def test_schema_context_respects_table_filter():
    raw = {
        "a": [{"name": "x", "type": "INTEGER"}],
        "b": [{"name": "y", "type": "INTEGER"}],
    }
    ctx = schema_context_from_introspection(raw, tables=["a"])
    assert ctx.total_tables == 1
    assert ctx.tables[0].name == "a"
