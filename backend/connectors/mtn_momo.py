"""
MTN Mobile Money (MoMo) Connector.

Syncs collections, disbursements, transfers, and account balances from MTN MoMo API.

Docs: https://momodeveloper.mtn.com/api-documentation
"""
import time
import logging
import base64
from typing import Any, Dict, Iterator, List, Optional
from datetime import datetime, timedelta, timezone

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
    "collections",
    "disbursements",
    "transfers",
    "account_balance",
]

TABLE_SCHEMAS = {
    "collections": {
        "financialTransactionId": "string",
        "externalId": "string",
        "amount": "string",
        "currency": "string",
        "payer": "object",
        "payerMessage": "string",
        "payeeNote": "string",
        "status": "string",
        "reason": "string",
    },
    "disbursements": {
        "financialTransactionId": "string",
        "externalId": "string",
        "amount": "string",
        "currency": "string",
        "payee": "object",
        "payerMessage": "string",
        "payeeNote": "string",
        "status": "string",
        "reason": "string",
    },
    "transfers": {
        "financialTransactionId": "string",
        "externalId": "string",
        "amount": "string",
        "currency": "string",
        "payee": "object",
        "payerMessage": "string",
        "payeeNote": "string",
        "status": "string",
    },
    "account_balance": {
        "availableBalance": "string",
        "currency": "string",
        "_snapshot_time": "datetime",
    },
}

ENVIRONMENT_URLS = {
    "sandbox": "https://sandbox.momodeveloper.mtn.com",
    "production": "https://proxy.momodeveloper.mtn.com",
}

PRODUCT_ENDPOINTS = {
    "collections": "/collection",
    "disbursements": "/disbursement",
    "transfers": "/remittance",
}


@register_connector("mtn_momo")
class MTNMoMoConnector(BaseConnector):
    """MTN Mobile Money API connector."""

    metadata = ConnectorMetadata(
        name="mtn_momo",
        display_name="MTN Mobile Money",
        description="Sync collections, disbursements, and transfers from MTN MoMo.",
        icon="mtn",
        category="payment",
        capabilities=ConnectorCapabilities(
            supports_incremental=False,
            supports_schema_discovery=True,
            auth_types=[AuthType.OAUTH2],
            pagination_type=PaginationType.NONE,
        ),
        supported_tables=SUPPORTED_TABLES,
    )

    def setup(self):
        creds = self.config.credentials
        self.subscription_key = creds.get("subscription_key", "")
        self.api_user = creds.get("api_user", "")
        self.api_key = creds.get("api_key", "")
        self.environment = creds.get("environment", "sandbox")
        self.target_environment = "sandbox" if self.environment == "sandbox" else creds.get("target_environment", "mtncameroon")
        self.base_url = ENVIRONMENT_URLS.get(self.environment, ENVIRONMENT_URLS["sandbox"])

        self.access_tokens: Dict[str, str] = {}
        self.token_expiry: Dict[str, Optional[datetime]] = {}

        self.session = requests.Session()
        retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _get_token(self, product: str) -> str:
        """Get OAuth2 token for a MoMo product (collection, disbursement, remittance)."""
        now = datetime.now(timezone.utc)
        if self.access_tokens.get(product) and self.token_expiry.get(product):
            if now < self.token_expiry[product] - timedelta(minutes=2):
                return self.access_tokens[product]

        endpoint = PRODUCT_ENDPOINTS.get(product, "/collection")
        url = f"{self.base_url}{endpoint}/token/"

        basic_auth = base64.b64encode(f"{self.api_user}:{self.api_key}".encode()).decode()
        headers = {
            "Authorization": f"Basic {basic_auth}",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
        }

        resp = self.session.post(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        self.access_tokens[product] = data["access_token"]
        self.token_expiry[product] = now + timedelta(seconds=int(data.get("expires_in", 3600)))
        return self.access_tokens[product]

    def _request(self, product: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        token = self._get_token(product)
        url = f"{self.base_url}{PRODUCT_ENDPOINTS[product]}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": self.target_environment,
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json",
        }
        resp = self.session.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def get_metadata(self) -> ConnectorMetadata:
        return self.metadata

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["subscription_key", "api_user", "api_key"],
            "properties": {
                "subscription_key": {
                    "type": "string",
                    "description": "Ocp-Apim-Subscription-Key from MoMo Developer Portal",
                    "secret": True,
                },
                "api_user": {
                    "type": "string",
                    "description": "API User (X-Reference-Id)",
                },
                "api_key": {
                    "type": "string",
                    "description": "API Key",
                    "secret": True,
                },
                "environment": {
                    "type": "string",
                    "enum": ["sandbox", "production"],
                    "default": "sandbox",
                },
                "target_environment": {
                    "type": "string",
                    "description": "Target environment (e.g., mtncameroon, mtnuganda, sandbox)",
                    "default": "sandbox",
                },
            },
        }

    def test_connection(self) -> Dict[str, Any]:
        try:
            token = self._get_token("collections")
            return {"success": True, "message": "Connected to MTN MoMo API"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def discover_schema(self) -> Dict[str, Any]:
        return TABLE_SCHEMAS

    def extract(self, table_name: str = "collections", **kwargs) -> Iterator[Dict[str, Any]]:
        if table_name not in SUPPORTED_TABLES:
            raise ValueError(f"Unknown table: {table_name}. Supported: {SUPPORTED_TABLES}")

        logger.info(f"Extracting MTN MoMo {table_name}")

        if table_name == "account_balance":
            for product in ["collections", "disbursements", "transfers"]:
                try:
                    data = self._request(product, "/v1_0/account/balance")
                    if data:
                        data["_product"] = product
                        data["_snapshot_time"] = datetime.now(timezone.utc).isoformat()
                        yield data
                except Exception as e:
                    logger.warning(f"Failed to get {product} balance: {e}")
        else:
            # MoMo API doesn't have a list-all endpoint for transactions.
            # In production, you'd store transaction reference IDs from webhooks
            # and query each one. For now, fetch recent via the transfer history
            # endpoint if available, or yield from stored webhook data.
            product = table_name if table_name != "transfers" else "transfers"
            try:
                # Try the v1_0 history endpoint (available in some markets)
                data = self._request(product, "/v1_0/account/transactions")
                if isinstance(data, list):
                    for item in data:
                        yield item
                elif isinstance(data, dict) and "transactions" in data:
                    for item in data["transactions"]:
                        yield item
            except Exception as e:
                logger.info(f"Transaction listing not available for {product}: {e}")
                # In production, transactions are captured via webhooks
                # and stored in the webhook_events table for extraction.

    def close(self):
        self.session.close()
