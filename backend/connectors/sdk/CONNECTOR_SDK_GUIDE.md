# Connector SDK — Developer Guide

Build custom data source connectors for the platform. This SDK provides a standard interface so any data source can be integrated without modifying core platform code.

## Quick Start

```python
from backend.connectors.sdk import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorCapabilities,
    AuthType,
    register_connector,
)

@register_connector
class GoCardlessConnector(BaseConnector):
    metadata = ConnectorMetadata(
        name="gocardless",
        display_name="GoCardless",
        description="Sync Direct Debit payments, mandates, and customers from GoCardless",
        icon="gocardless",
        category="payment",
        version="1.0.0",
        author="Data Platform",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_schema_discovery=True,
            auth_types=[AuthType.BEARER],
        ),
    )

    def get_config_schema(self):
        return {
            "access_token": {
                "type": "string",
                "required": True,
                "secret": True,
                "description": "GoCardless API access token",
            },
            "environment": {
                "type": "select",
                "options": ["sandbox", "live"],
                "default": "sandbox",
                "required": True,
            },
        }

    def test_connection(self):
        import requests
        token = self.config.require("access_token")
        env = self.config.get("environment", "sandbox")
        base = "https://api-sandbox.gocardless.com" if env == "sandbox" else "https://api.gocardless.com"
        resp = requests.get(f"{base}/creditors", headers={
            "Authorization": f"Bearer {token}",
            "GoCardless-Version": "2015-07-06",
        })
        if resp.status_code != 200:
            raise ConnectionError(f"GoCardless auth failed: {resp.status_code}")
        return True

    def discover_schema(self):
        return [
            {
                "name": "payments",
                "description": "Direct Debit payments",
                "columns": [
                    {"name": "id", "type": "string", "primary_key": True},
                    {"name": "amount", "type": "integer"},
                    {"name": "currency", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "charge_date", "type": "date"},
                    {"name": "created_at", "type": "datetime"},
                ],
                "supports_incremental": True,
                "incremental_key": "created_at",
            },
            {
                "name": "mandates",
                "description": "Direct Debit mandates (authorizations)",
                "columns": [
                    {"name": "id", "type": "string", "primary_key": True},
                    {"name": "status", "type": "string"},
                    {"name": "reference", "type": "string"},
                    {"name": "created_at", "type": "datetime"},
                ],
                "supports_incremental": True,
                "incremental_key": "created_at",
            },
            {
                "name": "customers",
                "description": "GoCardless customers",
                "columns": [
                    {"name": "id", "type": "string", "primary_key": True},
                    {"name": "email", "type": "string"},
                    {"name": "given_name", "type": "string"},
                    {"name": "family_name", "type": "string"},
                    {"name": "created_at", "type": "datetime"},
                ],
                "supports_incremental": True,
                "incremental_key": "created_at",
            },
        ]

    def extract(self, tables=None, incremental_key=None, last_value=None):
        import requests
        token = self.config.require("access_token")
        env = self.config.get("environment", "sandbox")
        base = "https://api-sandbox.gocardless.com" if env == "sandbox" else "https://api.gocardless.com"
        headers = {
            "Authorization": f"Bearer {token}",
            "GoCardless-Version": "2015-07-06",
        }

        target_tables = tables or ["payments", "mandates", "customers"]

        for table in target_tables:
            url = f"{base}/{table}"
            params = {"limit": 500}
            if incremental_key and last_value:
                params[f"created_at[gte]"] = last_value

            while url:
                resp = requests.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                for record in data.get(table, []):
                    record["_table"] = table
                    yield record

                # Cursor pagination
                cursors = data.get("meta", {}).get("cursors", {})
                if cursors.get("after"):
                    params["after"] = cursors["after"]
                else:
                    break
```

## BaseConnector Interface

### Required Methods

| Method | Description |
|--------|-------------|
| `get_config_schema()` | Return dict describing required configuration fields |
| `test_connection()` | Verify credentials work. Return True or raise exception |
| `discover_schema()` | Return list of available tables/streams with column info |
| `extract()` | Yield data records as dicts |

### Optional Methods

| Method | Description |
|--------|-------------|
| `setup()` | Called after `__init__`. Initialize clients, pools, etc. |
| `close()` | Cleanup. Close connections, pools, etc. |
| `to_dlt_resource()` | Convert extract output to a dlt resource (built-in) |

### ConnectorMetadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | Yes | Unique identifier (e.g., "gocardless") |
| `display_name` | str | Yes | Human-readable name |
| `description` | str | Yes | What this connector does |
| `category` | str | No | Category: database, api, payment, accounting, banking, file, other |
| `version` | str | No | Semantic version |
| `author` | str | No | Author name |
| `documentation_url` | str | No | Link to docs |
| `capabilities` | ConnectorCapabilities | No | Feature flags |

### Config Schema Field Types

```python
{
    "field_name": {
        "type": "string" | "integer" | "boolean" | "select",
        "required": True | False,
        "secret": True | False,  # Will be encrypted at rest
        "default": "value",
        "description": "Help text",
        "options": ["a", "b"],  # For select type
    }
}
```

## Registration

Use the `@register_connector` decorator:

```python
@register_connector
class MyConnector(BaseConnector):
    ...
```

Or register manually:

```python
from backend.connectors.sdk.registry import ConnectorRegistry
ConnectorRegistry.register(MyConnector)
```

## API Endpoints

Once registered, connectors appear in:
- `GET /connectors/` — List all connectors
- `GET /connectors/{name}` — Get details + config schema
- `GET /connectors/categories` — List categories

## Testing Your Connector

```python
from backend.connectors.sdk import ConnectorRegistry

# Instantiate
connector = ConnectorRegistry.instantiate("gocardless", {
    "access_token": "sandbox_xxx",
    "environment": "sandbox",
})

# Test
assert connector.test_connection() == True

# Discover
schema = connector.discover_schema()
print(schema)

# Extract
for record in connector.extract(tables=["payments"]):
    print(record)

connector.close()
```
