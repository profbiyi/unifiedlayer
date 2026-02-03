"""
Flutterwave Connector.

Syncs transactions, payments, transfers, subaccounts, settlements, and refunds
from the Flutterwave API v3.

Docs: https://developer.flutterwave.com/reference
"""
import time
import logging
from typing import Any, Dict, Iterator, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.connectors.sdk.base import (
    BaseConnector,
    ConnectorCapabilities,
    ConnectorMetadata,
    AuthType,
    PaginationType,
)
from backend.connectors.sdk.registry import register_connector

logger = logging.getLogger(__name__)

SUPPORTED_TABLES = [
    "transactions",
    "payments",
    "transfers",
    "subaccounts",
    "settlements",
    "refunds",
]

TABLE_ENDPOINTS = {
    "transactions": "/v3/transactions",
    "payments": "/v3/payments",
    "transfers": "/v3/transfers",
    "subaccounts": "/v3/subaccounts",
    "settlements": "/v3/settlements",
    "refunds": "/v3/refunds",
}

TABLE_SCHEMAS = {
    "transactions": {
        "id": "integer",
        "tx_ref": "string",
        "flw_ref": "string",
        "amount": "number",
        "currency": "string",
        "charged_amount": "number",
        "status": "string",
        "payment_type": "string",
        "customer_email": "string",
        "customer_name": "string",
        "created_at": "datetime",
    },
    "payments": {
        "id": "integer",
        "tx_ref": "string",
        "amount": "number",
        "currency": "string",
        "status": "string",
        "payment_type": "string",
        "created_at": "datetime",
    },
    "transfers": {
        "id": "integer",
        "reference": "string",
        "amount": "number",
        "currency": "string",
        "status": "string",
        "bank_name": "string",
        "account_number": "string",
        "narration": "string",
        "created_at": "datetime",
    },
    "subaccounts": {
        "id": "integer",
        "subaccount_id": "string",
        "account_bank": "string",
        "account_number": "string",
        "business_name": "string",
        "split_type": "string",
        "split_value": "number",
        "created_at": "datetime",
    },
    "settlements": {
        "id": "integer",
        "amount": "number",
        "currency": "string",
        "status": "string",
        "settled_date": "datetime",
        "created_at": "datetime",
    },
    "refunds": {
        "id": "integer",
        "amount_refunded": "number",
        "status": "string",
        "flw_ref": "string",
        "created_at": "datetime",
    },
}


@register_connector("flutterwave")
class FlutterwaveConnector(BaseConnector):
    """Flutterwave API v3 connector."""

    metadata = ConnectorMetadata(
        name="flutterwave",
        display_name="Flutterwave",
        description="Sync payments, transactions, transfers, settlements and more from Flutterwave.",
        icon="flutterwave",
        category="payment",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_schema_discovery=True,
            auth_types=[AuthType.BEARER],
            pagination_type=PaginationType.PAGE_NUMBER,
        ),
        supported_tables=SUPPORTED_TABLES,
    )

    BASE_URL = "https://api.flutterwave.com"
    MAX_REQUESTS_PER_MINUTE = 100
    RATE_LIMIT_WINDOW = 60

    def setup(self):
        self.secret_key = self.config.credentials.get("secret_key", "")
        self.request_times: List[float] = []
        self.session = requests.Session()
        retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _check_rate_limit(self):
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < self.RATE_LIMIT_WINDOW]
        if len(self.request_times) >= self.MAX_REQUESTS_PER_MINUTE:
            sleep_time = self.RATE_LIMIT_WINDOW - (now - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
        self.request_times.append(now)

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        self._check_rate_limit()
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
        resp = self.session.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 429:
            time.sleep(5)
            return self._request(endpoint, params)
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, endpoint: str, params: Optional[Dict] = None) -> Iterator[Dict]:
        page = 1
        per_page = 100
        base_params = params or {}
        while True:
            req_params = {**base_params, "page": page, "per_page": per_page}
            resp = self._request(endpoint, req_params)
            data = resp.get("data", [])
            if not data:
                break
            for item in data:
                yield item
            meta = resp.get("meta", {}).get("page_info", {})
            total_pages = meta.get("total_pages", meta.get("totalPages", 1))
            if page >= total_pages:
                break
            page += 1

    def get_metadata(self) -> ConnectorMetadata:
        return self.metadata

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["secret_key"],
            "properties": {
                "secret_key": {
                    "type": "string",
                    "description": "Flutterwave Secret Key (FLWSECK-...)",
                    "secret": True,
                },
            },
        }

    def test_connection(self) -> Dict[str, Any]:
        try:
            resp = self._request("/v3/transactions", {"per_page": 1})
            return {"success": True, "message": f"Connected. Status: {resp.get('status')}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def discover_schema(self) -> Dict[str, Any]:
        return TABLE_SCHEMAS

    def extract(self, table_name: str = "transactions", **kwargs) -> Iterator[Dict[str, Any]]:
        endpoint = TABLE_ENDPOINTS.get(table_name)
        if not endpoint:
            raise ValueError(f"Unknown table: {table_name}. Supported: {SUPPORTED_TABLES}")
        logger.info(f"Extracting Flutterwave {table_name}")
        yield from self._paginate(endpoint)

    def close(self):
        self.session.close()
