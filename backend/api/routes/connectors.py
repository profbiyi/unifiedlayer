"""
Connector SDK API routes.

Lists available connectors, their config schemas, and capabilities.
"""
from fastapi import APIRouter, HTTPException
from backend.connectors.sdk.registry import ConnectorRegistry

router = APIRouter(prefix="/connectors", tags=["Connector SDK"])


@router.get("/")
async def list_connectors():
    """List all available connectors with their metadata."""
    connectors = ConnectorRegistry.list_all()
    return {
        "total": len(connectors),
        "connectors": [
            {
                "name": c.name,
                "display_name": c.display_name,
                "description": c.description,
                "icon": c.icon,
                "category": c.category,
                "version": c.version,
                "author": c.author,
                "capabilities": {
                    "incremental": c.capabilities.supports_incremental,
                    "cdc": c.capabilities.supports_cdc,
                    "schema_discovery": c.capabilities.supports_schema_discovery,
                    "connection_test": c.capabilities.supports_connection_test,
                    "auth_types": [a.value for a in c.capabilities.auth_types],
                },
            }
            for c in connectors
        ],
    }


@router.get("/categories")
async def list_categories():
    """List all connector categories."""
    return {"categories": ConnectorRegistry.get_categories()}


@router.get("/{connector_name}")
async def get_connector_details(connector_name: str):
    """Get details and config schema for a specific connector."""
    connector_class = ConnectorRegistry.get(connector_name)
    if not connector_class:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_name}")

    meta = connector_class.metadata

    # Get config schema by instantiating with empty config (catch errors)
    config_schema = {}
    try:
        temp = connector_class.__new__(connector_class)
        temp.config = None
        temp.metadata = meta
        config_schema = temp.get_config_schema()
    except Exception:
        pass

    return {
        "name": meta.name,
        "display_name": meta.display_name,
        "description": meta.description,
        "icon": meta.icon,
        "category": meta.category,
        "version": meta.version,
        "author": meta.author,
        "documentation_url": meta.documentation_url,
        "capabilities": {
            "incremental": meta.capabilities.supports_incremental,
            "cdc": meta.capabilities.supports_cdc,
            "schema_discovery": meta.capabilities.supports_schema_discovery,
            "connection_test": meta.capabilities.supports_connection_test,
            "parallel_extraction": meta.capabilities.supports_parallel_extraction,
            "auth_types": [a.value for a in meta.capabilities.auth_types],
            "pagination": meta.capabilities.pagination_type.value,
        },
        "config_schema": config_schema,
    }
