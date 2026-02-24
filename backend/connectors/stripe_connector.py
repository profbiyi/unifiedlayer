"""
Stripe Connector using dlt framework.

Provides Stripe integration with API key authentication,
incremental loading, retry logic, and rate limiting.

Supports: charges, customers, invoices, subscriptions, payouts, balance_transactions
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


class StripeAPIError(Exception):
    """Custom exception for Stripe API errors."""
    pass


class StripeConnector:
    """
    Production-ready Stripe connector with Bearer token authentication.

    Features:
    - Bearer token auth (API key)
    - Cursor-based pagination (starting_after)
    - Incremental loading with state management
    - Rate limit handling (Stripe allows 100 requests/sec in live mode)
    - Comprehensive error handling with retries
    """

    BASE_URL = "https://api.stripe.com/v1"

    # Stripe rate limits: 100 req/sec in live mode, 25 req/sec in test mode
    MAX_REQUESTS_PER_SECOND = 25  # Conservative for test mode compatibility
    RATE_LIMIT_WINDOW = 1

    def __init__(self, api_key: str):
        """
        Initialize Stripe connector.

        Args:
            api_key: Stripe API key (sk_live_... or sk_test_...)
        """
        self.api_key = api_key
        self.request_times: List[float] = []
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session

    def _check_rate_limit(self) -> None:
        """Implement rate limiting to avoid hitting Stripe's limits."""
        current_time = time.time()
        # Remove requests older than the rate limit window
        self.request_times = [
            t for t in self.request_times
            if current_time - t < self.RATE_LIMIT_WINDOW
        ]

        if len(self.request_times) >= self.MAX_REQUESTS_PER_SECOND:
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
        """
        Make authenticated request to Stripe API.

        Args:
            endpoint: API endpoint (e.g., "/charges")
            params: Query parameters

        Returns:
            JSON response
        """
        self._check_rate_limit()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Stripe-Version": "2023-10-16",  # Pin API version for stability
        }
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.get(
                url, headers=headers, params=params, timeout=30,
            )

            # Handle rate limiting with Retry-After header
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning(f"Rate limit exceeded, waiting {retry_after} seconds")
                time.sleep(retry_after)
                return self._make_request(endpoint, params)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            error_body = {}
            try:
                error_body = e.response.json()
            except Exception:
                pass

            error_msg = error_body.get("error", {}).get("message", str(e))
            raise StripeAPIError(f"Stripe API error: {error_msg}")

        except requests.exceptions.RequestException as e:
            raise StripeAPIError(f"Request error: {str(e)}")

    def _paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> Iterator[Dict[str, Any]]:
        """
        Generic paginator for Stripe list endpoints using cursor pagination.

        Stripe uses cursor-based pagination with 'starting_after' parameter.
        """
        base_params = params or {}
        base_params["limit"] = limit

        while True:
            response = self._make_request(endpoint, params=base_params)

            data = response.get("data", [])
            if not data:
                break

            for item in data:
                yield item

            # Check if there are more results
            if not response.get("has_more", False):
                break

            # Use last item's ID as cursor for next page
            last_id = data[-1].get("id")
            if last_id:
                base_params["starting_after"] = last_id
            else:
                break

    def get_charges(self, created_after: Optional[int] = None) -> Iterator[TDataItem]:
        """Fetch charges (payments) from Stripe."""
        logger.info("Fetching Stripe charges")
        params = {}
        if created_after:
            params["created[gte]"] = created_after

        for item in self._paginate("/charges", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_customers(self, created_after: Optional[int] = None) -> Iterator[TDataItem]:
        """Fetch customers from Stripe."""
        logger.info("Fetching Stripe customers")
        params = {}
        if created_after:
            params["created[gte]"] = created_after

        for item in self._paginate("/customers", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_invoices(self, created_after: Optional[int] = None) -> Iterator[TDataItem]:
        """Fetch invoices from Stripe."""
        logger.info("Fetching Stripe invoices")
        params = {}
        if created_after:
            params["created[gte]"] = created_after

        for item in self._paginate("/invoices", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_subscriptions(self, created_after: Optional[int] = None) -> Iterator[TDataItem]:
        """Fetch subscriptions from Stripe."""
        logger.info("Fetching Stripe subscriptions")
        params = {}
        if created_after:
            params["created[gte]"] = created_after

        for item in self._paginate("/subscriptions", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_payouts(self, created_after: Optional[int] = None) -> Iterator[TDataItem]:
        """Fetch payouts from Stripe."""
        logger.info("Fetching Stripe payouts")
        params = {}
        if created_after:
            params["created[gte]"] = created_after

        for item in self._paginate("/payouts", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_balance_transactions(self, created_after: Optional[int] = None) -> Iterator[TDataItem]:
        """Fetch balance transactions from Stripe."""
        logger.info("Fetching Stripe balance transactions")
        params = {}
        if created_after:
            params["created[gte]"] = created_after

        for item in self._paginate("/balance_transactions", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_payment_intents(self, created_after: Optional[int] = None) -> Iterator[TDataItem]:
        """Fetch payment intents from Stripe."""
        logger.info("Fetching Stripe payment intents")
        params = {}
        if created_after:
            params["created[gte]"] = created_after

        for item in self._paginate("/payment_intents", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def get_refunds(self, created_after: Optional[int] = None) -> Iterator[TDataItem]:
        """Fetch refunds from Stripe."""
        logger.info("Fetching Stripe refunds")
        params = {}
        if created_after:
            params["created[gte]"] = created_after

        for item in self._paginate("/refunds", params):
            item["_dlt_load_time"] = datetime.now().isoformat()
            yield item

    def close(self):
        """Close the session."""
        self.session.close()


# Supported tables and their endpoints
STRIPE_TABLES = [
    "charges",
    "customers",
    "invoices",
    "subscriptions",
    "payouts",
    "balance_transactions",
    "payment_intents",
    "refunds",
]

TABLE_ENDPOINTS = {
    "charges": "/charges",
    "customers": "/customers",
    "invoices": "/invoices",
    "subscriptions": "/subscriptions",
    "payouts": "/payouts",
    "balance_transactions": "/balance_transactions",
    "payment_intents": "/payment_intents",
    "refunds": "/refunds",
}

TABLE_SCHEMAS = {
    "charges": {
        "id": "string",
        "amount": "integer",
        "currency": "string",
        "status": "string",
        "customer": "string",
        "description": "string",
        "created": "integer",
        "paid": "boolean",
        "refunded": "boolean",
    },
    "customers": {
        "id": "string",
        "email": "string",
        "name": "string",
        "phone": "string",
        "created": "integer",
        "currency": "string",
        "default_source": "string",
    },
    "invoices": {
        "id": "string",
        "customer": "string",
        "status": "string",
        "total": "integer",
        "currency": "string",
        "created": "integer",
        "due_date": "integer",
        "paid": "boolean",
    },
    "subscriptions": {
        "id": "string",
        "customer": "string",
        "status": "string",
        "current_period_start": "integer",
        "current_period_end": "integer",
        "created": "integer",
        "canceled_at": "integer",
    },
    "payouts": {
        "id": "string",
        "amount": "integer",
        "currency": "string",
        "status": "string",
        "arrival_date": "integer",
        "created": "integer",
    },
    "balance_transactions": {
        "id": "string",
        "amount": "integer",
        "currency": "string",
        "type": "string",
        "status": "string",
        "created": "integer",
        "available_on": "integer",
    },
    "payment_intents": {
        "id": "string",
        "amount": "integer",
        "currency": "string",
        "status": "string",
        "customer": "string",
        "created": "integer",
    },
    "refunds": {
        "id": "string",
        "amount": "integer",
        "currency": "string",
        "status": "string",
        "charge": "string",
        "created": "integer",
    },
}


@register_connector("stripe")
class StripeSDKConnector(BaseConnector):
    """Stripe connector using the BaseConnector SDK interface."""

    metadata = ConnectorMetadata(
        name="stripe",
        display_name="Stripe",
        description="Sync charges, customers, invoices, subscriptions, and payouts from Stripe.",
        icon="stripe",
        category="payment",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_schema_discovery=True,
            auth_types=[AuthType.BEARER],
            pagination_type=PaginationType.CURSOR,
        ),
        supported_tables=STRIPE_TABLES,
    )

    def setup(self):
        """Initialize the Stripe connector."""
        self._connector = StripeConnector(
            api_key=self.config.credentials.get("api_key", "")
        )

    def get_metadata(self) -> ConnectorMetadata:
        return self.metadata

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["api_key"],
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "Stripe API Key (sk_live_... or sk_test_...)",
                    "secret": True,
                },
            },
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection by fetching account balance."""
        try:
            # Fetch balance to verify API key works
            response = self._connector._make_request("/balance")
            available = response.get("available", [])
            currency = available[0].get("currency", "unknown") if available else "unknown"
            return {
                "success": True,
                "message": f"Connected to Stripe. Account currency: {currency.upper()}",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def discover_schema(self) -> Dict[str, Any]:
        return TABLE_SCHEMAS

    def extract(self, table_name: str = "charges", **kwargs) -> Iterator[Dict[str, Any]]:
        """Extract data from specified table."""
        endpoint = TABLE_ENDPOINTS.get(table_name)
        if not endpoint:
            raise ValueError(f"Unknown table: {table_name}. Supported: {STRIPE_TABLES}")

        logger.info(f"Extracting Stripe {table_name}")
        yield from self._connector._paginate(endpoint)

    def close(self):
        """Clean up resources."""
        self._connector.close()


@dlt.source(name="stripe")
def stripe_source(
    api_key: str = dlt.secrets.value,
    tables: Optional[List[str]] = None,
) -> List[DltResource]:
    """
    dlt source for Stripe data.

    Provides incremental loading for all Stripe objects.
    Uses 'created' timestamp for incremental sync.

    Args:
        api_key: Stripe API key
        tables: List of tables to sync (default: all)

    Returns:
        List of dlt resources
    """
    connector = StripeConnector(api_key=api_key)

    # Default to 30 days of historical data
    default_start = int((datetime.now() - timedelta(days=30)).timestamp())

    @dlt.resource(
        name="charges",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def charges(
        last_created: dlt.sources.incremental[int] = dlt.sources.incremental(
            "created",
            initial_value=default_start,
        )
    ) -> Iterator[TDataItem]:
        yield from connector.get_charges(created_after=last_created.last_value)

    @dlt.resource(
        name="customers",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def customers(
        last_created: dlt.sources.incremental[int] = dlt.sources.incremental(
            "created",
            initial_value=default_start,
        )
    ) -> Iterator[TDataItem]:
        yield from connector.get_customers(created_after=last_created.last_value)

    @dlt.resource(
        name="invoices",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def invoices(
        last_created: dlt.sources.incremental[int] = dlt.sources.incremental(
            "created",
            initial_value=default_start,
        )
    ) -> Iterator[TDataItem]:
        yield from connector.get_invoices(created_after=last_created.last_value)

    @dlt.resource(
        name="subscriptions",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def subscriptions(
        last_created: dlt.sources.incremental[int] = dlt.sources.incremental(
            "created",
            initial_value=default_start,
        )
    ) -> Iterator[TDataItem]:
        yield from connector.get_subscriptions(created_after=last_created.last_value)

    @dlt.resource(
        name="payouts",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def payouts(
        last_created: dlt.sources.incremental[int] = dlt.sources.incremental(
            "created",
            initial_value=default_start,
        )
    ) -> Iterator[TDataItem]:
        yield from connector.get_payouts(created_after=last_created.last_value)

    @dlt.resource(
        name="balance_transactions",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def balance_transactions(
        last_created: dlt.sources.incremental[int] = dlt.sources.incremental(
            "created",
            initial_value=default_start,
        )
    ) -> Iterator[TDataItem]:
        yield from connector.get_balance_transactions(created_after=last_created.last_value)

    @dlt.resource(
        name="payment_intents",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def payment_intents(
        last_created: dlt.sources.incremental[int] = dlt.sources.incremental(
            "created",
            initial_value=default_start,
        )
    ) -> Iterator[TDataItem]:
        yield from connector.get_payment_intents(created_after=last_created.last_value)

    @dlt.resource(
        name="refunds",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,
    )
    def refunds(
        last_created: dlt.sources.incremental[int] = dlt.sources.incremental(
            "created",
            initial_value=default_start,
        )
    ) -> Iterator[TDataItem]:
        yield from connector.get_refunds(created_after=last_created.last_value)

    # Build list of resources based on requested tables
    all_resources = {
        "charges": charges,
        "customers": customers,
        "invoices": invoices,
        "subscriptions": subscriptions,
        "payouts": payouts,
        "balance_transactions": balance_transactions,
        "payment_intents": payment_intents,
        "refunds": refunds,
    }

    if tables:
        resources = [all_resources[t] for t in tables if t in all_resources]
    else:
        resources = list(all_resources.values())

    logger.info(f"Created {len(resources)} resources for Stripe extraction")
    return resources
