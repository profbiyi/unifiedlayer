"""
Open Banking Connector (via TrueLayer).

Aggregates bank account data from all major UK banks (HSBC, Barclays,
Lloyds, NatWest, Santander, Monzo, Starling, etc.) via a single connector.

This is a novel use of Open Banking — most platforms use it for payments.
We use it as a **data source** for analytics: transaction history, balances,
merchant categorization, and cash flow analysis.

The UK leads the world in Open Banking with 294+ registered TPPs and
6B+ API calls annually.
"""
import logging
import time
from datetime import datetime, timedelta
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

TRUELAYER_AUTH_URL = "https://auth.truelayer.com"
TRUELAYER_API_URL = "https://api.truelayer.com"
TRUELAYER_SANDBOX_AUTH_URL = "https://auth.truelayer-sandbox.com"
TRUELAYER_SANDBOX_API_URL = "https://api.truelayer-sandbox.com"

TABLES = {
    "accounts": {
        "description": "Bank accounts connected via Open Banking",
        "columns": [
            {"name": "account_id", "type": "string", "primary_key": True},
            {"name": "display_name", "type": "string"},
            {"name": "account_type", "type": "string", "description": "TRANSACTION, SAVINGS, BUSINESS"},
            {"name": "currency", "type": "string"},
            {"name": "provider_display_name", "type": "string", "description": "Bank name (e.g., HSBC, Barclays)"},
            {"name": "provider_id", "type": "string"},
            {"name": "account_number_iban", "type": "string"},
            {"name": "account_number_sort_code", "type": "string"},
            {"name": "account_number_number", "type": "string"},
        ],
        "supports_incremental": False,
    },
    "balances": {
        "description": "Current and available balances for each account",
        "columns": [
            {"name": "account_id", "type": "string"},
            {"name": "current", "type": "float", "description": "Current balance"},
            {"name": "available", "type": "float", "description": "Available balance"},
            {"name": "currency", "type": "string"},
            {"name": "overdraft", "type": "float"},
            {"name": "update_timestamp", "type": "datetime"},
            {"name": "retrieved_at", "type": "datetime"},
        ],
        "supports_incremental": False,
    },
    "transactions": {
        "description": "Bank transactions with merchant categorization",
        "columns": [
            {"name": "transaction_id", "type": "string", "primary_key": True},
            {"name": "account_id", "type": "string"},
            {"name": "timestamp", "type": "datetime"},
            {"name": "amount", "type": "float"},
            {"name": "currency", "type": "string"},
            {"name": "transaction_type", "type": "string", "description": "DEBIT or CREDIT"},
            {"name": "transaction_category", "type": "string", "description": "Auto-categorized (e.g., PURCHASE, TRANSFER, SALARY)"},
            {"name": "transaction_classification", "type": "string", "description": "Detailed classification"},
            {"name": "description", "type": "string"},
            {"name": "merchant_name", "type": "string"},
            {"name": "running_balance_amount", "type": "float"},
            {"name": "running_balance_currency", "type": "string"},
            {"name": "meta_provider_transaction_id", "type": "string"},
        ],
        "supports_incremental": True,
        "incremental_key": "timestamp",
    },
    "pending_transactions": {
        "description": "Pending (not yet settled) transactions",
        "columns": [
            {"name": "transaction_id", "type": "string", "primary_key": True},
            {"name": "account_id", "type": "string"},
            {"name": "timestamp", "type": "datetime"},
            {"name": "amount", "type": "float"},
            {"name": "currency", "type": "string"},
            {"name": "transaction_type", "type": "string"},
            {"name": "transaction_category", "type": "string"},
            {"name": "description", "type": "string"},
            {"name": "merchant_name", "type": "string"},
        ],
        "supports_incremental": False,
    },
    "standing_orders": {
        "description": "Standing orders (recurring bank transfers)",
        "columns": [
            {"name": "standing_order_id", "type": "string", "primary_key": True},
            {"name": "account_id", "type": "string"},
            {"name": "frequency", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "first_payment_date", "type": "date"},
            {"name": "next_payment_date", "type": "date"},
            {"name": "final_payment_date", "type": "date"},
            {"name": "first_payment_amount", "type": "float"},
            {"name": "next_payment_amount", "type": "float"},
            {"name": "currency", "type": "string"},
            {"name": "reference", "type": "string"},
            {"name": "payee_name", "type": "string"},
        ],
        "supports_incremental": False,
    },
    "direct_debits": {
        "description": "Direct debit mandates on the account",
        "columns": [
            {"name": "direct_debit_id", "type": "string", "primary_key": True},
            {"name": "account_id", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "name", "type": "string", "description": "Originator name"},
            {"name": "previous_payment_date", "type": "date"},
            {"name": "previous_payment_amount", "type": "float"},
            {"name": "currency", "type": "string"},
            {"name": "mandate_id", "type": "string"},
        ],
        "supports_incremental": False,
    },
}


@register_connector
class OpenBankingConnector(BaseConnector):
    """
    Open Banking connector via TrueLayer.

    Aggregates bank data from all major UK banks into a single data source:
    accounts, balances, transactions (with merchant categorization),
    standing orders, and direct debits.
    """

    metadata = ConnectorMetadata(
        name="open_banking",
        display_name="Open Banking (UK)",
        description=(
            "Aggregate bank account data from all major UK banks — HSBC, Barclays, "
            "Lloyds, NatWest, Santander, Monzo, Starling, and more. Transactions, "
            "balances, standing orders, and direct debits via a single connector."
        ),
        icon="open-banking",
        category="banking",
        version="1.0.0",
        author="UnifiedLayer",
        documentation_url="https://truelayer.com/docs/",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_cdc=False,
            supports_schema_discovery=True,
            supports_connection_test=True,
            auth_types=[AuthType.OAUTH2],
            pagination_type=PaginationType.NONE,
        ),
    )

    def setup(self):
        self._session = requests.Session()
        env = self.config.get("environment", "sandbox")
        if env == "live":
            self._api_url = TRUELAYER_API_URL
            self._auth_url = TRUELAYER_AUTH_URL
        else:
            self._api_url = TRUELAYER_SANDBOX_API_URL
            self._auth_url = TRUELAYER_SANDBOX_AUTH_URL

        access_token = self.config.get("access_token", "")
        self._session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        })

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "client_id": {
                "type": "string",
                "required": True,
                "description": "TrueLayer application client ID",
            },
            "client_secret": {
                "type": "string",
                "required": True,
                "secret": True,
                "description": "TrueLayer application client secret",
            },
            "access_token": {
                "type": "string",
                "required": True,
                "secret": True,
                "description": "OAuth2 access token (obtained after user consent)",
            },
            "refresh_token": {
                "type": "string",
                "required": False,
                "secret": True,
                "description": "OAuth2 refresh token for automatic renewal",
            },
            "environment": {
                "type": "select",
                "options": ["sandbox", "live"],
                "default": "sandbox",
                "required": True,
                "description": "Use 'sandbox' for testing with mock banks",
            },
            "transaction_days": {
                "type": "integer",
                "default": 90,
                "required": False,
                "description": "Number of days of transaction history to fetch (max 90 for most banks)",
            },
        }

    def _refresh_token(self):
        """Refresh the access token using the refresh token."""
        refresh_token = self.config.get("refresh_token")
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")

        if not all([refresh_token, client_id, client_secret]):
            return False

        resp = requests.post(
            f"{self._auth_url}/connect/token",
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            },
        )

        if resp.status_code == 200:
            tokens = resp.json()
            self.config.credentials["access_token"] = tokens["access_token"]
            if "refresh_token" in tokens:
                self.config.credentials["refresh_token"] = tokens["refresh_token"]
            self._session.headers["Authorization"] = f"Bearer {tokens['access_token']}"
            logger.info("TrueLayer token refreshed")
            return True
        return False

    def test_connection(self) -> bool:
        resp = self._session.get(f"{self._api_url}/data/v1/accounts")

        if resp.status_code == 401:
            if self._refresh_token():
                resp = self._session.get(f"{self._api_url}/data/v1/accounts")

        if resp.status_code == 401:
            raise ConnectionError(
                "Invalid Open Banking credentials. The access token may have expired. "
                "Users need to re-authorize via TrueLayer."
            )
        if resp.status_code != 200:
            raise ConnectionError(f"TrueLayer API error: {resp.status_code} {resp.text[:200]}")

        accounts = resp.json().get("results", [])
        logger.info(f"Connected to Open Banking: {len(accounts)} account(s) found")
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

        # First get all accounts (needed for per-account endpoints)
        accounts = self._get_accounts()

        for table_name in target_tables:
            if table_name not in TABLES:
                logger.warning(f"Unknown Open Banking table: {table_name}, skipping")
                continue

            logger.info(f"Extracting Open Banking table: {table_name}")

            if table_name == "accounts":
                for acc in accounts:
                    acc["_table"] = "accounts"
                    yield acc
            elif table_name == "balances":
                yield from self._extract_balances(accounts)
            elif table_name == "transactions":
                yield from self._extract_transactions(accounts, incremental_key, last_value)
            elif table_name == "pending_transactions":
                yield from self._extract_pending_transactions(accounts)
            elif table_name == "standing_orders":
                yield from self._extract_per_account(accounts, "standing_orders", "standing-orders")
            elif table_name == "direct_debits":
                yield from self._extract_per_account(accounts, "direct_debits", "direct-debits")

    def _get_accounts(self) -> List[dict]:
        resp = self._session.get(f"{self._api_url}/data/v1/accounts")
        if resp.status_code == 401:
            self._refresh_token()
            resp = self._session.get(f"{self._api_url}/data/v1/accounts")
        resp.raise_for_status()

        accounts = resp.json().get("results", [])
        # Flatten account number
        for acc in accounts:
            numbers = acc.pop("account_number", {})
            if isinstance(numbers, dict):
                acc["account_number_iban"] = numbers.get("iban")
                acc["account_number_sort_code"] = numbers.get("sort_code")
                acc["account_number_number"] = numbers.get("number")
            provider = acc.pop("provider", {})
            if isinstance(provider, dict):
                acc["provider_display_name"] = provider.get("display_name")
                acc["provider_id"] = provider.get("provider_id")
        return accounts

    def _extract_balances(self, accounts: List[dict]) -> Iterator[Dict[str, Any]]:
        now = datetime.utcnow().isoformat()
        for acc in accounts:
            acc_id = acc["account_id"]
            resp = self._session.get(f"{self._api_url}/data/v1/accounts/{acc_id}/balance")
            if resp.status_code != 200:
                logger.warning(f"Failed to get balance for account {acc_id}: {resp.status_code}")
                continue

            for balance in resp.json().get("results", []):
                balance["account_id"] = acc_id
                balance["retrieved_at"] = now
                balance["_table"] = "balances"
                yield balance

    def _extract_transactions(
        self,
        accounts: List[dict],
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> Iterator[Dict[str, Any]]:
        days = int(self.config.get("transaction_days", 90))
        from_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")

        if incremental_key == "timestamp" and last_value:
            from_date = last_value

        to_date = datetime.utcnow().strftime("%Y-%m-%dT23:59:59Z")

        for acc in accounts:
            acc_id = acc["account_id"]
            url = f"{self._api_url}/data/v1/accounts/{acc_id}/transactions"
            params = {"from": from_date, "to": to_date}

            resp = self._session.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"Failed to get transactions for {acc_id}: {resp.status_code}")
                continue

            for txn in resp.json().get("results", []):
                txn["account_id"] = acc_id
                # Flatten nested fields
                running = txn.pop("running_balance", {})
                if isinstance(running, dict):
                    txn["running_balance_amount"] = running.get("amount")
                    txn["running_balance_currency"] = running.get("currency")
                meta = txn.pop("meta", {})
                if isinstance(meta, dict):
                    txn["meta_provider_transaction_id"] = meta.get("provider_transaction_id")
                # Classification list to string
                classification = txn.pop("transaction_classification", [])
                txn["transaction_classification"] = " > ".join(classification) if classification else None
                txn["_table"] = "transactions"
                yield txn

    def _extract_pending_transactions(self, accounts: List[dict]) -> Iterator[Dict[str, Any]]:
        for acc in accounts:
            acc_id = acc["account_id"]
            url = f"{self._api_url}/data/v1/accounts/{acc_id}/transactions/pending"
            resp = self._session.get(url)
            if resp.status_code != 200:
                continue
            for txn in resp.json().get("results", []):
                txn["account_id"] = acc_id
                txn["_table"] = "pending_transactions"
                yield txn

    def _extract_per_account(
        self, accounts: List[dict], table_name: str, endpoint_suffix: str
    ) -> Iterator[Dict[str, Any]]:
        for acc in accounts:
            acc_id = acc["account_id"]
            url = f"{self._api_url}/data/v1/accounts/{acc_id}/{endpoint_suffix}"
            resp = self._session.get(url)
            if resp.status_code != 200:
                logger.warning(f"Failed to get {table_name} for {acc_id}: {resp.status_code}")
                continue
            for record in resp.json().get("results", []):
                record["account_id"] = acc_id
                record["_table"] = table_name
                yield record

    def close(self):
        self._session.close()
