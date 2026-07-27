"""
Tests for the schema-discovery registry fallback in source_discovery.

The wizard's table-selection step calls /sources/discovery/discover-schema. For
source types without a bespoke async discoverer, it now dispatches to the
registered connector's discover_schema()/metadata. These tests cover the
normalization and dispatch without needing real credentials.
"""
from unittest.mock import MagicMock

import backend.connectors.sdk.registry as reg
from backend.api.routes.source_discovery import (
    _discover_via_connector_registry,
    _tables_from_discover,
)


def test_tables_from_discover_dict_of_columns():
    raw = {
        "customers": {"id": "string", "email": "string"},
        "charges": {"id": "string", "amount": "integer"},
    }
    tables = _tables_from_discover(raw, "stripe")

    names = {t.table for t in tables}
    assert names == {"customers", "charges"}
    customers = next(t for t in tables if t.table == "customers")
    assert customers.schema == "stripe"
    assert {c["name"] for c in customers.columns} == {"id", "email"}


def test_tables_from_discover_list_of_names():
    tables = _tables_from_discover(["customers", "charges"], "stripe")
    assert [t.table for t in tables] == ["customers", "charges"]
    assert all(t.columns == [] for t in tables)


def test_tables_from_discover_list_of_dicts():
    raw = [{"name": "invoices", "columns": [{"name": "id", "type": "string"}]}]
    tables = _tables_from_discover(raw, "stripe")
    assert tables[0].table == "invoices"
    assert tables[0].columns[0]["name"] == "id"


def _patch_registry(monkeypatch, *, found, connector=None):
    monkeypatch.setattr(
        reg.ConnectorRegistry, "get",
        classmethod(lambda cls, name: (object if found else None)),
    )
    if connector is not None:
        monkeypatch.setattr(
            reg.ConnectorRegistry, "instantiate",
            classmethod(lambda cls, name, config: connector),
        )


def test_discover_uses_connector_discover_schema(monkeypatch):
    fake = MagicMock()
    fake.discover_schema.return_value = {"customers": {"id": "string"}}
    _patch_registry(monkeypatch, found=True, connector=fake)

    result = _discover_via_connector_registry("stripe", {"api_key": "sk_test"})

    assert result is not None
    assert [t.table for t in result.tables] == ["customers"]
    fake.close.assert_called_once()


def test_discover_falls_back_to_supported_tables(monkeypatch):
    fake = MagicMock()
    fake.discover_schema.side_effect = RuntimeError("network down")
    fake.metadata.supported_tables = ["customers", "charges"]
    _patch_registry(monkeypatch, found=True, connector=fake)

    result = _discover_via_connector_registry("stripe", {"api_key": "sk_test"})

    assert result is not None
    assert {t.table for t in result.tables} == {"customers", "charges"}


def test_discover_unregistered_type_returns_none(monkeypatch):
    _patch_registry(monkeypatch, found=False)
    assert _discover_via_connector_registry("salesforce", {}) is None
