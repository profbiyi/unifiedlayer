"""
Connector SDK.

Provides base classes and utilities for building data source connectors.
Third-party developers can use this SDK to create custom connectors
that plug into the platform.
"""
from backend.connectors.sdk.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorCapabilities,
    ConnectorMetadata,
    AuthType,
    PaginationType,
)
from backend.connectors.sdk.registry import ConnectorRegistry, register_connector

__all__ = [
    "BaseConnector",
    "ConnectorConfig",
    "ConnectorCapabilities",
    "ConnectorMetadata",
    "AuthType",
    "PaginationType",
    "ConnectorRegistry",
    "register_connector",
]
