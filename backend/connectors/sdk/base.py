"""
Base Connector SDK.

All connectors must inherit from BaseConnector and implement the required methods.
This provides a standard interface for the platform to interact with any data source.

Example usage:
    from backend.connectors.sdk import BaseConnector, ConnectorMetadata, ConnectorConfig

    class MyConnector(BaseConnector):
        metadata = ConnectorMetadata(
            name="my_source",
            display_name="My Data Source",
            description="Pulls data from My Data Source API",
            icon="my-source",
            category="api",
        )

        def get_config_schema(self) -> dict:
            return {
                "api_key": {"type": "string", "required": True, "secret": True},
                "base_url": {"type": "string", "required": True},
            }

        def test_connection(self) -> bool:
            # Test that credentials work
            return True

        def discover_schema(self) -> list[dict]:
            return [{"name": "users", "columns": [...]}]

        def extract(self, tables=None, incremental_key=None, last_value=None):
            yield {"id": 1, "name": "Alice"}
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Union

import dlt
from dlt.sources import DltResource


class AuthType(str, Enum):
    NONE = "none"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    BEARER = "bearer"
    CUSTOM = "custom"


class PaginationType(str, Enum):
    NONE = "none"
    OFFSET = "offset"
    CURSOR = "cursor"
    PAGE_NUMBER = "page_number"
    LINK_HEADER = "link_header"


@dataclass
class ConnectorCapabilities:
    """Declares what a connector can do."""
    supports_incremental: bool = False
    supports_cdc: bool = False
    supports_schema_discovery: bool = True
    supports_connection_test: bool = True
    supports_parallel_extraction: bool = False
    max_concurrent_tables: int = 1
    auth_types: list = field(default_factory=lambda: [AuthType.NONE])
    pagination_type: PaginationType = PaginationType.NONE


@dataclass
class ConnectorMetadata:
    """Metadata about a connector for display and registration."""
    name: str  # Unique identifier, e.g. "gocardless"
    display_name: str  # Human-readable, e.g. "GoCardless"
    description: str
    icon: str = ""  # Icon name or URL
    category: str = "other"  # database, api, file, payment, accounting, banking
    version: str = "1.0.0"
    author: str = ""
    documentation_url: str = ""
    capabilities: ConnectorCapabilities = field(default_factory=ConnectorCapabilities)
    supported_tables: List[str] = field(default_factory=list)


@dataclass
class ConnectorConfig:
    """Configuration passed to a connector at runtime."""
    credentials: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.credentials.get(key, self.options.get(key, default))

    def require(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            raise ValueError(f"Required config key missing: {key}")
        return val


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.

    To create a new connector:
    1. Subclass BaseConnector
    2. Set the `metadata` class attribute
    3. Implement all abstract methods
    4. Register with @register_connector decorator

    Lifecycle:
        connector = MyConnector(config)
        connector.test_connection()    # Verify credentials
        schema = connector.discover_schema()  # Discover available tables/streams
        for record in connector.extract(tables=["users"]):  # Extract data
            process(record)
        connector.close()  # Cleanup
    """

    metadata: ConnectorMetadata = None  # Must be set by subclass

    def __init__(self, config: Union[ConnectorConfig, Dict[str, Any]]):
        if isinstance(config, dict):
            config = ConnectorConfig(credentials=config)
        self.config = config
        self._validate_metadata()
        self.setup()

    def _validate_metadata(self):
        if not self.metadata:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define a 'metadata' class attribute "
                f"of type ConnectorMetadata."
            )

    def setup(self):
        """Optional hook called after __init__. Override for custom initialization."""
        pass

    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Return the configuration schema for this connector.

        Returns a dict where keys are config field names and values describe the field:
            {
                "api_key": {
                    "type": "string",
                    "required": True,
                    "secret": True,
                    "description": "API key for authentication",
                },
                "environment": {
                    "type": "select",
                    "options": ["sandbox", "production"],
                    "default": "sandbox",
                    "required": True,
                },
            }
        """
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test that the connection credentials are valid.

        Returns True if connection succeeds, raises an exception with
        a descriptive message if it fails.
        """
        ...

    @abstractmethod
    def discover_schema(self) -> List[Dict[str, Any]]:
        """
        Discover available tables/streams and their schemas.

        Returns a list of table descriptors:
            [
                {
                    "name": "payments",
                    "description": "All payments",
                    "columns": [
                        {"name": "id", "type": "string", "primary_key": True},
                        {"name": "amount", "type": "integer"},
                        {"name": "created_at", "type": "datetime"},
                    ],
                    "supports_incremental": True,
                    "incremental_key": "created_at",
                },
            ]
        """
        ...

    @abstractmethod
    def extract(
        self,
        tables: Optional[List[str]] = None,
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Extract data from the source.

        Args:
            tables: List of table/stream names to extract. None = all.
            incremental_key: Column to use for incremental extraction.
            last_value: Last seen value of the incremental key (for resuming).

        Yields:
            Dicts representing individual records.
        """
        ...

    def to_dlt_resource(
        self,
        table_name: str,
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> DltResource:
        """Convert this connector's extract output to a dlt resource."""
        @dlt.resource(name=table_name, write_disposition="merge" if incremental_key else "replace")
        def _resource():
            yield from self.extract(
                tables=[table_name],
                incremental_key=incremental_key,
                last_value=last_value,
            )
        return _resource()

    def close(self):
        """Optional cleanup hook. Override to close connections, pools, etc."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.metadata.name}')>"
