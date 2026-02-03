"""
Connector Registry.

Central registry for all available connectors. Connectors register themselves
using the @register_connector decorator, and the platform queries the registry
to list available connectors, instantiate them, and check capabilities.
"""
import logging
from typing import Dict, List, Optional, Type

from backend.connectors.sdk.base import BaseConnector, ConnectorMetadata

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """Singleton registry of all available connectors."""

    _connectors: Dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, connector_class: Type[BaseConnector]) -> Type[BaseConnector]:
        """Register a connector class."""
        if not connector_class.metadata:
            raise ValueError(
                f"Connector {connector_class.__name__} must define metadata."
            )

        name = connector_class.metadata.name
        if name in cls._connectors:
            logger.warning(f"Connector '{name}' is being re-registered. Overwriting.")

        cls._connectors[name] = connector_class
        logger.info(f"Registered connector: {name} ({connector_class.metadata.display_name})")
        return connector_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseConnector]]:
        """Get a connector class by name."""
        return cls._connectors.get(name)

    @classmethod
    def list_all(cls) -> List[ConnectorMetadata]:
        """List metadata for all registered connectors."""
        return [c.metadata for c in cls._connectors.values()]

    @classmethod
    def list_by_category(cls, category: str) -> List[ConnectorMetadata]:
        """List connectors filtered by category."""
        return [
            c.metadata for c in cls._connectors.values()
            if c.metadata.category == category
        ]

    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all unique connector categories."""
        return list(set(c.metadata.category for c in cls._connectors.values()))

    @classmethod
    def count(cls) -> int:
        """Get total number of registered connectors."""
        return len(cls._connectors)

    @classmethod
    def instantiate(cls, name: str, config: dict) -> BaseConnector:
        """Create an instance of a connector by name."""
        connector_class = cls.get(name)
        if not connector_class:
            available = ", ".join(cls._connectors.keys())
            raise ValueError(
                f"Unknown connector: '{name}'. Available: {available}"
            )
        return connector_class(config)


def register_connector(cls_or_name=None):
    """
    Decorator to register a connector class.

    Usage:
        @register_connector
        class GoCardlessConnector(BaseConnector):
            metadata = ConnectorMetadata(name="gocardless", ...)

        @register_connector("mpesa")
        class MPesaConnector(BaseConnector):
            metadata = ConnectorMetadata(name="mpesa", ...)
    """
    # Called as @register_connector (no args) — cls_or_name is the class
    if isinstance(cls_or_name, type):
        return ConnectorRegistry.register(cls_or_name)

    # Called as @register_connector("name") — cls_or_name is a string, return wrapper
    def wrapper(cls: Type[BaseConnector]) -> Type[BaseConnector]:
        return ConnectorRegistry.register(cls)
    return wrapper
