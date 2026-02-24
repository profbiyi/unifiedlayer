"""
GoCardless Connector.

Extracts Direct Debit payment data from GoCardless — the dominant recurring
payment platform in the UK. Supports payments, mandates, customers, payouts,
refunds, subscriptions, and events.

No other data integration platform (Fivetran, Airbyte, Stitch) offers a
GoCardless connector. Direct Debit powers 80%+ of UK recurring payments.
"""
import logging
from typing import Any, Dict, Iterator, List, Optional

import requests

from backend.connectors.sdk import (
    BaseConnector,
    ConnectorCapabilities,
    ConnectorMetadata,
    AuthType,
    PaginationType,
    register_connector,
)

logger = logging.getLogger(__name__)

SANDBOX_URL = "https://api-sandbox.gocardless.com"
LIVE_URL = "https://api.gocardless.com"
API_VERSION = "2015-07-06"

TABLES = {
    "payments": {
        "description": "Direct Debit payments collected from customers",
        "columns": [
            {"name": "id", "type": "string", "primary_key": True},
            {"name": "amount", "type": "integer", "description": "Amount in pence"},
            {"name": "currency", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "charge_date", "type": "date"},
            {"name": "reference", "type": "string"},
            {"name": "metadata", "type": "json"},
            {"name": "created_at", "type": "datetime"},
            {"name": "links_mandate", "type": "string"},
            {"name": "links_customer", "type": "string"},
            {"name": "links_payout", "type": "string"},
            {"name": "links_subscription", "type": "string"},
        ],
        "supports_incremental": True,
        "incremental_key": "created_at",
    },
    "mandates": {
        "description": "Direct Debit mandates (customer authorizations)",
        "columns": [
            {"name": "id", "type": "string", "primary_key": True},
            {"name": "status", "type": "string"},
            {"name": "reference", "type": "string"},
            {"name": "scheme", "type": "string", "description": "bacs, sepa_core, etc."},
            {"name": "next_possible_charge_date", "type": "date"},
            {"name": "metadata", "type": "json"},
            {"name": "created_at", "type": "datetime"},
            {"name": "links_customer", "type": "string"},
            {"name": "links_customer_bank_account", "type": "string"},
            {"name": "links_creditor", "type": "string"},
        ],
        "supports_incremental": True,
        "incremental_key": "created_at",
    },
    "customers": {
        "description": "GoCardless customers",
        "columns": [
            {"name": "id", "type": "string", "primary_key": True},
            {"name": "email", "type": "string"},
            {"name": "given_name", "type": "string"},
            {"name": "family_name", "type": "string"},
            {"name": "company_name", "type": "string"},
            {"name": "address_line1", "type": "string"},
            {"name": "city", "type": "string"},
            {"name": "postal_code", "type": "string"},
            {"name": "country_code", "type": "string"},
            {"name": "language", "type": "string"},
            {"name": "metadata", "type": "json"},
            {"name": "created_at", "type": "datetime"},
        ],
        "supports_incremental": True,
        "incremental_key": "created_at",
    },
    "payouts": {
        "description": "Payouts from GoCardless to your bank account",
        "columns": [
            {"name": "id", "type": "string", "primary_key": True},
            {"name": "amount", "type": "integer", "description": "Amount in pence"},
            {"name": "currency", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "reference", "type": "string"},
            {"name": "arrival_date", "type": "date"},
            {"name": "deducted_fees", "type": "integer"},
            {"name": "payout_type", "type": "string"},
            {"name": "created_at", "type": "datetime"},
            {"name": "links_creditor", "type": "string"},
            {"name": "links_creditor_bank_account", "type": "string"},
        ],
        "supports_incremental": True,
        "incremental_key": "created_at",
    },
    "refunds": {
        "description": "Refunds issued against payments",
        "columns": [
            {"name": "id", "type": "string", "primary_key": True},
            {"name": "amount", "type": "integer"},
            {"name": "currency", "type": "string"},
            {"name": "reference", "type": "string"},
            {"name": "metadata", "type": "json"},
            {"name": "created_at", "type": "datetime"},
            {"name": "links_payment", "type": "string"},
            {"name": "links_mandate", "type": "string"},
        ],
        "supports_incremental": True,
        "incremental_key": "created_at",
    },
    "subscriptions": {
        "description": "Recurring payment subscriptions",
        "columns": [
            {"name": "id", "type": "string", "primary_key": True},
            {"name": "name", "type": "string"},
            {"name": "amount", "type": "integer"},
            {"name": "currency", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "interval", "type": "integer"},
            {"name": "interval_unit", "type": "string"},
            {"name": "day_of_month", "type": "integer"},
            {"name": "month", "type": "string"},
            {"name": "start_date", "type": "date"},
            {"name": "end_date", "type": "date"},
            {"name": "count", "type": "integer"},
            {"name": "metadata", "type": "json"},
            {"name": "created_at", "type": "datetime"},
            {"name": "links_mandate", "type": "string"},
            {"name": "links_customer", "type": "string"},
        ],
        "supports_incremental": True,
        "incremental_key": "created_at",
    },
    "events": {
        "description": "Webhook events / audit log of all changes",
        "columns": [
            {"name": "id", "type": "string", "primary_key": True},
            {"name": "action", "type": "string"},
            {"name": "resource_type", "type": "string"},
            {"name": "created_at", "type": "datetime"},
            {"name": "details_origin", "type": "string"},
            {"name": "details_cause", "type": "string"},
            {"name": "details_description", "type": "string"},
            {"name": "links_payment", "type": "string"},
            {"name": "links_mandate", "type": "string"},
            {"name": "links_subscription", "type": "string"},
            {"name": "links_refund", "type": "string"},
            {"name": "links_payout", "type": "string"},
        ],
        "supports_incremental": True,
        "incremental_key": "created_at",
    },
}


@register_connector
class GoCardlessConnector(BaseConnector):
    """
    GoCardless Direct Debit connector.

    Extracts payments, mandates, customers, payouts, refunds,
    subscriptions, and events from the GoCardless API.
    """

    metadata = ConnectorMetadata(
        name="gocardless",
        display_name="GoCardless",
        description=(
            "Sync Direct Debit payments, mandates, customers, payouts, and subscriptions "
            "from GoCardless. The dominant recurring payment platform in the UK."
        ),
        icon="gocardless",
        category="payment",
        version="1.0.0",
        author="UnifiedLayer",
        documentation_url="https://developer.gocardless.com/",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_cdc=False,
            supports_schema_discovery=True,
            supports_connection_test=True,
            auth_types=[AuthType.BEARER],
            pagination_type=PaginationType.CURSOR,
        ),
    )

    def setup(self):
        self._session = requests.Session()
        env = self.config.get("environment", "sandbox")
        self._base_url = LIVE_URL if env == "live" else SANDBOX_URL
        token = self.config.get("access_token", "")
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "GoCardless-Version": API_VERSION,
            "Content-Type": "application/json",
        })

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "access_token": {
                "type": "string",
                "required": True,
                "secret": True,
                "description": "GoCardless API access token (from Dashboard > Developers)",
            },
            "environment": {
                "type": "select",
                "options": ["sandbox", "live"],
                "default": "sandbox",
                "required": True,
                "description": "Use 'sandbox' for testing, 'live' for production data",
            },
        }

    def test_connection(self) -> bool:
        resp = self._session.get(f"{self._base_url}/creditors")
        if resp.status_code == 401:
            raise ConnectionError("Invalid GoCardless access token.")
        if resp.status_code != 200:
            raise ConnectionError(f"GoCardless API error: {resp.status_code} {resp.text[:200]}")
        return True

    def discover_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "description": table["description"],
                "columns": table["columns"],
                "supports_incremental": table["supports_incremental"],
                "incremental_key": table.get("incremental_key"),
            }
            for name, table in TABLES.items()
        ]

    def extract(
        self,
        tables: Optional[List[str]] = None,
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> Iterator[Dict[str, Any]]:
        target_tables = tables or list(TABLES.keys())

        for table_name in target_tables:
            if table_name not in TABLES:
                logger.warning(f"Unknown table: {table_name}, skipping")
                continue

            logger.info(f"Extracting GoCardless table: {table_name}")
            yield from self._extract_table(table_name, incremental_key, last_value)

    def _extract_table(
        self,
        table_name: str,
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Extract all records from a GoCardless endpoint with cursor pagination."""
        url = f"{self._base_url}/{table_name}"
        params: Dict[str, Any] = {"limit": 500}

        if incremental_key and last_value and incremental_key == "created_at":
            params["created_at[gte]"] = last_value

        total_records = 0
        cursor = None

        while True:
            if cursor:
                params["after"] = cursor

            resp = self._session.get(url, params=params)

            if resp.status_code == 429:
                import time
                retry_after = int(resp.headers.get("Retry-After", "1"))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            data = resp.json()

            records = data.get(table_name, [])
            if not records:
                break

            for record in records:
                flat = self._flatten_record(record, table_name)
                flat["_table"] = table_name
                yield flat
                total_records += 1

            # Cursor pagination
            meta = data.get("meta", {})
            cursors = meta.get("cursors", {})
            cursor = cursors.get("after")

            if not cursor:
                break

        logger.info(f"Extracted {total_records} records from GoCardless/{table_name}")

    def _flatten_record(self, record: dict, table_name: str) -> dict:
        """Flatten nested links into top-level fields."""
        flat = {}
        for key, value in record.items():
            if key == "links" and isinstance(value, dict):
                for link_key, link_value in value.items():
                    flat[f"links_{link_key}"] = link_value
            elif key == "details" and isinstance(value, dict):
                for detail_key, detail_value in value.items():
                    flat[f"details_{detail_key}"] = detail_value
            else:
                flat[key] = value
        return flat

    def close(self):
        self._session.close()
