"""
Tests for the Connector SDK (base class and registry).
"""
from typing import Iterator, Dict, Any, List, Optional

from backend.connectors.sdk.base import BaseConnector, ConnectorMetadata, ConnectorCapabilities
from backend.connectors.sdk.registry import ConnectorRegistry, register_connector


class DummyConnector(BaseConnector):
    """A minimal connector for testing the SDK."""

    metadata = ConnectorMetadata(
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

    def test_connection(self) -> bool:
        return True

    def discover_schema(self) -> List[Dict[str, Any]]:
        return [
            {"name": "items", "columns": {"id": "string", "name": "string"}},
            {"name": "orders", "columns": {"id": "string", "total": "number"}},
        ]

    def extract(
        self,
        tables: Optional[List[str]] = None,
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> Iterator[Dict[str, Any]]:
        target = tables or ["items", "orders"]
        if "items" in target:
            yield {"id": "1", "name": "Widget"}
            yield {"id": "2", "name": "Gadget"}
        if "orders" in target:
            yield {"id": "O1", "total": 99.99}


class TestBaseConnector:
    def test_metadata(self):
        meta = DummyConnector.metadata
        assert meta.name == "dummy"
        assert "items" in meta.supported_tables

    def test_config_schema(self):
        c = DummyConnector({"api_key": "test"})
        schema = c.get_config_schema()
        assert "api_key" in schema["required"]

    def test_test_connection(self):
        c = DummyConnector({"api_key": "test"})
        result = c.test_connection()
        assert result is True

    def test_discover_schema(self):
        c = DummyConnector({"api_key": "test"})
        schema = c.discover_schema()
        names = [t["name"] for t in schema]
        assert "items" in names

    def test_extract(self):
        c = DummyConnector({"api_key": "test"})
        rows = list(c.extract(tables=["items"]))
        assert len(rows) == 2
        assert rows[0]["name"] == "Widget"

    def test_to_dlt_resource(self):
        c = DummyConnector({"api_key": "test"})
        resource = c.to_dlt_resource(table_name="items")
        assert resource is not None

    def test_context_manager(self):
        with DummyConnector({"api_key": "test"}) as c:
            assert c.test_connection() is True


class TestConnectorRegistry:
    def test_register_and_get(self):
        # Register using the class itself (metadata.name = "dummy")
        ConnectorRegistry.register(DummyConnector)
        assert ConnectorRegistry.get("dummy") == DummyConnector

    def test_get_nonexistent(self):
        registry = ConnectorRegistry()
        assert registry.get("nonexistent_xyz_123") is None

    def test_list_all(self):
        ConnectorRegistry.register(DummyConnector)
        all_metadata = ConnectorRegistry.list_all()
        # list_all() returns ConnectorMetadata objects
        names = [m.name for m in all_metadata]
        assert "dummy" in names

    def test_instantiate(self):
        ConnectorRegistry.register(DummyConnector)
        instance = ConnectorRegistry.instantiate("dummy", {"api_key": "test"})
        assert isinstance(instance, DummyConnector)
        assert instance.test_connection() is True

    def test_decorator(self):
        @register_connector
        class DecoratedConnector(BaseConnector):
            metadata = ConnectorMetadata(
                name="decorated_test",
                display_name="Decorated Test",
                description="Decorator test connector",
                category="test",
            )

            def get_config_schema(self) -> Dict[str, Any]:
                return {}

            def test_connection(self) -> bool:
                return True

            def discover_schema(self) -> List[Dict[str, Any]]:
                return []

            def extract(self, tables=None, incremental_key=None, last_value=None):
                return iter([])

        assert ConnectorRegistry.get("decorated_test") == DecoratedConnector
