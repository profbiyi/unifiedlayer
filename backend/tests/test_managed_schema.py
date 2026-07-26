"""
Tests for managed-warehouse schema context (phase 3).

The live bucket read needs S3, so these cover the parts testable without one:
the engine→LLM-shape conversion (over a local engine) and the graceful-empty
fallbacks (not configured / not provisioned).
"""
import duckdb

from backend.config import settings
from backend.services import managed_schema, managed_storage
from backend.services.duckdb_engine import DuckDBAnalyticsEngine


def _write_parquet(path, rows_sql):
    con = duckdb.connect()
    con.execute(f"COPY ({rows_sql}) TO '{path}' (FORMAT PARQUET)")
    con.close()


def test_schema_from_engine_shape(tmp_path):
    base = tmp_path / "org-30"
    base.mkdir()
    _write_parquet(
        str(base / "payments.parquet"),
        "SELECT * FROM (VALUES (1, 5000, 'NGN')) AS t(id, amount, currency)",
    )
    with DuckDBAnalyticsEngine(base_path=str(base)) as engine:
        engine.register_all()
        schema = managed_schema.schema_from_engine(engine)

    assert "payments" in schema
    assert schema["payments"]["source"] == "managed"
    names = {c["name"] for c in schema["payments"]["columns"]}
    assert {"id", "amount", "currency"} <= names
    # every column carries the {name,type,description} keys the LLM context needs
    for col in schema["payments"]["columns"]:
        assert set(col.keys()) == {"name", "type", "description"}


def test_get_org_schema_empty_when_storage_unconfigured(monkeypatch, db, test_org):
    monkeypatch.setattr(settings, "MANAGED_STORAGE_BUCKET", None, raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_ACCESS_KEY", None, raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_SECRET_KEY", None, raising=False)
    assert managed_schema.is_managed(db, test_org.id) is False
    assert managed_schema.get_org_schema(db, test_org.id) == {}


def test_get_org_schema_empty_when_not_provisioned(monkeypatch, db, test_org):
    # Storage configured, but this org has no managed destination yet.
    monkeypatch.setattr(settings, "MANAGED_STORAGE_BUCKET", "ul-managed", raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_ACCESS_KEY", "AKIA", raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_SECRET_KEY", "secret", raising=False)
    assert managed_storage.get_managed_destination(db, test_org.id) is None
    assert managed_schema.get_org_schema(db, test_org.id) == {}
