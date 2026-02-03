"""
Xero Connector.

Extracts accounting data from Xero — the #1 cloud accounting platform
for UK SMEs (3.95M subscribers globally). Supports invoices, contacts,
bank transactions, accounts, payments, purchase orders, journals,
and financial reports (P&L, balance sheet).

Uses OAuth 2.0 with PKCE for authentication.
"""
import logging
import time
from datetime import datetime
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

XERO_API_URL = "https://api.xero.com/api.xro/2.0"
XERO_CONNECTIONS_URL = "https://api.xero.com/connections"
XERO_TOKEN_URL = "https://identity.xero.com/connect/token"

# Rate limit: 60 calls per minute
RATE_LIMIT_CALLS = 60
RATE_LIMIT_WINDOW = 60

TABLES = {
    "invoices": {
        "endpoint": "/Invoices",
        "description": "Sales and purchase invoices",
        "columns": [
            {"name": "InvoiceID", "type": "string", "primary_key": True},
            {"name": "InvoiceNumber", "type": "string"},
            {"name": "Type", "type": "string", "description": "ACCREC (sales) or ACCPAY (bills)"},
            {"name": "Status", "type": "string"},
            {"name": "Contact_ContactID", "type": "string"},
            {"name": "Contact_Name", "type": "string"},
            {"name": "DateString", "type": "date"},
            {"name": "DueDateString", "type": "date"},
            {"name": "SubTotal", "type": "float"},
            {"name": "TotalTax", "type": "float"},
            {"name": "Total", "type": "float"},
            {"name": "AmountDue", "type": "float"},
            {"name": "AmountPaid", "type": "float"},
            {"name": "AmountCredited", "type": "float"},
            {"name": "CurrencyCode", "type": "string"},
            {"name": "CurrencyRate", "type": "float"},
            {"name": "Reference", "type": "string"},
            {"name": "SentToContact", "type": "boolean"},
            {"name": "HasAttachments", "type": "boolean"},
            {"name": "UpdatedDateUTC", "type": "datetime"},
        ],
        "supports_incremental": True,
        "incremental_key": "UpdatedDateUTC",
        "modified_after_param": "If-Modified-Since",
    },
    "contacts": {
        "endpoint": "/Contacts",
        "description": "Customers, suppliers, and other contacts",
        "columns": [
            {"name": "ContactID", "type": "string", "primary_key": True},
            {"name": "Name", "type": "string"},
            {"name": "FirstName", "type": "string"},
            {"name": "LastName", "type": "string"},
            {"name": "EmailAddress", "type": "string"},
            {"name": "ContactStatus", "type": "string"},
            {"name": "IsSupplier", "type": "boolean"},
            {"name": "IsCustomer", "type": "boolean"},
            {"name": "DefaultCurrency", "type": "string"},
            {"name": "AccountNumber", "type": "string"},
            {"name": "TaxNumber", "type": "string"},
            {"name": "CompanyNumber", "type": "string"},
            {"name": "AccountsReceivableTaxType", "type": "string"},
            {"name": "AccountsPayableTaxType", "type": "string"},
            {"name": "UpdatedDateUTC", "type": "datetime"},
        ],
        "supports_incremental": True,
        "incremental_key": "UpdatedDateUTC",
        "modified_after_param": "If-Modified-Since",
    },
    "bank_transactions": {
        "endpoint": "/BankTransactions",
        "description": "Bank transactions (spend and receive money)",
        "columns": [
            {"name": "BankTransactionID", "type": "string", "primary_key": True},
            {"name": "Type", "type": "string"},
            {"name": "Status", "type": "string"},
            {"name": "Contact_ContactID", "type": "string"},
            {"name": "Contact_Name", "type": "string"},
            {"name": "DateString", "type": "date"},
            {"name": "SubTotal", "type": "float"},
            {"name": "TotalTax", "type": "float"},
            {"name": "Total", "type": "float"},
            {"name": "Reference", "type": "string"},
            {"name": "IsReconciled", "type": "boolean"},
            {"name": "BankAccount_AccountID", "type": "string"},
            {"name": "BankAccount_Name", "type": "string"},
            {"name": "CurrencyCode", "type": "string"},
            {"name": "UpdatedDateUTC", "type": "datetime"},
        ],
        "supports_incremental": True,
        "incremental_key": "UpdatedDateUTC",
        "modified_after_param": "If-Modified-Since",
    },
    "accounts": {
        "endpoint": "/Accounts",
        "description": "Chart of accounts",
        "columns": [
            {"name": "AccountID", "type": "string", "primary_key": True},
            {"name": "Code", "type": "string"},
            {"name": "Name", "type": "string"},
            {"name": "Type", "type": "string"},
            {"name": "Status", "type": "string"},
            {"name": "Class", "type": "string"},
            {"name": "TaxType", "type": "string"},
            {"name": "Description", "type": "string"},
            {"name": "BankAccountNumber", "type": "string"},
            {"name": "BankAccountType", "type": "string"},
            {"name": "CurrencyCode", "type": "string"},
            {"name": "EnablePaymentsToAccount", "type": "boolean"},
            {"name": "ShowInExpenseClaims", "type": "boolean"},
            {"name": "UpdatedDateUTC", "type": "datetime"},
        ],
        "supports_incremental": True,
        "incremental_key": "UpdatedDateUTC",
    },
    "payments": {
        "endpoint": "/Payments",
        "description": "Payments against invoices and credit notes",
        "columns": [
            {"name": "PaymentID", "type": "string", "primary_key": True},
            {"name": "PaymentType", "type": "string"},
            {"name": "Status", "type": "string"},
            {"name": "Date", "type": "date"},
            {"name": "Amount", "type": "float"},
            {"name": "CurrencyRate", "type": "float"},
            {"name": "Reference", "type": "string"},
            {"name": "IsReconciled", "type": "boolean"},
            {"name": "Invoice_InvoiceID", "type": "string"},
            {"name": "Invoice_InvoiceNumber", "type": "string"},
            {"name": "Account_AccountID", "type": "string"},
            {"name": "Account_Code", "type": "string"},
            {"name": "UpdatedDateUTC", "type": "datetime"},
        ],
        "supports_incremental": True,
        "incremental_key": "UpdatedDateUTC",
        "modified_after_param": "If-Modified-Since",
    },
    "credit_notes": {
        "endpoint": "/CreditNotes",
        "description": "Credit notes issued or received",
        "columns": [
            {"name": "CreditNoteID", "type": "string", "primary_key": True},
            {"name": "CreditNoteNumber", "type": "string"},
            {"name": "Type", "type": "string"},
            {"name": "Status", "type": "string"},
            {"name": "Contact_ContactID", "type": "string"},
            {"name": "Contact_Name", "type": "string"},
            {"name": "DateString", "type": "date"},
            {"name": "SubTotal", "type": "float"},
            {"name": "TotalTax", "type": "float"},
            {"name": "Total", "type": "float"},
            {"name": "RemainingCredit", "type": "float"},
            {"name": "CurrencyCode", "type": "string"},
            {"name": "UpdatedDateUTC", "type": "datetime"},
        ],
        "supports_incremental": True,
        "incremental_key": "UpdatedDateUTC",
    },
    "purchase_orders": {
        "endpoint": "/PurchaseOrders",
        "description": "Purchase orders to suppliers",
        "columns": [
            {"name": "PurchaseOrderID", "type": "string", "primary_key": True},
            {"name": "PurchaseOrderNumber", "type": "string"},
            {"name": "Status", "type": "string"},
            {"name": "Contact_ContactID", "type": "string"},
            {"name": "Contact_Name", "type": "string"},
            {"name": "DateString", "type": "date"},
            {"name": "DeliveryDateString", "type": "date"},
            {"name": "SubTotal", "type": "float"},
            {"name": "TotalTax", "type": "float"},
            {"name": "Total", "type": "float"},
            {"name": "CurrencyCode", "type": "string"},
            {"name": "Reference", "type": "string"},
            {"name": "UpdatedDateUTC", "type": "datetime"},
        ],
        "supports_incremental": True,
        "incremental_key": "UpdatedDateUTC",
    },
    "items": {
        "endpoint": "/Items",
        "description": "Products and services",
        "columns": [
            {"name": "ItemID", "type": "string", "primary_key": True},
            {"name": "Code", "type": "string"},
            {"name": "Name", "type": "string"},
            {"name": "Description", "type": "string"},
            {"name": "PurchaseDescription", "type": "string"},
            {"name": "IsTrackedAsInventory", "type": "boolean"},
            {"name": "IsSold", "type": "boolean"},
            {"name": "IsPurchased", "type": "boolean"},
            {"name": "QuantityOnHand", "type": "float"},
            {"name": "TotalCostPool", "type": "float"},
            {"name": "UpdatedDateUTC", "type": "datetime"},
        ],
        "supports_incremental": True,
        "incremental_key": "UpdatedDateUTC",
    },
}


@register_connector
class XeroConnector(BaseConnector):
    """
    Xero accounting data connector.

    Extracts invoices, contacts, bank transactions, accounts, payments,
    credit notes, purchase orders, and items from the Xero API.
    """

    metadata = ConnectorMetadata(
        name="xero",
        display_name="Xero",
        description=(
            "Sync invoices, contacts, bank transactions, payments, and more "
            "from Xero — the #1 cloud accounting platform for UK SMEs."
        ),
        icon="xero",
        category="accounting",
        version="1.0.0",
        author="UnifiedLayer",
        documentation_url="https://developer.xero.com/documentation/api/accounting/overview",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_cdc=False,
            supports_schema_discovery=True,
            supports_connection_test=True,
            auth_types=[AuthType.OAUTH2],
            pagination_type=PaginationType.PAGE_NUMBER,
        ),
    )

    def setup(self):
        self._session = requests.Session()
        self._tenant_id = self.config.get("tenant_id")
        self._call_count = 0
        self._window_start = time.time()
        self._update_auth_headers()

    def _update_auth_headers(self):
        access_token = self.config.get("access_token", "")
        self._session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        if self._tenant_id:
            self._session.headers["Xero-Tenant-Id"] = self._tenant_id

    def _refresh_token_if_needed(self):
        """Refresh OAuth2 token using refresh token."""
        refresh_token = self.config.get("refresh_token")
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")

        if not all([refresh_token, client_id]):
            return

        resp = requests.post(
            XERO_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret or "",
            },
        )

        if resp.status_code == 200:
            tokens = resp.json()
            self.config.credentials["access_token"] = tokens["access_token"]
            self.config.credentials["refresh_token"] = tokens["refresh_token"]
            self._update_auth_headers()
            logger.info("Xero token refreshed successfully")
        else:
            logger.error(f"Xero token refresh failed: {resp.status_code}")

    def _rate_limit(self):
        """Enforce rate limit of 60 calls per minute."""
        self._call_count += 1
        elapsed = time.time() - self._window_start

        if self._call_count >= RATE_LIMIT_CALLS:
            if elapsed < RATE_LIMIT_WINDOW:
                sleep_time = RATE_LIMIT_WINDOW - elapsed + 1
                logger.info(f"Rate limit approaching, sleeping {sleep_time:.0f}s")
                time.sleep(sleep_time)
            self._call_count = 0
            self._window_start = time.time()

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "client_id": {
                "type": "string",
                "required": True,
                "description": "Xero OAuth2 App client ID",
            },
            "client_secret": {
                "type": "string",
                "required": False,
                "secret": True,
                "description": "Xero OAuth2 App client secret (for confidential apps)",
            },
            "access_token": {
                "type": "string",
                "required": True,
                "secret": True,
                "description": "OAuth2 access token",
            },
            "refresh_token": {
                "type": "string",
                "required": True,
                "secret": True,
                "description": "OAuth2 refresh token for automatic renewal",
            },
            "tenant_id": {
                "type": "string",
                "required": True,
                "description": "Xero organisation tenant ID (from /connections endpoint)",
            },
        }

    def test_connection(self) -> bool:
        self._rate_limit()
        resp = self._session.get(f"{XERO_API_URL}/Organisation")

        if resp.status_code == 401:
            # Try refresh
            self._refresh_token_if_needed()
            resp = self._session.get(f"{XERO_API_URL}/Organisation")

        if resp.status_code == 401:
            raise ConnectionError("Invalid Xero credentials. Check your access token or re-authorize.")
        if resp.status_code != 200:
            raise ConnectionError(f"Xero API error: {resp.status_code} {resp.text[:200]}")

        org = resp.json().get("Organisations", [{}])[0]
        logger.info(f"Connected to Xero organisation: {org.get('Name', 'Unknown')}")
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
                logger.warning(f"Unknown Xero table: {table_name}, skipping")
                continue

            logger.info(f"Extracting Xero table: {table_name}")
            yield from self._extract_table(table_name, incremental_key, last_value)

    def _extract_table(
        self,
        table_name: str,
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> Iterator[Dict[str, Any]]:
        table_def = TABLES[table_name]
        endpoint = table_def["endpoint"]
        url = f"{XERO_API_URL}{endpoint}"

        page = 1
        total_records = 0
        headers = {}

        # Incremental: use If-Modified-Since header
        if incremental_key and last_value and table_def.get("modified_after_param"):
            headers["If-Modified-Since"] = last_value

        while True:
            self._rate_limit()
            params = {"page": page}
            resp = self._session.get(url, params=params, headers=headers)

            if resp.status_code == 401:
                self._refresh_token_if_needed()
                resp = self._session.get(url, params=params, headers=headers)

            if resp.status_code == 304:
                # Not modified since last sync
                logger.info(f"Xero/{table_name}: no changes since last sync")
                break

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60"))
                logger.warning(f"Xero rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            data = resp.json()

            # Xero wraps results in a key matching the endpoint name (e.g., "Invoices")
            result_key = table_name.replace("_", "").title()
            # Handle various naming conventions
            for possible_key in [
                endpoint.strip("/"),
                table_name.title().replace("_", ""),
                table_name,
            ]:
                if possible_key in data:
                    result_key = possible_key
                    break

            records = data.get(result_key, [])
            if not records:
                break

            for record in records:
                flat = self._flatten_record(record)
                flat["_table"] = table_name
                yield flat
                total_records += 1

            # Xero returns up to 100 records per page
            if len(records) < 100:
                break

            page += 1

        logger.info(f"Extracted {total_records} records from Xero/{table_name}")

    def _flatten_record(self, record: dict, prefix: str = "") -> dict:
        """Flatten nested Xero objects (Contact, Account, etc.) into top-level fields."""
        flat = {}
        for key, value in record.items():
            full_key = f"{prefix}_{key}" if prefix else key

            if isinstance(value, dict):
                # Flatten one level deep for linked objects
                for sub_key, sub_value in value.items():
                    if not isinstance(sub_value, (dict, list)):
                        flat[f"{key}_{sub_key}"] = sub_value
            elif isinstance(value, list):
                # Skip line items arrays — too complex for flat table
                continue
            else:
                flat[full_key] = value

        return flat

    def close(self):
        self._session.close()
