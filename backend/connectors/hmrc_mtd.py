"""
HMRC Making Tax Digital (MTD) Connector.

Extracts VAT data from HMRC's Making Tax Digital API — the UK government's
mandatory digital tax filing system. All VAT-registered businesses in the UK
(1.2M+) must file digitally via MTD.

No data integration platform offers an HMRC connector. This is entirely
UK-specific and a strong signal that the business must be based in the UK.

Supports: VAT obligations, VAT returns, VAT liabilities, VAT payments.
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

HMRC_API_URL = "https://api.service.hmrc.gov.uk"
HMRC_SANDBOX_URL = "https://test-api.service.hmrc.gov.uk"
HMRC_TOKEN_URL = "https://api.service.hmrc.gov.uk/oauth/token"
HMRC_SANDBOX_TOKEN_URL = "https://test-api.service.hmrc.gov.uk/oauth/token"

TABLES = {
    "vat_obligations": {
        "description": "VAT return filing obligations (periods you need to file for)",
        "endpoint": "/organisations/vat/{vrn}/obligations",
        "columns": [
            {"name": "period_key", "type": "string", "primary_key": True},
            {"name": "start", "type": "date", "description": "Period start date"},
            {"name": "end", "type": "date", "description": "Period end date"},
            {"name": "due", "type": "date", "description": "Filing deadline"},
            {"name": "status", "type": "string", "description": "O (open) or F (fulfilled)"},
            {"name": "received", "type": "datetime", "description": "When HMRC received the return"},
        ],
        "supports_incremental": False,
    },
    "vat_returns": {
        "description": "Submitted VAT returns with box values (output VAT, input VAT, net VAT)",
        "endpoint": "/organisations/vat/{vrn}/returns/{period_key}",
        "columns": [
            {"name": "period_key", "type": "string", "primary_key": True},
            {"name": "vatDueSales", "type": "float", "description": "Box 1: VAT due on sales"},
            {"name": "vatDueAcquisitions", "type": "float", "description": "Box 2: VAT due on acquisitions"},
            {"name": "totalVatDue", "type": "float", "description": "Box 3: Total VAT due"},
            {"name": "vatReclaimedCurrPeriod", "type": "float", "description": "Box 4: VAT reclaimed"},
            {"name": "netVatDue", "type": "float", "description": "Box 5: Net VAT (owed or refund)"},
            {"name": "totalValueSalesExVAT", "type": "float", "description": "Box 6: Total sales ex VAT"},
            {"name": "totalValuePurchasesExVAT", "type": "float", "description": "Box 7: Total purchases ex VAT"},
            {"name": "totalValueGoodsSuppliedExVAT", "type": "float", "description": "Box 8: Goods supplied to EU ex VAT"},
            {"name": "totalAcquisitionsExVAT", "type": "float", "description": "Box 9: Acquisitions from EU ex VAT"},
        ],
        "supports_incremental": False,
    },
    "vat_liabilities": {
        "description": "Outstanding VAT liabilities (what you owe HMRC)",
        "endpoint": "/organisations/vat/{vrn}/liabilities",
        "columns": [
            {"name": "tax_period_from", "type": "date"},
            {"name": "tax_period_to", "type": "date"},
            {"name": "type", "type": "string", "description": "Liability type"},
            {"name": "original_amount", "type": "float"},
            {"name": "outstanding_amount", "type": "float"},
            {"name": "due", "type": "date"},
        ],
        "supports_incremental": False,
    },
    "vat_payments": {
        "description": "VAT payments made to HMRC",
        "endpoint": "/organisations/vat/{vrn}/payments",
        "columns": [
            {"name": "amount", "type": "float"},
            {"name": "received", "type": "date", "description": "Date HMRC received payment"},
        ],
        "supports_incremental": False,
    },
}


@register_connector
class HMRCMTDConnector(BaseConnector):
    """
    HMRC Making Tax Digital connector.

    Extracts VAT obligations, returns, liabilities, and payments from
    the HMRC MTD API. UK-specific — no other data platform offers this.
    """

    metadata = ConnectorMetadata(
        name="hmrc_mtd",
        display_name="HMRC Making Tax Digital",
        description=(
            "Sync VAT returns, obligations, liabilities, and payments from "
            "HMRC Making Tax Digital. Mandatory for all UK VAT-registered businesses."
        ),
        icon="hmrc",
        category="tax",
        version="1.0.0",
        author="UnifiedLayer",
        documentation_url="https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/vat-api",
        capabilities=ConnectorCapabilities(
            supports_incremental=False,
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
            self._api_url = HMRC_API_URL
            self._token_url = HMRC_TOKEN_URL
        else:
            self._api_url = HMRC_SANDBOX_URL
            self._token_url = HMRC_SANDBOX_TOKEN_URL

        access_token = self.config.get("access_token", "")
        self._vrn = self.config.get("vrn", "")
        self._session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.hmrc.1.0+json",
            "Content-Type": "application/json",
        })
        # HMRC fraud prevention headers (required for production)
        self._session.headers.update(self._get_fraud_prevention_headers())

    def _get_fraud_prevention_headers(self) -> dict:
        """Return HMRC fraud prevention headers (mandatory for production API calls)."""
        return {
            "Gov-Client-Connection-Method": "BATCH_PROCESS_DIRECT",
            "Gov-Vendor-Version": "Data-Platform=1.0.0",
            "Gov-Vendor-Product-Name": "Data-Platform",
        }

    def _refresh_token(self) -> bool:
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")
        refresh_token = self.config.get("refresh_token")

        if not all([client_id, client_secret, refresh_token]):
            return False

        resp = requests.post(
            self._token_url,
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
            self.config.credentials["refresh_token"] = tokens["refresh_token"]
            self._session.headers["Authorization"] = f"Bearer {tokens['access_token']}"
            logger.info("HMRC token refreshed")
            return True

        logger.error(f"HMRC token refresh failed: {resp.status_code}")
        return False

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "vrn": {
                "type": "string",
                "required": True,
                "description": "VAT Registration Number (9 digits)",
            },
            "client_id": {
                "type": "string",
                "required": True,
                "description": "HMRC Developer Hub application client ID",
            },
            "client_secret": {
                "type": "string",
                "required": True,
                "secret": True,
                "description": "HMRC Developer Hub application client secret",
            },
            "access_token": {
                "type": "string",
                "required": True,
                "secret": True,
                "description": "OAuth2 access token (obtained after user grants access)",
            },
            "refresh_token": {
                "type": "string",
                "required": True,
                "secret": True,
                "description": "OAuth2 refresh token for automatic renewal",
            },
            "environment": {
                "type": "select",
                "options": ["sandbox", "live"],
                "default": "sandbox",
                "required": True,
                "description": "Use 'sandbox' for testing with HMRC test data",
            },
            "lookback_months": {
                "type": "integer",
                "default": 24,
                "required": False,
                "description": "How many months of VAT history to fetch (default 24)",
            },
        }

    def test_connection(self) -> bool:
        vrn = self._vrn
        if not vrn:
            raise ConnectionError("VAT Registration Number (VRN) is required.")

        # Test with obligations endpoint
        from_date = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")
        to_date = datetime.utcnow().strftime("%Y-%m-%d")

        url = f"{self._api_url}/organisations/vat/{vrn}/obligations"
        resp = self._session.get(url, params={"from": from_date, "to": to_date})

        if resp.status_code == 401:
            if self._refresh_token():
                resp = self._session.get(url, params={"from": from_date, "to": to_date})

        if resp.status_code == 401:
            raise ConnectionError("Invalid HMRC credentials. Re-authorize via HMRC.")
        if resp.status_code == 403:
            raise ConnectionError(
                "Access denied. The access token may not have the required scope "
                "(read:vat). Re-authorize with the correct permissions."
            )
        if resp.status_code != 200:
            raise ConnectionError(f"HMRC API error: {resp.status_code} {resp.text[:200]}")

        obligations = resp.json().get("obligations", [])
        logger.info(f"Connected to HMRC MTD: VRN {vrn}, {len(obligations)} obligation(s)")
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
        vrn = self._vrn
        lookback = int(self.config.get("lookback_months", 24))

        if not vrn:
            raise ValueError("VAT Registration Number (VRN) is required.")

        for table_name in target_tables:
            if table_name not in TABLES:
                logger.warning(f"Unknown HMRC table: {table_name}, skipping")
                continue

            logger.info(f"Extracting HMRC MTD table: {table_name}")

            if table_name == "vat_obligations":
                yield from self._extract_obligations(vrn, lookback)
            elif table_name == "vat_returns":
                yield from self._extract_returns(vrn, lookback)
            elif table_name == "vat_liabilities":
                yield from self._extract_liabilities(vrn, lookback)
            elif table_name == "vat_payments":
                yield from self._extract_payments(vrn, lookback)

    def _make_request(self, url: str, params: dict = None) -> Optional[dict]:
        """Make an HMRC API request with retry and token refresh."""
        resp = self._session.get(url, params=params)

        if resp.status_code == 401:
            if self._refresh_token():
                resp = self._session.get(url, params=params)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            logger.warning(f"HMRC rate limited, waiting {retry_after}s")
            time.sleep(retry_after)
            resp = self._session.get(url, params=params)

        if resp.status_code == 404:
            return None

        if resp.status_code != 200:
            logger.error(f"HMRC API error: {resp.status_code} {resp.text[:200]}")
            return None

        return resp.json()

    def _extract_obligations(self, vrn: str, lookback_months: int) -> Iterator[Dict[str, Any]]:
        """Extract VAT obligations (filing periods)."""
        # HMRC limits to max 366 days per request, so we chunk
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_months * 30)
        total = 0

        while start_date < end_date:
            chunk_end = min(start_date + timedelta(days=365), end_date)

            url = f"{self._api_url}/organisations/vat/{vrn}/obligations"
            data = self._make_request(url, {
                "from": start_date.strftime("%Y-%m-%d"),
                "to": chunk_end.strftime("%Y-%m-%d"),
            })

            if data:
                for obligation in data.get("obligations", []):
                    obligation["_table"] = "vat_obligations"
                    yield obligation
                    total += 1

            start_date = chunk_end + timedelta(days=1)

        logger.info(f"Extracted {total} VAT obligations")

    def _extract_returns(self, vrn: str, lookback_months: int) -> Iterator[Dict[str, Any]]:
        """Extract submitted VAT returns (must first get obligations to know period keys)."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_months * 30)
        total = 0

        # Get fulfilled obligations to find period keys
        url = f"{self._api_url}/organisations/vat/{vrn}/obligations"
        data = self._make_request(url, {
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
            "status": "F",  # Fulfilled only
        })

        if not data:
            return

        for obligation in data.get("obligations", []):
            period_key = obligation.get("periodKey")
            if not period_key:
                continue

            return_url = f"{self._api_url}/organisations/vat/{vrn}/returns/{period_key}"
            return_data = self._make_request(return_url)

            if return_data:
                return_data["period_key"] = period_key
                return_data["_table"] = "vat_returns"
                yield return_data
                total += 1

        logger.info(f"Extracted {total} VAT returns")

    def _extract_liabilities(self, vrn: str, lookback_months: int) -> Iterator[Dict[str, Any]]:
        """Extract VAT liabilities (amounts owed to HMRC)."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_months * 30)
        total = 0

        url = f"{self._api_url}/organisations/vat/{vrn}/liabilities"
        data = self._make_request(url, {
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
        })

        if data:
            for liability in data.get("liabilities", []):
                # Flatten taxPeriod
                period = liability.pop("taxPeriod", {})
                liability["tax_period_from"] = period.get("from")
                liability["tax_period_to"] = period.get("to")
                liability["original_amount"] = liability.pop("originalAmount", None)
                liability["outstanding_amount"] = liability.pop("outstandingAmount", None)
                liability["_table"] = "vat_liabilities"
                yield liability
                total += 1

        logger.info(f"Extracted {total} VAT liabilities")

    def _extract_payments(self, vrn: str, lookback_months: int) -> Iterator[Dict[str, Any]]:
        """Extract VAT payments made to HMRC."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_months * 30)
        total = 0

        url = f"{self._api_url}/organisations/vat/{vrn}/payments"
        data = self._make_request(url, {
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
        })

        if data:
            for payment in data.get("payments", []):
                payment["_table"] = "vat_payments"
                yield payment
                total += 1

        logger.info(f"Extracted {total} VAT payments")

    def close(self):
        self._session.close()
