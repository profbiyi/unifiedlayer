"""
Generic REST API Connector using dlt framework.

Provides a configurable connector supporting multiple authentication types,
pagination strategies, and rate limiting for any REST API.

Supports both synchronous and asynchronous (parallel) data fetching:
- Sync mode: Traditional sequential requests
- Async mode: Concurrent requests using httpx for better I/O performance
"""
from typing import Iterator, Dict, Any, Optional, List, Union, Tuple, AsyncIterator
from datetime import datetime, timedelta
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import dlt
from dlt.sources import DltResource
from dlt.common.typing import TDataItem
import logging
import time
import asyncio
from urllib.parse import urljoin, urlparse, parse_qs

# Async HTTP client
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


class AuthType(str, Enum):
    """Supported authentication types."""
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    NONE = "none"


class PaginationType(str, Enum):
    """Supported pagination strategies."""
    OFFSET = "offset"
    PAGE = "page"
    CURSOR = "cursor"
    LINK_HEADER = "link_header"
    TOKEN = "token"
    NEXT_URL = "next_url"
    NONE = "none"


class RESTAPIError(Exception):
    """Custom exception for REST API connector errors."""
    pass


class RESTAPIConnector:
    """
    Production-ready generic REST API connector.

    Features:
    - Multiple authentication types (API key, Bearer, OAuth2, Basic)
    - Multiple pagination strategies (offset, page, cursor, link header, token, next_url)
    - Rate limiting
    - Configurable endpoints
    - Retry logic with exponential backoff

    Pagination Strategies:
        - PAGE: Page number + page size (e.g., page=1&page_size=100)
        - OFFSET: Offset + limit (e.g., offset=0&limit=100)
        - CURSOR: Cursor-based (e.g., cursor=abc123)
        - LINK_HEADER: RFC 5988 Link header with rel="next"
        - TOKEN: Token-based (e.g., next_page_token=xyz)
        - NEXT_URL: Full URL in response body (e.g., {"next": "https://..."})
        - NONE: No pagination (single request)
    """

    def __init__(
        self,
        base_url: str,
        auth_type: AuthType = AuthType.NONE,
        auth_config: Optional[Dict[str, Any]] = None,
        pagination_type: PaginationType = PaginationType.NONE,
        pagination_config: Optional[Dict[str, Any]] = None,
        rate_limit: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize REST API connector.

        Args:
            base_url: Base URL for the API
            auth_type: Type of authentication
            auth_config: Authentication configuration
            pagination_type: Type of pagination
            pagination_config: Pagination configuration
                - For PAGE: {"page_param": "page", "size_param": "page_size", "page_size": 100}
                - For OFFSET: {"offset_param": "offset", "limit_param": "limit", "limit": 100}
                - For CURSOR: {"cursor_path": "next_cursor", "cursor_param": "cursor"}
                - For TOKEN: {"token_path": "next_page_token", "token_param": "page_token"}
                - For NEXT_URL: {"next_url_path": "next"}
                - For LINK_HEADER: No config needed
            rate_limit: Max requests per minute
            headers: Additional headers
            retry_config: Retry configuration
                - total_retries: Max retries (default: 5)
                - backoff_factor: Exponential backoff multiplier (default: 2)
                - Example: {"total_retries": 3, "backoff_factor": 1.5}
        """
        self.base_url = base_url.rstrip("/")
        self.auth_type = AuthType(auth_type) if isinstance(auth_type, str) else auth_type
        self.auth_config = auth_config or {}
        self.pagination_type = PaginationType(pagination_type) if isinstance(pagination_type, str) else pagination_type
        self.pagination_config = pagination_config or {}
        self.rate_limit = rate_limit
        self.custom_headers = headers or {}
        self.retry_config = retry_config or {}

        # Validate pagination config
        self._validate_pagination_config()

        # Rate limiting state
        self.request_times: List[float] = []

        # OAuth2 token cache
        self.oauth_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # Setup session
        self.session = self._create_session()

    def _validate_pagination_config(self) -> None:
        """Validate pagination configuration based on pagination type."""
        if self.pagination_type == PaginationType.NONE:
            return

        config = self.pagination_config

        if self.pagination_type == PaginationType.PAGE:
            page_size = config.get("page_size")
            if page_size and (not isinstance(page_size, int) or page_size <= 0):
                raise RESTAPIError("page_size must be a positive integer")

        elif self.pagination_type == PaginationType.OFFSET:
            limit = config.get("limit")
            if limit and (not isinstance(limit, int) or limit <= 0):
                raise RESTAPIError("limit must be a positive integer")

        elif self.pagination_type == PaginationType.CURSOR:
            if not config.get("cursor_path"):
                logger.warning("cursor_path not specified, using default 'next_cursor'")
            if not config.get("cursor_param"):
                logger.warning("cursor_param not specified, using default 'cursor'")

        elif self.pagination_type == PaginationType.TOKEN:
            if not config.get("token_path"):
                logger.warning("token_path not specified, using default 'next_page_token'")
            if not config.get("token_param"):
                logger.warning("token_param not specified, using default 'page_token'")

        elif self.pagination_type == PaginationType.NEXT_URL:
            if not config.get("next_url_path"):
                logger.warning("next_url_path not specified, using default 'next'")

        # LINK_HEADER doesn't need configuration validation

    def _create_session(self) -> requests.Session:
        """Create requests session with configurable retry strategy."""
        session = requests.Session()

        # Get retry config with defaults
        total_retries = self.retry_config.get("total_retries", 5)
        backoff_factor = self.retry_config.get("backoff_factor", 2)
        status_forcelist = self.retry_config.get(
            "status_forcelist",
            [429, 500, 502, 503, 504]
        )

        retry_strategy = Retry(
            total=total_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        logger.info(f"Session configured with {total_retries} retries, backoff factor {backoff_factor}")

        return session

    def _check_rate_limit(self) -> None:
        """Implement rate limiting."""
        if not self.rate_limit:
            return

        current_time = time.time()

        # Remove old timestamps
        self.request_times = [
            t for t in self.request_times
            if current_time - t < 60
        ]

        # Check if limit reached
        if len(self.request_times) >= self.rate_limit:
            oldest_request = self.request_times[0]
            sleep_time = 60 - (current_time - oldest_request)
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

        self.request_times.append(current_time)

    def _get_oauth_token(self) -> str:
        """
        Get OAuth2 access token.

        Returns:
            Access token
        """
        # Return cached token if valid
        if self.oauth_token and self.token_expiry:
            if datetime.now() < self.token_expiry:
                return self.oauth_token

        token_url = self.auth_config.get("token_url")
        client_id = self.auth_config.get("client_id")
        client_secret = self.auth_config.get("client_secret")
        scope = self.auth_config.get("scope", "")

        if not all([token_url, client_id, client_secret]):
            raise RESTAPIError("OAuth2 configuration incomplete")

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope,
        }

        try:
            response = self.session.post(token_url, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            self.oauth_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

            logger.info("OAuth2 token obtained successfully")
            return self.oauth_token

        except requests.exceptions.RequestException as e:
            raise RESTAPIError(f"Failed to get OAuth2 token: {str(e)}")

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers based on auth type.

        Returns:
            Authentication headers
        """
        headers = {}

        if self.auth_type == AuthType.API_KEY:
            header_name = self.auth_config.get("header_name", "X-API-Key")
            api_key = self.auth_config.get("api_key")
            if api_key:
                headers[header_name] = api_key

        elif self.auth_type == AuthType.BEARER:
            token = self.auth_config.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == AuthType.OAUTH2:
            token = self._get_oauth_token()
            headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == AuthType.BASIC:
            # Basic auth is handled by requests.auth parameter
            pass

        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        return_headers: bool = False,
    ) -> Union[Dict[str, Any], Tuple[Dict[str, Any], Dict[str, str]]]:
        """
        Make authenticated API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request payload
            return_headers: If True, return tuple of (json_data, headers)

        Returns:
            Response JSON data, or tuple of (json_data, headers) if return_headers=True
        """
        self._check_rate_limit()

        url = urljoin(self.base_url, endpoint.lstrip("/"))
        headers = {**self.custom_headers, **self._get_auth_headers()}

        auth = None
        if self.auth_type == AuthType.BASIC:
            username = self.auth_config.get("username")
            password = self.auth_config.get("password")
            if username and password:
                auth = (username, password)

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                auth=auth,
                timeout=30,
            )
            response.raise_for_status()

            json_data = response.json()

            if return_headers:
                return json_data, dict(response.headers)

            return json_data

        except requests.exceptions.HTTPError as e:
            raise RESTAPIError(f"API request failed: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise RESTAPIError(f"Request error: {str(e)}")

    def fetch_data(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data_path: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Fetch data from endpoint with pagination support.

        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data_path: JSON path to data array (e.g., "data" or "results.items")

        Yields:
            Data records
        """
        params = params or {}
        page = 1
        offset = 0
        current_endpoint = endpoint

        while True:
            # Add pagination parameters
            if self.pagination_type == PaginationType.PAGE:
                page_param = self.pagination_config.get("page_param", "page")
                size_param = self.pagination_config.get("size_param", "page_size")
                page_size = self.pagination_config.get("page_size", 100)

                params[page_param] = page
                params[size_param] = page_size

            elif self.pagination_type == PaginationType.OFFSET:
                offset_param = self.pagination_config.get("offset_param", "offset")
                limit_param = self.pagination_config.get("limit_param", "limit")
                limit = self.pagination_config.get("limit", 100)

                params[offset_param] = offset
                params[limit_param] = limit

            try:
                # For LINK_HEADER, we need response headers
                return_headers = self.pagination_type == PaginationType.LINK_HEADER

                if return_headers:
                    response, headers = self._make_request(
                        method, current_endpoint, params=params, return_headers=True
                    )
                else:
                    response = self._make_request(method, current_endpoint, params=params)

                # Extract data from response
                if data_path:
                    data = response
                    for key in data_path.split("."):
                        data = data.get(key, []) if isinstance(data, dict) else []
                else:
                    # If response is already a list, use it directly
                    if isinstance(response, list):
                        data = response
                    elif isinstance(response, dict):
                        # Try common data keys
                        data = response.get("data") or response.get("results") or response.get("items") or response
                    else:
                        data = response

                if not isinstance(data, list):
                    data = [data] if data else []

                if not data:
                    break

                for item in data:
                    if isinstance(item, dict):
                        item["_dlt_load_time"] = datetime.now().isoformat()
                        yield item

                # Handle pagination
                if self.pagination_type == PaginationType.PAGE:
                    if len(data) < page_size:
                        break
                    page += 1

                elif self.pagination_type == PaginationType.OFFSET:
                    if len(data) < limit:
                        break
                    offset += limit

                elif self.pagination_type == PaginationType.CURSOR:
                    cursor_path = self.pagination_config.get("cursor_path", "next_cursor")
                    cursor_param = self.pagination_config.get("cursor_param", "cursor")

                    next_cursor = response
                    for key in cursor_path.split("."):
                        next_cursor = next_cursor.get(key) if isinstance(next_cursor, dict) else None

                    if not next_cursor:
                        break

                    params[cursor_param] = next_cursor

                elif self.pagination_type == PaginationType.LINK_HEADER:
                    # Parse Link header (RFC 5988)
                    # Example: <https://api.example.com/data?page=2>; rel="next"
                    link_header = headers.get("Link", "")
                    next_url = None

                    if link_header:
                        links = link_header.split(",")
                        for link in links:
                            if 'rel="next"' in link or "rel='next'" in link:
                                # Extract URL from <URL>
                                url_match = link.split(";")[0].strip()
                                if url_match.startswith("<") and url_match.endswith(">"):
                                    next_url = url_match[1:-1]
                                break

                    if not next_url:
                        break

                    # Parse the next URL to extract endpoint and params
                    parsed = urlparse(next_url)
                    current_endpoint = parsed.path
                    params = dict(parse_qs(parsed.query))
                    # Convert single-item lists to strings
                    params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

                elif self.pagination_type == PaginationType.TOKEN:
                    # Token-based pagination (e.g., next_page_token)
                    token_path = self.pagination_config.get("token_path", "next_page_token")
                    token_param = self.pagination_config.get("token_param", "page_token")

                    next_token = response
                    for key in token_path.split("."):
                        next_token = next_token.get(key) if isinstance(next_token, dict) else None

                    if not next_token:
                        break

                    params[token_param] = next_token

                elif self.pagination_type == PaginationType.NEXT_URL:
                    # Next URL in response body (e.g., "next": "https://...")
                    next_url_path = self.pagination_config.get("next_url_path", "next")

                    next_url = response
                    for key in next_url_path.split("."):
                        next_url = next_url.get(key) if isinstance(next_url, dict) else None

                    if not next_url:
                        break

                    # Parse the next URL
                    parsed = urlparse(next_url)
                    current_endpoint = parsed.path
                    params = dict(parse_qs(parsed.query))
                    # Convert single-item lists to strings
                    params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

                else:
                    # No pagination
                    break

            except RESTAPIError as e:
                logger.error(f"Error fetching data: {str(e)}")
                break


class AsyncRESTAPIConnector:
    """
    Async version of REST API connector for parallel data fetching.

    Uses httpx.AsyncClient for concurrent HTTP requests, allowing
    one thread to handle hundreds of I/O operations without waiting.
    """

    def __init__(
        self,
        base_url: str,
        auth_type: AuthType = AuthType.NONE,
        auth_config: Optional[Dict[str, Any]] = None,
        pagination_type: PaginationType = PaginationType.NONE,
        pagination_config: Optional[Dict[str, Any]] = None,
        rate_limit: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 10,
    ):
        """
        Initialize async REST API connector.

        Args:
            base_url: Base URL for the API
            auth_type: Type of authentication
            auth_config: Authentication configuration
            pagination_type: Type of pagination
            pagination_config: Pagination configuration
            rate_limit: Max requests per minute
            headers: Additional headers
            retry_config: Retry configuration
            max_concurrent: Maximum concurrent requests (default: 10)
        """
        if not HTTPX_AVAILABLE:
            raise RESTAPIError("httpx is required for async mode. Install with: pip install httpx")

        self.base_url = base_url.rstrip("/")
        self.auth_type = AuthType(auth_type) if isinstance(auth_type, str) else auth_type
        self.auth_config = auth_config or {}
        self.pagination_type = PaginationType(pagination_type) if isinstance(pagination_type, str) else pagination_type
        self.pagination_config = pagination_config or {}
        self.rate_limit = rate_limit
        self.custom_headers = headers or {}
        self.retry_config = retry_config or {}
        self.max_concurrent = max_concurrent

        # Rate limiting state
        self.request_times: List[float] = []
        self._rate_limit_lock = asyncio.Lock()

        # OAuth2 token cache
        self.oauth_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._token_lock = asyncio.Lock()

        # Semaphore for concurrent request limiting
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Create httpx async client with retry configuration."""
        total_retries = self.retry_config.get("total_retries", 5)

        transport = httpx.AsyncHTTPTransport(retries=total_retries)

        return httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )

    async def _check_rate_limit(self) -> None:
        """Implement async rate limiting."""
        if not self.rate_limit:
            return

        async with self._rate_limit_lock:
            current_time = time.time()

            # Remove old timestamps
            self.request_times = [
                t for t in self.request_times
                if current_time - t < 60
            ]

            # Check if limit reached
            if len(self.request_times) >= self.rate_limit:
                oldest_request = self.request_times[0]
                sleep_time = 60 - (current_time - oldest_request)
                if sleep_time > 0:
                    logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                    await asyncio.sleep(sleep_time)

            self.request_times.append(current_time)

    async def _get_oauth_token(self, client: httpx.AsyncClient) -> str:
        """Get OAuth2 access token asynchronously."""
        async with self._token_lock:
            # Return cached token if valid
            if self.oauth_token and self.token_expiry:
                if datetime.now() < self.token_expiry:
                    return self.oauth_token

            token_url = self.auth_config.get("token_url")
            client_id = self.auth_config.get("client_id")
            client_secret = self.auth_config.get("client_secret")
            scope = self.auth_config.get("scope", "")

            if not all([token_url, client_id, client_secret]):
                raise RESTAPIError("OAuth2 configuration incomplete")

            data = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope,
            }

            try:
                response = await client.post(token_url, data=data)
                response.raise_for_status()

                token_data = response.json()
                self.oauth_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

                logger.info("OAuth2 token obtained successfully")
                return self.oauth_token

            except httpx.HTTPError as e:
                raise RESTAPIError(f"Failed to get OAuth2 token: {str(e)}")

    async def _get_auth_headers(self, client: httpx.AsyncClient) -> Dict[str, str]:
        """Get authentication headers based on auth type."""
        headers = {}

        if self.auth_type == AuthType.API_KEY:
            header_name = self.auth_config.get("header_name", "X-API-Key")
            api_key = self.auth_config.get("api_key")
            if api_key:
                headers[header_name] = api_key

        elif self.auth_type == AuthType.BEARER:
            token = self.auth_config.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == AuthType.OAUTH2:
            token = await self._get_oauth_token(client)
            headers["Authorization"] = f"Bearer {token}"

        return headers

    async def _make_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        return_headers: bool = False,
    ) -> Union[Dict[str, Any], Tuple[Dict[str, Any], Dict[str, str]]]:
        """Make authenticated async API request."""
        await self._check_rate_limit()

        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        auth_headers = await self._get_auth_headers(client)
        headers = {**self.custom_headers, **auth_headers}

        auth = None
        if self.auth_type == AuthType.BASIC:
            username = self.auth_config.get("username")
            password = self.auth_config.get("password")
            if username and password:
                auth = httpx.BasicAuth(username, password)

        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                auth=auth,
            )
            response.raise_for_status()

            json_data = response.json()

            if return_headers:
                return json_data, dict(response.headers)

            return json_data

        except httpx.HTTPStatusError as e:
            raise RESTAPIError(f"API request failed: {e.response.status_code} - {e.response.text}")
        except httpx.HTTPError as e:
            raise RESTAPIError(f"Request error: {str(e)}")

    async def fetch_data(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data_path: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Fetch data from endpoint with pagination support (async).

        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data_path: JSON path to data array

        Yields:
            Data records
        """
        params = params.copy() if params else {}
        page = 1
        offset = 0
        current_endpoint = endpoint

        async with self._get_client() as client:
            while True:
                # Add pagination parameters
                if self.pagination_type == PaginationType.PAGE:
                    page_param = self.pagination_config.get("page_param", "page")
                    size_param = self.pagination_config.get("size_param", "page_size")
                    page_size = self.pagination_config.get("page_size", 100)

                    params[page_param] = page
                    params[size_param] = page_size

                elif self.pagination_type == PaginationType.OFFSET:
                    offset_param = self.pagination_config.get("offset_param", "offset")
                    limit_param = self.pagination_config.get("limit_param", "limit")
                    limit = self.pagination_config.get("limit", 100)

                    params[offset_param] = offset
                    params[limit_param] = limit

                try:
                    return_headers = self.pagination_type == PaginationType.LINK_HEADER

                    if return_headers:
                        response, headers = await self._make_request(
                            client, method, current_endpoint, params=params, return_headers=True
                        )
                    else:
                        response = await self._make_request(
                            client, method, current_endpoint, params=params
                        )

                    # Extract data from response
                    if data_path:
                        data = response
                        for key in data_path.split("."):
                            data = data.get(key, []) if isinstance(data, dict) else []
                    else:
                        if isinstance(response, list):
                            data = response
                        elif isinstance(response, dict):
                            data = response.get("data") or response.get("results") or response.get("items") or response
                        else:
                            data = response

                    if not isinstance(data, list):
                        data = [data] if data else []

                    if not data:
                        break

                    for item in data:
                        if isinstance(item, dict):
                            item["_dlt_load_time"] = datetime.now().isoformat()
                            yield item

                    # Handle pagination (same logic as sync version)
                    if self.pagination_type == PaginationType.PAGE:
                        if len(data) < page_size:
                            break
                        page += 1

                    elif self.pagination_type == PaginationType.OFFSET:
                        if len(data) < limit:
                            break
                        offset += limit

                    elif self.pagination_type == PaginationType.CURSOR:
                        cursor_path = self.pagination_config.get("cursor_path", "next_cursor")
                        cursor_param = self.pagination_config.get("cursor_param", "cursor")

                        next_cursor = response
                        for key in cursor_path.split("."):
                            next_cursor = next_cursor.get(key) if isinstance(next_cursor, dict) else None

                        if not next_cursor:
                            break

                        params[cursor_param] = next_cursor

                    elif self.pagination_type == PaginationType.LINK_HEADER:
                        link_header = headers.get("Link", "")
                        next_url = None

                        if link_header:
                            links = link_header.split(",")
                            for link in links:
                                if 'rel="next"' in link or "rel='next'" in link:
                                    url_match = link.split(";")[0].strip()
                                    if url_match.startswith("<") and url_match.endswith(">"):
                                        next_url = url_match[1:-1]
                                    break

                        if not next_url:
                            break

                        parsed = urlparse(next_url)
                        current_endpoint = parsed.path
                        params = dict(parse_qs(parsed.query))
                        params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

                    elif self.pagination_type == PaginationType.TOKEN:
                        token_path = self.pagination_config.get("token_path", "next_page_token")
                        token_param = self.pagination_config.get("token_param", "page_token")

                        next_token = response
                        for key in token_path.split("."):
                            next_token = next_token.get(key) if isinstance(next_token, dict) else None

                        if not next_token:
                            break

                        params[token_param] = next_token

                    elif self.pagination_type == PaginationType.NEXT_URL:
                        next_url_path = self.pagination_config.get("next_url_path", "next")

                        next_url = response
                        for key in next_url_path.split("."):
                            next_url = next_url.get(key) if isinstance(next_url, dict) else None

                        if not next_url:
                            break

                        parsed = urlparse(next_url)
                        current_endpoint = parsed.path
                        params = dict(parse_qs(parsed.query))
                        params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

                    else:
                        break

                except RESTAPIError as e:
                    logger.error(f"Error fetching data: {str(e)}")
                    break

    async def fetch_multiple_endpoints(
        self,
        endpoints: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch data from multiple endpoints concurrently.

        Args:
            endpoints: List of endpoint configurations with 'name', 'path', etc.

        Returns:
            Dictionary mapping endpoint names to their data
        """
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)

        async def fetch_endpoint(endpoint_config: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
            async with self._semaphore:
                name = endpoint_config.get("name")
                path = endpoint_config.get("path")
                method = endpoint_config.get("method", "GET")
                data_path = endpoint_config.get("data_path")

                results = []
                async for item in self.fetch_data(path, method, data_path=data_path):
                    results.append(item)

                return name, results

        tasks = [fetch_endpoint(ep) for ep in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error fetching endpoint: {result}")
            else:
                name, items = result
                data[name] = items

        return data


@dlt.source(name="rest_api")
def rest_api_source(
    base_url: str,
    endpoints: List[Dict[str, Any]],
    auth_type: str = "none",
    auth_config: Optional[Dict[str, Any]] = None,
    pagination_type: str = "none",
    pagination_config: Optional[Dict[str, Any]] = None,
    rate_limit: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    output_format: str = "table",  # "table", "json", or "both"
    retry_config: Optional[Dict[str, Any]] = None,
) -> List[DltResource]:
    """
    dlt source for generic REST API.

    Args:
        base_url: Base URL for the API
        endpoints: List of endpoint configurations
        auth_type: Authentication type
        auth_config: Authentication configuration
        pagination_type: Pagination type
        pagination_config: Pagination configuration
        rate_limit: Max requests per minute
        headers: Additional headers
        output_format: Output format - "table" (normalized), "json" (raw), or "both"

    Returns:
        List of dlt resources

    Output Formats:
        - "table": Data is normalized into columns (default)
        - "json": Data is stored as raw JSON in a single column
        - "both": Data is stored both as columns AND as raw JSON

    Example:
        endpoints = [
            {
                "name": "users",
                "path": "/api/users",
                "method": "GET",
                "data_path": "data",
                "primary_key": "id",
                "output_format": "table"  # Optional, overrides source-level setting
            },
            {
                "name": "orders",
                "path": "/api/orders",
                "method": "GET",
                "data_path": "results",
                "primary_key": "order_id",
                "output_format": "json"  # Store as raw JSON
            },
        ]
    """
    connector = RESTAPIConnector(
        base_url=base_url,
        auth_type=auth_type,
        auth_config=auth_config,
        pagination_type=pagination_type,
        pagination_config=pagination_config,
        rate_limit=rate_limit,
        headers=headers,
        retry_config=retry_config,
    )

    resources = []

    for endpoint_config in endpoints:
        name = endpoint_config.get("name")
        path = endpoint_config.get("path")
        method = endpoint_config.get("method", "GET")
        data_path = endpoint_config.get("data_path")
        primary_key = endpoint_config.get("primary_key")
        write_disposition = endpoint_config.get("write_disposition", "append")

        # Get output format (endpoint-level overrides source-level)
        endpoint_format = endpoint_config.get("output_format", output_format)

        if endpoint_format == "json":
            # Store as raw JSON in a single column
            @dlt.resource(
                name=name,
                write_disposition=write_disposition,
                primary_key=primary_key,
            )
            def load_endpoint_json(
                endpoint_path: str = path,
                http_method: str = method,
                json_path: Optional[str] = data_path,
            ) -> Iterator[TDataItem]:
                """Load data from REST API endpoint as raw JSON."""
                import json as json_lib

                for item in connector.fetch_data(
                    endpoint=endpoint_path,
                    method=http_method,
                    data_path=json_path,
                ):
                    # Convert entire record to JSON string
                    yield {
                        "data": json_lib.dumps(item),
                        "id": item.get(primary_key) if primary_key else None,
                        "_dlt_load_time": item.get("_dlt_load_time"),
                    }

            resources.append(load_endpoint_json)

        elif endpoint_format == "both":
            # Store both normalized columns AND raw JSON
            @dlt.resource(
                name=name,
                write_disposition=write_disposition,
                primary_key=primary_key,
            )
            def load_endpoint_both(
                endpoint_path: str = path,
                http_method: str = method,
                json_path: Optional[str] = data_path,
            ) -> Iterator[TDataItem]:
                """Load data from REST API endpoint with raw JSON column."""
                import json as json_lib

                for item in connector.fetch_data(
                    endpoint=endpoint_path,
                    method=http_method,
                    data_path=json_path,
                ):
                    # Create copy without internal fields for raw JSON
                    raw_item = {k: v for k, v in item.items() if not k.startswith('_dlt_')}

                    # Add raw JSON column
                    item["_raw_json"] = json_lib.dumps(raw_item)
                    yield item

            resources.append(load_endpoint_both)

        else:  # "table" format (default)
            # Standard normalized format
            @dlt.resource(
                name=name,
                write_disposition=write_disposition,
                primary_key=primary_key,
            )
            def load_endpoint(
                endpoint_path: str = path,
                http_method: str = method,
                json_path: Optional[str] = data_path,
            ) -> Iterator[TDataItem]:
                """Load data from REST API endpoint."""
                yield from connector.fetch_data(
                    endpoint=endpoint_path,
                    method=http_method,
                    data_path=json_path,
                )

            resources.append(load_endpoint)

    return resources


@dlt.source(name="rest_api_async")
def rest_api_source_async(
    base_url: str,
    endpoints: List[Dict[str, Any]],
    auth_type: str = "none",
    auth_config: Optional[Dict[str, Any]] = None,
    pagination_type: str = "none",
    pagination_config: Optional[Dict[str, Any]] = None,
    rate_limit: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    output_format: str = "table",
    retry_config: Optional[Dict[str, Any]] = None,
    max_concurrent: int = 10,
) -> List[DltResource]:
    """
    Async dlt source for generic REST API with parallel processing.

    Uses async/await for concurrent HTTP requests, allowing one thread
    to handle many I/O operations simultaneously without waiting.

    Args:
        base_url: Base URL for the API
        endpoints: List of endpoint configurations
        auth_type: Authentication type
        auth_config: Authentication configuration
        pagination_type: Pagination type
        pagination_config: Pagination configuration
        rate_limit: Max requests per minute
        headers: Additional headers
        output_format: Output format - "table" (normalized), "json" (raw), or "both"
        retry_config: Retry configuration
        max_concurrent: Maximum concurrent requests (default: 10)

    Returns:
        List of async dlt resources

    Example:
        endpoints = [
            {
                "name": "users",
                "path": "/api/v1/users",
                "data_path": "data",
                "primary_key": "id",
            },
            {
                "name": "orders",
                "path": "/api/v1/orders",
                "data_path": "results",
                "primary_key": "order_id",
            },
        ]

        # All endpoints will be fetched concurrently
        pipeline.run(rest_api_source_async(...))
    """
    if not HTTPX_AVAILABLE:
        logger.warning("httpx not available, falling back to sync mode")
        return rest_api_source(
            base_url=base_url,
            endpoints=endpoints,
            auth_type=auth_type,
            auth_config=auth_config,
            pagination_type=pagination_type,
            pagination_config=pagination_config,
            rate_limit=rate_limit,
            headers=headers,
            output_format=output_format,
            retry_config=retry_config,
        )

    connector = AsyncRESTAPIConnector(
        base_url=base_url,
        auth_type=auth_type,
        auth_config=auth_config,
        pagination_type=pagination_type,
        pagination_config=pagination_config,
        rate_limit=rate_limit,
        headers=headers,
        retry_config=retry_config,
        max_concurrent=max_concurrent,
    )

    resources = []

    for endpoint_config in endpoints:
        name = endpoint_config.get("name")
        path = endpoint_config.get("path")
        method = endpoint_config.get("method", "GET")
        data_path = endpoint_config.get("data_path")
        primary_key = endpoint_config.get("primary_key")
        write_disposition = endpoint_config.get("write_disposition", "append")
        endpoint_format = endpoint_config.get("output_format", output_format)

        if endpoint_format == "json":
            @dlt.resource(
                name=name,
                write_disposition=write_disposition,
                primary_key=primary_key,
            )
            async def load_endpoint_json_async(
                endpoint_path: str = path,
                http_method: str = method,
                json_path: Optional[str] = data_path,
            ) -> AsyncIterator[TDataItem]:
                """Load data from REST API endpoint as raw JSON (async)."""
                import json as json_lib

                async for item in connector.fetch_data(
                    endpoint=endpoint_path,
                    method=http_method,
                    data_path=json_path,
                ):
                    yield {
                        "data": json_lib.dumps(item),
                        "id": item.get(primary_key) if primary_key else None,
                        "_dlt_load_time": item.get("_dlt_load_time"),
                    }

            resources.append(load_endpoint_json_async)

        elif endpoint_format == "both":
            @dlt.resource(
                name=name,
                write_disposition=write_disposition,
                primary_key=primary_key,
            )
            async def load_endpoint_both_async(
                endpoint_path: str = path,
                http_method: str = method,
                json_path: Optional[str] = data_path,
            ) -> AsyncIterator[TDataItem]:
                """Load data from REST API endpoint with raw JSON column (async)."""
                import json as json_lib

                async for item in connector.fetch_data(
                    endpoint=endpoint_path,
                    method=http_method,
                    data_path=json_path,
                ):
                    raw_item = {k: v for k, v in item.items() if not k.startswith('_dlt_')}
                    item["_raw_json"] = json_lib.dumps(raw_item)
                    yield item

            resources.append(load_endpoint_both_async)

        else:  # "table" format (default)
            @dlt.resource(
                name=name,
                write_disposition=write_disposition,
                primary_key=primary_key,
            )
            async def load_endpoint_async(
                endpoint_path: str = path,
                http_method: str = method,
                json_path: Optional[str] = data_path,
            ) -> AsyncIterator[TDataItem]:
                """Load data from REST API endpoint (async)."""
                async for item in connector.fetch_data(
                    endpoint=endpoint_path,
                    method=http_method,
                    data_path=json_path,
                ):
                    yield item

            resources.append(load_endpoint_async)

    return resources


# Factory function to choose sync or async based on configuration
def create_rest_api_source(
    base_url: str,
    endpoints: List[Dict[str, Any]],
    auth_type: str = "none",
    auth_config: Optional[Dict[str, Any]] = None,
    pagination_type: str = "none",
    pagination_config: Optional[Dict[str, Any]] = None,
    rate_limit: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    output_format: str = "table",
    retry_config: Optional[Dict[str, Any]] = None,
    async_mode: bool = True,
    max_concurrent: int = 10,
) -> List[DltResource]:
    """
    Create REST API source with automatic async/sync selection.

    This factory function automatically uses async mode for better
    performance when httpx is available, falling back to sync mode otherwise.

    Args:
        base_url: Base URL for the API
        endpoints: List of endpoint configurations
        auth_type: Authentication type
        auth_config: Authentication configuration
        pagination_type: Pagination type
        pagination_config: Pagination configuration
        rate_limit: Max requests per minute
        headers: Additional headers
        output_format: Output format - "table", "json", or "both"
        retry_config: Retry configuration
        async_mode: Use async mode if available (default: True)
        max_concurrent: Maximum concurrent requests for async mode

    Returns:
        List of dlt resources (async or sync based on availability)

    Example:
        # Automatically uses async for parallel processing
        source = create_rest_api_source(
            base_url="https://api.example.com",
            endpoints=[
                {"name": "users", "path": "/users", "data_path": "data"},
                {"name": "orders", "path": "/orders", "data_path": "items"},
            ],
            auth_type="bearer",
            auth_config={"token": "your-token"},
        )

        pipeline.run(source)
    """
    if async_mode and HTTPX_AVAILABLE:
        logger.info(f"Using async REST API source with {max_concurrent} concurrent requests")
        return rest_api_source_async(
            base_url=base_url,
            endpoints=endpoints,
            auth_type=auth_type,
            auth_config=auth_config,
            pagination_type=pagination_type,
            pagination_config=pagination_config,
            rate_limit=rate_limit,
            headers=headers,
            output_format=output_format,
            retry_config=retry_config,
            max_concurrent=max_concurrent,
        )
    else:
        logger.info("Using sync REST API source")
        return rest_api_source(
            base_url=base_url,
            endpoints=endpoints,
            auth_type=auth_type,
            auth_config=auth_config,
            pagination_type=pagination_type,
            pagination_config=pagination_config,
            rate_limit=rate_limit,
            headers=headers,
            output_format=output_format,
            retry_config=retry_config,
        )


if __name__ == "__main__":
    # Example usage with async mode
    pipeline = dlt.pipeline(
        pipeline_name="rest_api_pipeline",
        destination="duckdb",
        dataset_name="api_data",
    )

    # Configure endpoints - all will be fetched concurrently
    endpoints = [
        {
            "name": "users",
            "path": "/api/v1/users",
            "data_path": "data",
            "primary_key": "id",
        },
        {
            "name": "posts",
            "path": "/api/v1/posts",
            "data_path": "data",
            "primary_key": "id",
        },
    ]

    # Load data using async source (automatic parallel processing)
    load_info = pipeline.run(
        create_rest_api_source(
            base_url="https://api.example.com",
            endpoints=endpoints,
            auth_type="bearer",
            auth_config={"token": "your-token-here"},
            pagination_type="page",
            pagination_config={"page_size": 100},
            async_mode=True,  # Enable parallel processing
            max_concurrent=10,  # Up to 10 concurrent requests
        )
    )
    logger.info(load_info)
