"""
M-Pesa Connector using dlt framework.

Provides complete M-Pesa integration with OAuth2 authentication,
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


class MPesaAPIError(Exception):
    """Custom exception for M-Pesa API errors."""
    pass


class MPesaConnector:
    """
    Production-ready M-Pesa connector with OAuth2 authentication.

    Features:
    - OAuth2 token management with auto-refresh
    - Incremental loading with state management
    - Exponential backoff retry logic
    - Rate limit handling (100 requests per minute)
    - Comprehensive error handling
    """

    BASE_URL = "https://api.safaricom.co.ke"
    TOKEN_URL = "/oauth/v1/generate?grant_type=client_credentials"
    TRANSACTIONS_URL = "/mpesa/transactionstatus/v1/query"
    B2C_URL = "/mpesa/b2c/v1/paymentrequest"

    # Rate limiting: 100 requests per minute
    MAX_REQUESTS_PER_MINUTE = 100
    RATE_LIMIT_WINDOW = 60  # seconds

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        environment: str = "sandbox",
        passkey: Optional[str] = None,
        shortcode: Optional[str] = None,
    ):
        """
        Initialize M-Pesa connector.

        Args:
            consumer_key: M-Pesa consumer key
            consumer_secret: M-Pesa consumer secret
            environment: 'sandbox' or 'production'
            passkey: M-Pesa passkey for specific operations
            shortcode: Business shortcode
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.environment = environment
        self.passkey = passkey
        self.shortcode = shortcode

        if environment == "production":
            self.BASE_URL = "https://api.safaricom.co.ke"
        else:
            self.BASE_URL = "https://sandbox.safaricom.co.ke"

        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # Rate limiting state
        self.request_times: List[float] = []

        # Setup session with retry logic
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()

        # Exponential backoff retry strategy
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,  # 2, 4, 8, 16, 32 seconds
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _check_rate_limit(self) -> None:
        """Implement rate limiting to avoid API throttling."""
        current_time = time.time()

        # Remove timestamps outside the current window
        self.request_times = [
            t for t in self.request_times
            if current_time - t < self.RATE_LIMIT_WINDOW
        ]

        # Check if we've hit the rate limit
        if len(self.request_times) >= self.MAX_REQUESTS_PER_MINUTE:
            oldest_request = self.request_times[0]
            sleep_time = self.RATE_LIMIT_WINDOW - (current_time - oldest_request)
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

        # Record this request
        self.request_times.append(current_time)

    def _get_access_token(self) -> str:
        """
        Get OAuth2 access token with automatic refresh.

        Returns:
            Valid access token

        Raises:
            MPesaAPIError: If token generation fails
        """
        # Return cached token if still valid
        if self.access_token and self.token_expiry:
            if datetime.now() < self.token_expiry - timedelta(minutes=5):
                return self.access_token

        logger.info("Generating new M-Pesa access token")

        try:
            response = self.session.get(
                f"{self.BASE_URL}{self.TOKEN_URL}",
                auth=(self.consumer_key, self.consumer_secret),
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]
            expires_in = int(data.get("expires_in", 3600))
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

            logger.info(f"Access token generated, expires in {expires_in} seconds")
            return self.access_token

        except requests.exceptions.RequestException as e:
            raise MPesaAPIError(f"Failed to generate access token: {str(e)}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated API request with rate limiting.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            data: Request payload
            params: Query parameters

        Returns:
            Response JSON data

        Raises:
            MPesaAPIError: If request fails
        """
        self._check_rate_limit()

        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limit exceeded, backing off")
                time.sleep(5)
                return self._make_request(method, endpoint, data, params)
            raise MPesaAPIError(f"API request failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise MPesaAPIError(f"Request error: {str(e)}")

    def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        transaction_type: str = "all",
    ) -> Iterator[TDataItem]:
        """
        Fetch M-Pesa transactions with incremental loading support.

        Args:
            start_date: Start date for transactions
            end_date: End date for transactions
            transaction_type: Type of transactions (all, c2b, b2c, b2b)

        Yields:
            Transaction records
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        logger.info(f"Fetching M-Pesa transactions from {start_date} to {end_date}")

        page = 1
        page_size = 100

        while True:
            params = {
                "start_date": start_date.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d"),
                "transaction_type": transaction_type,
                "page": page,
                "page_size": page_size,
            }

            try:
                response = self._make_request("GET", "/mpesa/transactions", params=params)

                transactions = response.get("transactions", [])
                if not transactions:
                    break

                for transaction in transactions:
                    # Add metadata
                    transaction["_dlt_load_time"] = datetime.now().isoformat()
                    transaction["_transaction_type"] = transaction_type
                    yield transaction

                # Check if there are more pages
                if len(transactions) < page_size:
                    break

                page += 1

            except MPesaAPIError as e:
                logger.error(f"Error fetching transactions: {str(e)}")
                break

    def get_balance(self) -> Dict[str, Any]:
        """
        Get M-Pesa account balance.

        Returns:
            Account balance information
        """
        logger.info("Fetching M-Pesa account balance")

        payload = {
            "Initiator": self.shortcode,
            "CommandID": "AccountBalance",
            "PartyA": self.shortcode,
            "IdentifierType": "4",
            "Remarks": "Balance query",
        }

        return self._make_request("POST", "/mpesa/accountbalance/v1/query", data=payload)


MPESA_TABLES = ["transactions", "balance"]

MPESA_TABLE_SCHEMAS = {
    "transactions": {
        "transaction_id": "string",
        "transaction_date": "datetime",
        "amount": "number",
        "currency": "string",
        "transaction_type": "string",
        "sender": "string",
        "receiver": "string",
        "status": "string",
    },
    "balance": {
        "available_balance": "number",
        "currency": "string",
        "_dlt_load_time": "datetime",
    },
}


@register_connector("mpesa")
class MPesaSDKConnector(BaseConnector):
    """M-Pesa connector using the BaseConnector SDK interface."""

    metadata = ConnectorMetadata(
        name="mpesa",
        display_name="M-Pesa",
        description="Sync transactions and balances from Safaricom M-Pesa.",
        icon="mpesa",
        category="payment",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_schema_discovery=True,
            auth_types=[AuthType.OAUTH2],
            pagination_type=PaginationType.PAGE_NUMBER,
        ),
        supported_tables=MPESA_TABLES,
    )

    def setup(self):
        creds = self.config.credentials
        self._connector = MPesaConnector(
            consumer_key=creds.get("consumer_key", ""),
            consumer_secret=creds.get("consumer_secret", ""),
            environment=creds.get("environment", "sandbox"),
            passkey=creds.get("passkey"),
            shortcode=creds.get("shortcode"),
        )

    def get_metadata(self) -> ConnectorMetadata:
        return self.metadata

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["consumer_key", "consumer_secret"],
            "properties": {
                "consumer_key": {"type": "string", "description": "M-Pesa Consumer Key", "secret": True},
                "consumer_secret": {"type": "string", "description": "M-Pesa Consumer Secret", "secret": True},
                "environment": {"type": "string", "enum": ["sandbox", "production"], "default": "sandbox"},
                "passkey": {"type": "string", "description": "M-Pesa Passkey", "secret": True},
                "shortcode": {"type": "string", "description": "Business Shortcode"},
            },
        }

    def test_connection(self) -> Dict[str, Any]:
        try:
            self._connector._get_access_token()
            return {"success": True, "message": "Connected. Token obtained."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def discover_schema(self) -> Dict[str, Any]:
        return MPESA_TABLE_SCHEMAS

    def extract(self, table_name: str = "transactions", **kwargs) -> Iterator[Dict[str, Any]]:
        if table_name not in MPESA_TABLES:
            raise ValueError(f"Unknown table: {table_name}. Supported: {MPESA_TABLES}")
        logger.info(f"Extracting M-Pesa {table_name}")
        if table_name == "transactions":
            yield from self._connector.get_transactions()
        elif table_name == "balance":
            data = self._connector.get_balance()
            data["_dlt_load_time"] = datetime.now().isoformat()
            yield data

    def close(self):
        self._connector.session.close()


@dlt.source(name="mpesa")
def mpesa_source(
    consumer_key: str = dlt.secrets.value,
    consumer_secret: str = dlt.secrets.value,
    environment: str = "sandbox",
    passkey: Optional[str] = dlt.secrets.value,
    shortcode: Optional[str] = dlt.secrets.value,
) -> List[DltResource]:
    """
    dlt source for M-Pesa data.

    Provides incremental loading with state management.

    Args:
        consumer_key: M-Pesa consumer key
        consumer_secret: M-Pesa consumer secret
        environment: sandbox or production
        passkey: M-Pesa passkey
        shortcode: Business shortcode

    Returns:
        List of dlt resources
    """
    connector = MPesaConnector(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        environment=environment,
        passkey=passkey,
        shortcode=shortcode,
    )

    @dlt.resource(
        name="transactions",
        write_disposition="merge",
        primary_key="transaction_id",
        parallelized=True,  # Enable parallel extraction
    )
    def transactions(
        last_transaction_date: dlt.sources.incremental[datetime] = dlt.sources.incremental(
            "transaction_date",
            initial_value=datetime.now() - timedelta(days=30),
        )
    ) -> Iterator[TDataItem]:
        """
        Load M-Pesa transactions incrementally (parallelized).

        Tracks the last transaction date to only fetch new records.
        """
        start_date = last_transaction_date.last_value
        end_date = datetime.now()

        yield from connector.get_transactions(
            start_date=start_date,
            end_date=end_date,
        )

    @dlt.resource(name="balance", parallelized=True)  # Enable parallel extraction
    def balance() -> Iterator[TDataItem]:
        """Load current M-Pesa account balance (parallelized)."""
        balance_data = connector.get_balance()
        balance_data["_dlt_load_time"] = datetime.now().isoformat()
        yield balance_data

    logger.info("Created 2 parallelized resources for M-Pesa extraction")
    return [transactions, balance]


if __name__ == "__main__":
    # Example usage
    pipeline = dlt.pipeline(
        pipeline_name="mpesa_pipeline",
        destination="duckdb",
        dataset_name="mpesa_data",
    )

    # Load data
    load_info = pipeline.run(mpesa_source())
    logger.info(load_info)
