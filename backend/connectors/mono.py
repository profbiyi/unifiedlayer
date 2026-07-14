"""
Mono Connector — African open banking.

Syncs linked bank account details, transactions, and identity data from
the Mono API (https://docs.mono.co). Mono provides read access to bank
accounts across Nigeria (and other African markets) once an account has
been linked via Mono Connect and exchanged for an account id.

Config:
    secret_key   - Mono secret key (sk_...), sent as the mono-sec-key header
    account_ids  - comma-separated Mono account ids to sync (optional; when
                   omitted, all accounts linked to the app are synced)

Docs: https://docs.mono.co/api
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
    "accounts",
    "transactions",
    "identity",
]

TABLE_SCHEMAS = {
    "accounts": {
        "account_id": "string",
        "name": "string",
        "account_number": "string",
        "currency": "string",
        "balance": "number",
        "type": "string",
        "institution_name": "string",
        "institution_bank_code": "string",
        "bvn": "string",
    },
    "transactions": {
        "id": "string",
        "account_id": "string",
        "amount": "number",
        "date": "datetime",
        "narration": "string",
        "type": "string",
        "category": "string",
        "currency": "string",
        "balance": "number",
    },
    "identity": {
        "account_id": "string",
        "full_name": "string",
        "email": "string",
        "phone": "string",
        "bvn": "string",
        "gender": "string",
        "marital_status": "string",
        "address_line1": "string",
    },
}


class MonoAPIError(Exception):
    """Custom exception for Mono API errors."""
    pass


@register_connector("mono")
class MonoConnector(BaseConnector):
    """Mono open banking connector (Nigerian bank accounts)."""

    metadata = ConnectorMetadata(
        name="mono",
        display_name="Mono",
        description="African open banking — sync bank accounts, transactions, and identity data via Mono.",
        icon="mono",
        category="banking",
        documentation_url="https://docs.mono.co/api",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_schema_discovery=True,
            auth_types=[AuthType.API_KEY],
            pagination_type=PaginationType.PAGE_NUMBER,
        ),
        supported_tables=SUPPORTED_TABLES,
    )

    BASE_URL = "https://api.withmono.com"
    MAX_REQUESTS_PER_MINUTE = 60
    RATE_LIMIT_WINDOW = 60

    def setup(self):
        self.secret_key = self.config.credentials.get("secret_key", "")
        raw_ids = self.config.credentials.get("account_ids", "") or ""
        if isinstance(raw_ids, list):
            self.account_ids = [str(a).strip() for a in raw_ids if str(a).strip()]
        else:
            self.account_ids = [a.strip() for a in str(raw_ids).split(",") if a.strip()]
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
                logger.warning(f"Mono rate limit reached, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
        self.request_times.append(now)

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        self._check_rate_limit()
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "mono-sec-key": self.secret_key,
            "Accept": "application/json",
        }
        resp = self.session.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 429:
            time.sleep(5)
            return self._request(endpoint, params)
        if resp.status_code >= 400:
            raise MonoAPIError(f"Mono API error {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    @staticmethod
    def _unwrap(payload: Dict) -> Any:
        """Mono v2 responses wrap results in {status, message, data}; v1 may not."""
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def _resolve_account_ids(self) -> List[str]:
        """Configured account ids, or every account linked to the app."""
        if self.account_ids:
            return self.account_ids
        payload = self._request("/v2/accounts")
        data = self._unwrap(payload) or []
        ids = []
        for item in data if isinstance(data, list) else []:
            account = item.get("account", item) if isinstance(item, dict) else {}
            account_id = account.get("id") or item.get("id")
            if account_id:
                ids.append(account_id)
        return ids

    def _paginate_transactions(self, account_id: str) -> Iterator[Dict]:
        page = 1
        while True:
            payload = self._request(
                f"/v2/accounts/{account_id}/transactions", {"page": page, "paginate": "true"}
            )
            data = self._unwrap(payload) or []
            if not isinstance(data, list) or not data:
                break
            for item in data:
                item["account_id"] = account_id
                yield item
            meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
            total_pages = meta.get("pages") or meta.get("total_pages")
            has_next = meta.get("next")
            if total_pages is not None and page >= int(total_pages):
                break
            if total_pages is None and not has_next:
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
                    "description": "Mono Secret Key (sk_...)",
                    "secret": True,
                },
                "account_ids": {
                    "type": "string",
                    "description": "Comma-separated Mono account IDs to sync (leave empty for all linked accounts)",
                },
            },
        }

    def test_connection(self) -> Dict[str, Any]:
        try:
            if self.account_ids:
                self._request(f"/v2/accounts/{self.account_ids[0]}")
                return {
                    "success": True,
                    "message": f"Connected. Verified access to account {self.account_ids[0]}.",
                }
            payload = self._request("/v2/accounts")
            data = self._unwrap(payload)
            count = len(data) if isinstance(data, list) else 0
            return {"success": True, "message": f"Connected. {count} linked account(s) found."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def discover_schema(self) -> Dict[str, Any]:
        return TABLE_SCHEMAS

    def extract(
        self,
        tables: Optional[List[str]] = None,
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> Iterator[Dict[str, Any]]:
        requested = tables or SUPPORTED_TABLES
        unknown = [t for t in requested if t not in SUPPORTED_TABLES]
        if unknown:
            raise ValueError(f"Unknown table(s): {unknown}. Supported: {SUPPORTED_TABLES}")

        account_ids = self._resolve_account_ids()
        if not account_ids:
            logger.warning("Mono: no linked accounts found to extract from")
            return

        for table in requested:
            logger.info(f"Extracting Mono {table} for {len(account_ids)} account(s)")
            for account_id in account_ids:
                if table == "accounts":
                    payload = self._request(f"/v2/accounts/{account_id}")
                    data = self._unwrap(payload) or {}
                    account = data.get("account", data) if isinstance(data, dict) else {}
                    account["account_id"] = account_id
                    yield account
                elif table == "transactions":
                    yield from self._paginate_transactions(account_id)
                elif table == "identity":
                    payload = self._request(f"/v2/accounts/{account_id}/identity")
                    data = self._unwrap(payload) or {}
                    if isinstance(data, dict):
                        data["account_id"] = account_id
                        yield data

    def close(self):
        self.session.close()
