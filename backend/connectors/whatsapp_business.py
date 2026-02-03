"""
WhatsApp Business API Connector using dlt framework.

Provides complete WhatsApp Business integration with message fetching,
template management, analytics, and webhook handling.
"""
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import dlt
from dlt.sources import DltResource
from dlt.common.typing import TDataItem
import logging
import hashlib
import hmac

logger = logging.getLogger(__name__)


class WhatsAppAPIError(Exception):
    """Custom exception for WhatsApp API errors."""
    pass


class WhatsAppBusinessConnector:
    """
    Production-ready WhatsApp Business API connector.

    Features:
    - Message fetching with pagination
    - Template management
    - Analytics data collection
    - Webhook handling for real-time events
    - Rate limiting and error handling
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        business_account_id: str,
        verify_token: Optional[str] = None,
        app_secret: Optional[str] = None,
    ):
        """
        Initialize WhatsApp Business connector.

        Args:
            access_token: WhatsApp Business API access token
            phone_number_id: Phone number ID
            business_account_id: Business account ID
            verify_token: Token for webhook verification
            app_secret: App secret for webhook signature verification
        """
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.business_account_id = business_account_id
        self.verify_token = verify_token
        self.app_secret = app_secret

        # Setup session with retry logic
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()

        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request payload
            params: Query parameters

        Returns:
            Response JSON data

        Raises:
            WhatsAppAPIError: If request fails
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
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
            error_data = e.response.json() if e.response else {}
            raise WhatsAppAPIError(
                f"API request failed: {e.response.status_code} - {error_data}"
            )
        except requests.exceptions.RequestException as e:
            raise WhatsAppAPIError(f"Request error: {str(e)}")

    def get_messages(
        self,
        limit: int = 100,
        after: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Fetch messages with pagination.

        Args:
            limit: Number of messages per page
            after: Cursor for pagination

        Yields:
            Message records
        """
        logger.info(f"Fetching messages for phone number {self.phone_number_id}")

        endpoint = f"/{self.phone_number_id}/messages"
        params = {"limit": limit}

        if after:
            params["after"] = after

        try:
            while True:
                response = self._make_request("GET", endpoint, params=params)

                messages = response.get("data", [])
                if not messages:
                    break

                for message in messages:
                    message["_dlt_load_time"] = datetime.now().isoformat()
                    message["_phone_number_id"] = self.phone_number_id
                    yield message

                # Check for next page
                paging = response.get("paging", {})
                cursors = paging.get("cursors", {})
                after_cursor = cursors.get("after")

                if not after_cursor:
                    break

                params["after"] = after_cursor

        except WhatsAppAPIError as e:
            logger.error(f"Error fetching messages: {str(e)}")

    def get_templates(self) -> Iterator[Dict[str, Any]]:
        """
        Fetch message templates.

        Yields:
            Template records
        """
        logger.info(f"Fetching templates for business account {self.business_account_id}")

        endpoint = f"/{self.business_account_id}/message_templates"
        params = {"limit": 100}

        try:
            while True:
                response = self._make_request("GET", endpoint, params=params)

                templates = response.get("data", [])
                if not templates:
                    break

                for template in templates:
                    template["_dlt_load_time"] = datetime.now().isoformat()
                    template["_business_account_id"] = self.business_account_id
                    yield template

                # Check for next page
                paging = response.get("paging", {})
                after_cursor = paging.get("cursors", {}).get("after")

                if not after_cursor:
                    break

                params["after"] = after_cursor

        except WhatsAppAPIError as e:
            logger.error(f"Error fetching templates: {str(e)}")

    def get_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "DAY",
    ) -> Iterator[Dict[str, Any]]:
        """
        Fetch analytics data.

        Args:
            start_date: Start date for analytics
            end_date: End date for analytics
            granularity: DAY or HOUR

        Yields:
            Analytics records
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        logger.info(
            f"Fetching analytics from {start_date} to {end_date} "
            f"with granularity {granularity}"
        )

        endpoint = f"/{self.phone_number_id}/analytics"
        params = {
            "start": int(start_date.timestamp()),
            "end": int(end_date.timestamp()),
            "granularity": granularity,
        }

        try:
            response = self._make_request("GET", endpoint, params=params)

            analytics = response.get("data", [])
            for record in analytics:
                record["_dlt_load_time"] = datetime.now().isoformat()
                record["_phone_number_id"] = self.phone_number_id
                record["_granularity"] = granularity
                yield record

        except WhatsAppAPIError as e:
            logger.error(f"Error fetching analytics: {str(e)}")

    def get_conversations(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Fetch conversation analytics.

        Args:
            start_date: Start date
            end_date: End date

        Yields:
            Conversation records
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        logger.info(f"Fetching conversations from {start_date} to {end_date}")

        endpoint = f"/{self.business_account_id}/conversation_analytics"
        params = {
            "start": int(start_date.timestamp()),
            "end": int(end_date.timestamp()),
            "granularity": "DAILY",
            "phone_numbers": [self.phone_number_id],
        }

        try:
            response = self._make_request("GET", endpoint, params=params)

            conversations = response.get("data", [])
            for conversation in conversations:
                conversation["_dlt_load_time"] = datetime.now().isoformat()
                conversation["_phone_number_id"] = self.phone_number_id
                yield conversation

        except WhatsAppAPIError as e:
            logger.error(f"Error fetching conversations: {str(e)}")

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Webhook payload
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self.app_secret:
            logger.warning("App secret not configured, cannot verify webhook signature")
            return False

        expected_signature = hmac.new(
            key=self.app_secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        signature_value = signature.replace("sha256=", "")
        return hmac.compare_digest(expected_signature, signature_value)

    def parse_webhook_event(self, event: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """
        Parse webhook event.

        Args:
            event: Webhook event data

        Yields:
            Parsed event records
        """
        entry_list = event.get("entry", [])

        for entry in entry_list:
            changes = entry.get("changes", [])

            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                statuses = value.get("statuses", [])

                # Process messages
                for message in messages:
                    yield {
                        "event_type": "message",
                        "timestamp": datetime.now().isoformat(),
                        "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
                        "from": message.get("from"),
                        "message_id": message.get("id"),
                        "message_type": message.get("type"),
                        "message_data": message,
                        "_dlt_load_time": datetime.now().isoformat(),
                    }

                # Process status updates
                for status in statuses:
                    yield {
                        "event_type": "status",
                        "timestamp": datetime.now().isoformat(),
                        "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
                        "message_id": status.get("id"),
                        "status": status.get("status"),
                        "status_data": status,
                        "_dlt_load_time": datetime.now().isoformat(),
                    }


@dlt.source(name="whatsapp_business")
def whatsapp_business_source(
    access_token: str = dlt.secrets.value,
    phone_number_id: str = dlt.secrets.value,
    business_account_id: str = dlt.secrets.value,
    verify_token: Optional[str] = dlt.secrets.value,
    app_secret: Optional[str] = dlt.secrets.value,
) -> List[DltResource]:
    """
    dlt source for WhatsApp Business data.

    Args:
        access_token: WhatsApp Business API access token
        phone_number_id: Phone number ID
        business_account_id: Business account ID
        verify_token: Webhook verification token
        app_secret: App secret for signature verification

    Returns:
        List of dlt resources
    """
    connector = WhatsAppBusinessConnector(
        access_token=access_token,
        phone_number_id=phone_number_id,
        business_account_id=business_account_id,
        verify_token=verify_token,
        app_secret=app_secret,
    )

    @dlt.resource(
        name="messages",
        write_disposition="merge",
        primary_key="id",
        parallelized=True,  # Enable parallel extraction
    )
    def messages(
        last_cursor: dlt.sources.incremental[str] = dlt.sources.incremental(
            "id",
            initial_value=None,
        )
    ) -> Iterator[TDataItem]:
        """Load WhatsApp messages incrementally (parallelized)."""
        after_cursor = last_cursor.last_value if last_cursor.last_value else None
        yield from connector.get_messages(after=after_cursor)

    @dlt.resource(name="templates", write_disposition="replace", parallelized=True)
    def templates() -> Iterator[TDataItem]:
        """Load WhatsApp message templates (parallelized)."""
        yield from connector.get_templates()

    @dlt.resource(name="analytics", write_disposition="append", parallelized=True)
    def analytics(
        last_date: dlt.sources.incremental[datetime] = dlt.sources.incremental(
            "data_point_start",
            initial_value=datetime.now() - timedelta(days=7),
        )
    ) -> Iterator[TDataItem]:
        """Load WhatsApp analytics data (parallelized)."""
        start_date = last_date.last_value
        end_date = datetime.now()

        yield from connector.get_analytics(
            start_date=start_date,
            end_date=end_date,
        )

    @dlt.resource(name="conversations", write_disposition="append", parallelized=True)
    def conversations(
        last_date: dlt.sources.incremental[datetime] = dlt.sources.incremental(
            "start",
            initial_value=datetime.now() - timedelta(days=7),
        )
    ) -> Iterator[TDataItem]:
        """Load WhatsApp conversation analytics (parallelized)."""
        start_date = last_date.last_value
        end_date = datetime.now()

        yield from connector.get_conversations(
            start_date=start_date,
            end_date=end_date,
        )

    logger.info("Created 4 parallelized resources for WhatsApp Business extraction")
    return [messages, templates, analytics, conversations]


if __name__ == "__main__":
    # Example usage
    pipeline = dlt.pipeline(
        pipeline_name="whatsapp_pipeline",
        destination="duckdb",
        dataset_name="whatsapp_data",
    )

    # Load data
    load_info = pipeline.run(whatsapp_business_source())
    logger.info(load_info)
