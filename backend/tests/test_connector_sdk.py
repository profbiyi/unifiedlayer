"""
Tests for the Connector SDK (base class and registry).
"""
from typing import Iterator, Dict, Any

from backend.connectors.sdk.base import BaseConnector, ConnectorMetadata
from backend.connectors.sdk.registry import ConnectorRegistry, register_connector


class DummyConnector(BaseConnector):
    """A minimal connector for testing the SDK."""

    def get_metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="dummy",
            display_name="Dummy Connector",
            description="A test connector",
            category="test",
            supported_tables=["items", "orders"],
        )

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["api_key"],
            "properties": {
                "api_key": {"type": "string"},
            },
        }

    def test_connection(self) -> Dict[str, Any]:
        return {"success": True, "message": "Connected"}

    def discover_schema(self) -> Dict[str, Any]:
        return {
            "items": {"id": "string", "name": "string"},
            "orders": {"id": "string", "total": "number"},
        }

    def extract(self, table_name: str, **kwargs) -> Iterator[Dict[str, Any]]:
        if table_name == "items":
            yield {"id": "1", "name": "Widget"}
            yield {"id": "2", "name": "Gadget"}
        elif table_name == "orders":
            yield {"id": "O1", "total": 99.99}


class TestBaseConnector:
    def test_metadata(self):
        c = DummyConnector({"api_key": "test"})
        meta = c.get_metadata()
        assert meta.name == "dummy"
        assert "items" in meta.supported_tables

    def test_config_schema(self):
        c = DummyConnector({"api_key": "test"})
        schema = c.get_config_schema()
        assert "api_key" in schema["required"]

    def test_test_connection(self):
        c = DummyConnector({"api_key": "test"})
        result = c.test_connection()
        assert result["success"] is True

    def test_discover_schema(self):
        c = DummyConnector({"api_key": "test"})
        schema = c.discover_schema()
        assert "items" in schema

    def test_extract(self):
        c = DummyConnector({"api_key": "test"})
        rows = list(c.extract("items"))
        assert len(rows) == 2
        assert rows[0]["name"] == "Widget"

    def test_to_dlt_resource(self):
        c = DummyConnector({"api_key": "test"})
        resource = c.to_dlt_resource(table_name="items")
        assert resource is not None

    def test_context_manager(self):
        with DummyConnector({"api_key": "test"}) as c:
            assert c.test_connection()["success"] is True


class TestConnectorRegistry:
    def test_register_and_get(self):
        registry = ConnectorRegistry()
        registry.register("dummy", DummyConnector)
        assert registry.get("dummy") == DummyConnector

    def test_get_nonexistent(self):
        registry = ConnectorRegistry()
        assert registry.get("nonexistent") is None

    def test_list_all(self):
        registry = ConnectorRegistry()
        registry.register("dummy", DummyConnector)
        all_connectors = registry.list_all()
        assert "dummy" in all_connectors

    def test_instantiate(self):
        registry = ConnectorRegistry()
        registry.register("dummy", DummyConnector)
        instance = registry.instantiate("dummy", {"api_key": "test"})
        assert isinstance(instance, DummyConnector)
        assert instance.test_connection()["success"] is True

    def test_decorator(self):
        registry = ConnectorRegistry()

        @register_connector("decorated", registry=registry)
        class DecoratedConnector(DummyConnector):
            pass

        assert registry.get("decorated") == DecoratedConnector
