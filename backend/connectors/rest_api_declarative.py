"""
Declarative REST API Connector.

Allows customers to connect to ANY REST API by providing a JSON configuration.
Powered by dlt's built-in rest_api source which handles:
- 6 pagination strategies (cursor, offset, page number, JSON link, header link, single page)
- 4 auth methods (bearer token, API key, Basic Auth, OAuth2 client credentials)
- Incremental loading via cursor fields
- Parallel dependent resources (parent-child fetching)
- Automatic schema inference

Configuration example:
    {
        "base_url": "https://api.example.com/v1/",
        "auth": {
            "type": "bearer",
            "token": "sk_live_..."
        },
        "resources": [
            {
                "name": "orders",
                "endpoint": "orders",
                "primary_key": "id",
                "cursor_field": "updated_at",
                "cursor_initial": "2024-01-01",
                "write_mode": "merge"
            },
            {
                "name": "order_items",
                "endpoint": "orders/{parent_id}/items",
                "parent_resource": "orders",
                "parent_key": "id",
                "parallelized": true
            }
        ],
        "pagination": {
            "type": "cursor",
            "cursor_path": "meta.next_cursor",
            "cursor_param": "cursor"
        }
    }
"""
import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class RestApiDeclarativeConnector:
    """
    Connector that builds a dlt rest_api source from a declarative JSON config.

    Customers configure once via the UI, and dlt handles all the
    pagination, auth, incremental state, and schema inference.
    """

    PAGINATION_TYPE_MAP = {
        "cursor": "cursor",
        "offset": "offset",
        "page": "page_number",
        "json_link": "json_link",
        "header_link": "header_link",
        "single": "single_page",
    }

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config["base_url"].rstrip("/") + "/"
        self.auth_config = config.get("auth", {})
        self.resources_config = config.get("resources", [])
        self.pagination_config = config.get("pagination", {})
        self.headers = config.get("headers", {})

    # ------------------------------------------------------------------
    # Auth builders
    # ------------------------------------------------------------------

    def _build_auth(self) -> Optional[Dict]:
        """Convert user-friendly auth config to dlt auth format."""
        auth_type = self.auth_config.get("type")
        if not auth_type or auth_type == "none":
            return None

        if auth_type == "bearer":
            return {"type": "bearer", "token": self.auth_config["token"]}

        if auth_type == "api_key":
            return {
                "type": "api_key",
                "name": self.auth_config.get("header_name", "X-API-Key"),
                "api_key": self.auth_config["api_key"],
                "location": self.auth_config.get("location", "header"),
            }

        if auth_type == "http_basic":
            return {
                "type": "http_basic",
                "username": self.auth_config["username"],
                "password": self.auth_config["password"],
            }

        if auth_type == "oauth2_client_credentials":
            return {
                "type": "oauth2_client_credentials",
                "access_token_url": self.auth_config["token_url"],
                "client_id": self.auth_config["client_id"],
                "client_secret": self.auth_config["client_secret"],
            }

        raise ValueError(f"Unsupported auth type: {auth_type}")

    # ------------------------------------------------------------------
    # Pagination builders
    # ------------------------------------------------------------------

    def _build_pagination(self, resource_pagination: Optional[Dict] = None) -> Optional[Dict]:
        """Convert user-friendly pagination config to dlt pagination format."""
        pg = resource_pagination or self.pagination_config
        if not pg:
            return None

        ptype = self.PAGINATION_TYPE_MAP.get(pg.get("type", ""), pg.get("type"))
        if not ptype:
            return None

        if ptype == "cursor":
            return {
                "type": "cursor",
                "cursor_path": pg["cursor_path"],
                "cursor_param": pg.get("cursor_param", "cursor"),
            }

        if ptype == "offset":
            return {
                "type": "offset",
                "limit": pg.get("limit", 100),
                "offset_param": pg.get("offset_param", "offset"),
                "limit_param": pg.get("limit_param", "limit"),
                "total_path": pg.get("total_path", "total"),
            }

        if ptype == "page_number":
            return {
                "type": "page_number",
                "page_param": pg.get("page_param", "page"),
                "total_path": pg.get("total_path"),
                "base_page": pg.get("base_page", 1),
            }

        if ptype in ("json_link", "header_link"):
            return {
                "type": ptype,
                "next_url_path": pg.get("next_url_path", "links.next"),
            }

        if ptype == "single_page":
            return {"type": "single_page"}

        return None

    # ------------------------------------------------------------------
    # Resource builder
    # ------------------------------------------------------------------

    def _build_resource(self, res: Dict) -> Dict:
        """Convert one user resource config to dlt resource config."""
        dlt_resource: Dict[str, Any] = {
            "name": res["name"],
        }

        endpoint_path = res.get("endpoint", res["name"])

        # Parent-child relationship: replace {parent_id} placeholder with
        # a dlt resolve reference so child records are fetched per parent.
        if res.get("parent_resource") and res.get("parent_key"):
            parent_field = res["parent_key"]
            # dlt rest_api expects a "resolve" dict for path params
            dlt_resource["include_from_parent"] = [parent_field]
            endpoint_config: Dict[str, Any] = {
                "path": endpoint_path,
                "params": {
                    parent_field: {
                        "type": "resolve",
                        "resource": res["parent_resource"],
                        "field": parent_field,
                    }
                },
            }
        else:
            endpoint_config = {"path": endpoint_path}

        # Incremental loading via dlt's built-in incremental support
        if res.get("cursor_field"):
            endpoint_config["incremental"] = {
                "cursor_path": res["cursor_field"],
                "initial_value": res.get("cursor_initial", "2020-01-01"),
            }

        # Resource-level pagination override
        resource_pg = self._build_pagination(res.get("pagination"))
        if resource_pg:
            endpoint_config["paginator"] = resource_pg

        # JSONPath to the array of records inside the response
        if res.get("data_path"):
            endpoint_config["data_selector"] = res["data_path"]

        dlt_resource["endpoint"] = endpoint_config

        if res.get("primary_key"):
            dlt_resource["primary_key"] = res["primary_key"]

        # Write disposition
        write_mode = res.get("write_mode", "append")
        if write_mode == "merge" and res.get("primary_key"):
            dlt_resource["write_disposition"] = "merge"
        elif write_mode in ("replace", "full_refresh"):
            dlt_resource["write_disposition"] = "replace"
        else:
            dlt_resource["write_disposition"] = "append"

        # Parallelism for child resources (supported in dlt >= 1.22.0)
        if res.get("parallelized") and res.get("parent_resource"):
            dlt_resource["parallelized"] = True

        return dlt_resource

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_dlt_source(self):
        """Build and return the dlt rest_api source."""
        from dlt.sources.rest_api import rest_api_source

        config: Dict[str, Any] = {
            "client": {
                "base_url": self.base_url,
            },
            "resources": [self._build_resource(r) for r in self.resources_config],
        }

        # Global auth
        auth = self._build_auth()
        if auth:
            config["client"]["auth"] = auth

        # Custom headers
        if self.headers:
            config["client"]["headers"] = self.headers

        # Global pagination default
        pagination = self._build_pagination()
        if pagination:
            config["client"]["paginator"] = pagination

        logger.info(
            "RestApiDeclarativeConnector: building source for %s with %d resource(s)",
            self.base_url, len(self.resources_config),
        )

        return rest_api_source(config)

    def test_connection(self) -> Dict[str, Any]:
        """Test that the base URL is reachable with the configured auth."""
        try:
            headers = dict(self.headers)
            auth_config = self._build_auth()

            if auth_config and auth_config["type"] == "bearer":
                headers["Authorization"] = f"Bearer {auth_config['token']}"
            elif auth_config and auth_config["type"] == "api_key":
                if auth_config.get("location", "header") == "header":
                    headers[auth_config["name"]] = auth_config["api_key"]

            resp = requests.get(self.base_url, headers=headers, timeout=10)
            return {
                "success": resp.status_code < 400,
                "status_code": resp.status_code,
                "base_url": self.base_url,
                "resources": [r["name"] for r in self.resources_config],
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Connection refused or DNS failure: {e}",
                "base_url": self.base_url,
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timed out after 10 seconds",
                "base_url": self.base_url,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "base_url": self.base_url}

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for the source wizard UI."""
        return {
            "type": "object",
            "required": ["base_url", "resources"],
            "properties": {
                "base_url": {
                    "type": "string",
                    "title": "Base URL",
                    "description": "Root URL for the API, e.g. https://api.example.com/v1/",
                    "placeholder": "https://api.example.com/v1/",
                },
                "auth": {
                    "type": "object",
                    "title": "Authentication",
                    "properties": {
                        "type": {
                            "type": "string",
                            "title": "Auth Type",
                            "enum": [
                                "none",
                                "bearer",
                                "api_key",
                                "http_basic",
                                "oauth2_client_credentials",
                            ],
                            "default": "none",
                        },
                        "token": {
                            "type": "string",
                            "title": "Bearer Token",
                            "description": "Used when type is 'bearer'",
                        },
                        "api_key": {
                            "type": "string",
                            "title": "API Key",
                            "description": "Used when type is 'api_key'",
                        },
                        "header_name": {
                            "type": "string",
                            "title": "API Key Header Name",
                            "default": "X-API-Key",
                        },
                        "username": {
                            "type": "string",
                            "title": "Username",
                            "description": "Used when type is 'http_basic'",
                        },
                        "password": {
                            "type": "string",
                            "title": "Password",
                            "description": "Used when type is 'http_basic'",
                        },
                        "token_url": {
                            "type": "string",
                            "title": "Token URL",
                            "description": "Used when type is 'oauth2_client_credentials'",
                        },
                        "client_id": {
                            "type": "string",
                            "title": "Client ID",
                            "description": "Used when type is 'oauth2_client_credentials'",
                        },
                        "client_secret": {
                            "type": "string",
                            "title": "Client Secret",
                            "description": "Used when type is 'oauth2_client_credentials'",
                        },
                    },
                },
                "pagination": {
                    "type": "object",
                    "title": "Global Pagination (applies to all resources unless overridden)",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "cursor",
                                "offset",
                                "page",
                                "json_link",
                                "header_link",
                                "single",
                            ],
                        },
                        "cursor_path": {
                            "type": "string",
                            "title": "Cursor JSONPath",
                            "description": "JSONPath to the next cursor value in the response",
                            "placeholder": "meta.next_cursor",
                        },
                        "cursor_param": {
                            "type": "string",
                            "title": "Cursor Query Param Name",
                            "default": "cursor",
                        },
                        "limit": {
                            "type": "integer",
                            "title": "Page Size",
                            "default": 100,
                        },
                        "next_url_path": {
                            "type": "string",
                            "title": "Next URL JSONPath",
                            "description": "JSONPath to the next page URL (for json_link)",
                            "default": "links.next",
                        },
                    },
                },
                "resources": {
                    "type": "array",
                    "title": "API Endpoints to Sync",
                    "items": {
                        "type": "object",
                        "required": ["name", "endpoint"],
                        "properties": {
                            "name": {
                                "type": "string",
                                "title": "Table Name",
                                "description": "Destination table name in your data warehouse",
                            },
                            "endpoint": {
                                "type": "string",
                                "title": "Endpoint Path",
                                "description": "Relative path from base URL, e.g. 'orders' or 'users/{id}/posts'",
                            },
                            "primary_key": {
                                "type": "string",
                                "title": "Primary Key Field",
                            },
                            "cursor_field": {
                                "type": "string",
                                "title": "Incremental Cursor Field",
                                "description": "Field name to use for incremental loading (e.g. updated_at)",
                            },
                            "cursor_initial": {
                                "type": "string",
                                "title": "Initial Cursor Value",
                                "description": "Start loading from this value on first sync",
                                "default": "2020-01-01",
                            },
                            "write_mode": {
                                "type": "string",
                                "title": "Write Mode",
                                "enum": ["append", "merge", "replace"],
                                "default": "append",
                            },
                            "data_path": {
                                "type": "string",
                                "title": "Response Data JSONPath",
                                "description": "JSONPath to the array of records in the response, e.g. 'data' or 'results'",
                            },
                            "parent_resource": {
                                "type": "string",
                                "title": "Parent Resource Name",
                                "description": "Name of the parent resource for nested endpoints",
                            },
                            "parent_key": {
                                "type": "string",
                                "title": "Parent Key Field",
                                "description": "Field in the parent used to build the child URL",
                            },
                            "parallelized": {
                                "type": "boolean",
                                "title": "Parallel Fetch (for child resources)",
                                "description": "Fetch child records in parallel per parent (requires dlt >= 1.22.0)",
                                "default": False,
                            },
                        },
                    },
                },
                "headers": {
                    "type": "object",
                    "title": "Custom Request Headers",
                    "description": "Additional HTTP headers sent with every request",
                    "additionalProperties": {"type": "string"},
                },
            },
        }


def create_rest_api_source(config: Dict[str, Any]):
    """
    Factory function called by pipeline_flow.py for source_type='rest_api_declarative'.

    Returns a dlt source ready for pipeline.run().
    """
    connector = RestApiDeclarativeConnector(config)
    return connector.get_dlt_source()
