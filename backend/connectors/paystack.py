"""
Paystack Connector using dlt framework.

Provides Paystack integration with Bearer token authentication,
incremental loading, retry logic, and rate limiting.
"""
import time
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import dlt
from dlt.sources import DltResource
from dlt.common.typing import TDataItem
import logging

from backend.connectors.sdk.base import (
    BaseConnector,
    ConnectorCapabilities,
    ConnectorMetadata,
    AuthType,
    PaginationType,
)
from backend.connectors.sdk.registry import register_connector

logger = logging.getLogger(__name__)


class PaystackAPIError(Exception):
    """Custom exception for Paystack API errors."""
    pass


class PaystackConnector:
    """
    Production-ready Paystack connector with Bearer token authentication.

    Features:
    - Bearer token auth
    - Pagination via page/perPage params
    - Incremental loading with state management
    - Rate limit handling
    - Comprehensive error handling
    """

    BASE_URL = "https://api.paystack.co"

    MAX_REQUESTS_PER_MINUTE = 100
    RATE_LIMIT_WINDOW = 60

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.request_times: List[float] = []
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session

    def _check_rate_limit(self) -> None:
        current_time = time.time()
        self.request_times = [
            t for t in self.request_times
            if current_time - t < self.RATE_LIMIT_WINDOW
        ]
        if len(self.request_times) >= self.MAX_REQUESTS_PER_MINUTE:
            oldest_request = self.request_times[0]
            sleep_time = self.RATE_LIMIT_WINDOW - (current_time - oldest_request)
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        self.request_times.append(current_time)

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._check_rate_limit()

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.get(
                url, headers=headers, params=params, timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limit exceeded, backing off")
                time.sleep(5)
                return self._make_request(endpoint, params)
            raise PaystackAPIError(f"API request failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise PaystackAPIError(f"Request error: {str(e)}")

    def _paginate(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Iterator[Dict[str, Any]]:
        """Generic paginator for Paystack list endpoints."""
        page = 1
        per_page = 100
        base_params = params or {}

        while True:
            request_params = {**base_params, "page": page, "perPage": per_page}
            response = self._make_request(endpoint, params=request_params)

            data = response.get("data", [])
            if not data:
                break

            for item in data:
                yield item

            meta = response.get("meta", {}).get("pageInfo", {})
            total = meta.get("total", 0)
            if page * per_page >= total:
                break
            page += 1

    def get_transactions(self, start_date: Optional[datetime] = None) -> Iterator[TDataItem]:
        logger.info("Fetching Paystack transactions")
        params = {}
        if start_date:
            params["from"] = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        for item in self._paginate("/transaction", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_customers(self, start_date: Optional[datetime] = None) -> Iterator[TDataItem]:
        logger.info("Fetching Paystack customers")
        params = {}
        if start_date:
            params["from"] = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        for item in self._paginate("/customer", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_transfers(self, start_date: Optional[datetime] = None) -> Iterator[TDataItem]:
        logger.info("Fetching Paystack transfers")
        params = {}
        if start_date:
            params["from"] = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        for item in self._paginate("/transfer", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_settlements(self, start_date: Optional[datetime] = None) -> Iterator[TDataItem]:
        logger.info("Fetching Paystack settlements")
        params = {}
        if start_date:
            params["from"] = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        for item in self._paginate("/settlement", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item


PAYSTACK_TABLES = ["transactions", "customers", "transfers", "settlements"]

TABLE_ENDPOINTS = {
    "transactions": "/transaction",
    "customers": "/customer",
    "transfers": "/transfer",
    "settlements": "/settlement",
}

TABLE_SCHEMAS = {
    "transactions": {"id": "integer", "reference": "string", "amount": "number", "currency": "string", "status": "string", "customer": "object", "created_at": "datetime"},
    "customers": {"id": "integer", "email": "string", "first_name": "string", "last_name": "string", "customer_code": "string", "created_at": "datetime"},
    "transfers": {"id": "integer", "reference": "string", "amount": "number", "currency": "string", "status": "string", "recipient": "object", "created_at": "datetime"},
    "settlements": {"id": "integer", "total_amount": "number", "currency": "string", "status": "string", "settled_date": "datetime", "created_at": "datetime"},
}


@register_connector("paystack")
class PaystackSDKConnector(BaseConnector):
    """Paystack connector using the BaseConnector SDK interface."""

    metadata = ConnectorMetadata(
        name="paystack",
        display_name="Paystack",
        description="Sync transactions, customers, transfers, and settlements from Paystack.",
        icon="paystack",
        category="payment",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_schema_discovery=True,
            auth_types=[AuthType.BEARER],
            pagination_type=PaginationType.PAGE_NUMBER,
        ),
        supported_tables=PAYSTACK_TABLES,
    )

    def setup(self):
        self._connector = PaystackConnector(
            secret_key=self.config.credentials.get("secret_key", "")
        )

    def get_metadata(self) -> ConnectorMetadata:
        return self.metadata

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["secret_key"],
            "properties": {
                "secret_key": {"type": "string", "description": "Paystack Secret Key (sk_...)", "secret": True},
            },
        }

    def test_connection(self) -> Dict[str, Any]:
        try:
            resp = self._connector._make_request("/transaction", {"perPage": 1})
            return {"success": True, "message": f"Connected. Status: {resp.get('status')}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def discover_schema(self) -> Dict[str, Any]:
        return TABLE_SCHEMAS

    def extract(self, table_name: str = "transactions", **kwargs) -> Iterator[Dict[str, Any]]:
        endpoint = TABLE_ENDPOINTS.get(table_name)
        if not endpoint:
            raise ValueError(f"Unknown table: {table_name}. Supported: {PAYSTACK_TABLES}")
        logger.info(f"Extracting Paystack {table_name}")
        yield from self._connector._paginate(endpoint)

    def close(self):
        self._connector.session.close()


@dlt.source(name="paystack")
def paystack_source(
    secret_key: str = dlt.secrets.value,
) -> List[DltResource]:
    """
    dlt source for Paystack data.

    Provides incremental loading for transactions, customers, transfers, and settlements.
    """
    connector = PaystackConnector(secret_key=secret_key)

    @dlt.resource(
        name="transactions",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def transactions(
        last_created_at: dlt.sources.incremental[str] = dlt.sources.incremental(
            "created_at",
            initial_value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        )
    ) -> Iterator[TDataItem]:
        start_date = None
        if last_created_at.last_value:
            try:
                start_date = datetime.fromisoformat(last_created_at.last_value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        yield from connector.get_transactions(start_date=start_date)

    @dlt.resource(
        name="customers",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def customers(
        last_created_at: dlt.sources.incremental[str] = dlt.sources.incremental(
            "created_at",
            initial_value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        )
    ) -> Iterator[TDataItem]:
        start_date = None
        if last_created_at.last_value:
            try:
                start_date = datetime.fromisoformat(last_created_at.last_value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        yield from connector.get_customers(start_date=start_date)

    @dlt.resource(
        name="transfers",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def transfers(
        last_created_at: dlt.sources.incremental[str] = dlt.sources.incremental(
            "created_at",
            initial_value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        )
    ) -> Iterator[TDataItem]:
        start_date = None
        if last_created_at.last_value:
            try:
                start_date = datetime.fromisoformat(last_created_at.last_value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        yield from connector.get_transfers(start_date=start_date)

    @dlt.resource(
        name="settlements",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def settlements(
        last_created_at: dlt.sources.incremental[str] = dlt.sources.incremental(
            "created_at",
            initial_value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        )
    ) -> Iterator[TDataItem]:
        start_date = None
        if last_created_at.last_value:
            try:
                start_date = datetime.fromisoformat(last_created_at.last_value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        yield from connector.get_settlements(start_date=start_date)

    logger.info("Created 4 parallelized resources for Paystack extraction")
    return [transactions, customers, transfers, settlements]
