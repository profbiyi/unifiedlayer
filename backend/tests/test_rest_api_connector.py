"""
Tests for REST API Connector with all pagination strategies.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json
from backend.connectors.rest_api import (
    RESTAPIConnector,
    AuthType,
    PaginationType,
    RESTAPIError,
    rest_api_source,
)


class TestRESTAPIConnectorPagination:
    """Test all pagination strategies."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock requests session."""
        with patch("backend.connectors.rest_api.requests.Session") as mock:
            session = Mock()
            mock.return_value = session
            yield session

    def test_page_pagination(self, mock_session):
        """Test PAGE pagination strategy."""
        # Setup mock responses
        responses = [
            {"data": [{"id": 1}, {"id": 2}]},
            {"data": [{"id": 3}, {"id": 4}]},
            {"data": []},  # Empty response signals end
        ]

        mock_response = Mock()
        mock_response.json.side_effect = responses
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            pagination_type="page",
            pagination_config={
                "page_param": "page",
                "size_param": "page_size",
                "page_size": 2,
            },
        )

        items = list(connector.fetch_data("/users"))

        assert len(items) == 4
        assert items[0]["id"] == 1
        assert items[3]["id"] == 4
        assert all("_dlt_load_time" in item for item in items)

        # Verify pagination parameters were set correctly
        calls = mock_session.request.call_args_list
        assert calls[0][1]["params"]["page"] == 1
        assert calls[1][1]["params"]["page"] == 2

    def test_offset_pagination(self, mock_session):
        """Test OFFSET pagination strategy."""
        responses = [
            {"results": [{"id": 1}, {"id": 2}, {"id": 3}]},
            {"results": [{"id": 4}, {"id": 5}]},  # Less than limit, signals end
        ]

        mock_response = Mock()
        mock_response.json.side_effect = responses
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            pagination_type="offset",
            pagination_config={
                "offset_param": "offset",
                "limit_param": "limit",
                "limit": 3,
            },
        )

        items = list(connector.fetch_data("/users", data_path="results"))

        assert len(items) == 5
        assert items[0]["id"] == 1
        assert items[4]["id"] == 5

        # Verify pagination parameters
        calls = mock_session.request.call_args_list
        assert calls[0][1]["params"]["offset"] == 0
        assert calls[1][1]["params"]["offset"] == 3

    def test_cursor_pagination(self, mock_session):
        """Test CURSOR pagination strategy."""
        responses = [
            {"data": [{"id": 1}, {"id": 2}], "pagination": {"next_cursor": "abc123"}},
            {"data": [{"id": 3}, {"id": 4}], "pagination": {"next_cursor": "def456"}},
            {"data": [{"id": 5}], "pagination": {"next_cursor": None}},
        ]

        mock_response = Mock()
        mock_response.json.side_effect = responses
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            pagination_type="cursor",
            pagination_config={
                "cursor_path": "pagination.next_cursor",
                "cursor_param": "cursor",
            },
        )

        items = list(connector.fetch_data("/users"))

        assert len(items) == 5

        # Verify cursor was passed correctly
        calls = mock_session.request.call_args_list
        assert "cursor" not in calls[0][1]["params"]  # First call has no cursor
        assert calls[1][1]["params"]["cursor"] == "abc123"
        assert calls[2][1]["params"]["cursor"] == "def456"

    def test_link_header_pagination(self, mock_session):
        """Test LINK_HEADER pagination strategy."""
        responses = [
            {"data": [{"id": 1}, {"id": 2}]},
            {"data": [{"id": 3}, {"id": 4}]},
            {"data": [{"id": 5}]},
        ]

        headers_sequence = [
            {"Link": '<https://api.example.com/users?page=2>; rel="next"'},
            {"Link": '<https://api.example.com/users?page=3>; rel="next"'},
            {"Link": ""},  # No next link
        ]

        mock_responses = []
        for resp_data, headers in zip(responses, headers_sequence):
            mock_resp = Mock()
            mock_resp.json.return_value = resp_data
            mock_resp.headers = headers
            mock_resp.raise_for_status = Mock()
            mock_responses.append(mock_resp)

        mock_session.request.side_effect = mock_responses

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            pagination_type="link_header",
        )

        items = list(connector.fetch_data("/users"))

        assert len(items) == 5
        assert items[0]["id"] == 1
        assert items[4]["id"] == 5

    def test_token_pagination(self, mock_session):
        """Test TOKEN pagination strategy."""
        responses = [
            {"items": [{"id": 1}], "next_page_token": "token1"},
            {"items": [{"id": 2}], "next_page_token": "token2"},
            {"items": [{"id": 3}], "next_page_token": None},
        ]

        mock_response = Mock()
        mock_response.json.side_effect = responses
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            pagination_type="token",
            pagination_config={
                "token_path": "next_page_token",
                "token_param": "pageToken",
            },
        )

        items = list(connector.fetch_data("/users"))

        assert len(items) == 3

        calls = mock_session.request.call_args_list
        assert "pageToken" not in calls[0][1]["params"]
        assert calls[1][1]["params"]["pageToken"] == "token1"

    def test_next_url_pagination(self, mock_session):
        """Test NEXT_URL pagination strategy."""
        responses = [
            {
                "data": [{"id": 1}, {"id": 2}],
                "next": "https://api.example.com/users?page=2"
            },
            {
                "data": [{"id": 3}],
                "next": None
            },
        ]

        mock_response = Mock()
        mock_response.json.side_effect = responses
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            pagination_type="next_url",
            pagination_config={
                "next_url_path": "next",
            },
        )

        items = list(connector.fetch_data("/users"))

        assert len(items) == 3

    def test_no_pagination(self, mock_session):
        """Test NONE pagination (single request)."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": [{"id": 1}, {"id": 2}, {"id": 3}]}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            pagination_type="none",
        )

        items = list(connector.fetch_data("/users"))

        assert len(items) == 3
        assert mock_session.request.call_count == 1


class TestRESTAPIConnectorAuth:
    """Test authentication methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock requests session."""
        with patch("backend.connectors.rest_api.requests.Session") as mock:
            session = Mock()
            mock.return_value = session
            yield session

    def test_api_key_auth(self, mock_session):
        """Test API key authentication."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            auth_type="api_key",
            auth_config={
                "api_key": "secret123",
                "header_name": "X-API-Key",
            },
        )

        list(connector.fetch_data("/users"))

        call_args = mock_session.request.call_args
        assert call_args[1]["headers"]["X-API-Key"] == "secret123"

    def test_bearer_auth(self, mock_session):
        """Test Bearer token authentication."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            auth_type="bearer",
            auth_config={"token": "bearer_token_123"},
        )

        list(connector.fetch_data("/users"))

        call_args = mock_session.request.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer bearer_token_123"

    def test_basic_auth(self, mock_session):
        """Test Basic authentication."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        connector = RESTAPIConnector(
            base_url="https://api.example.com",
            auth_type="basic",
            auth_config={
                "username": "user",
                "password": "pass",
            },
        )

        list(connector.fetch_data("/users"))

        call_args = mock_session.request.call_args
        assert call_args[1]["auth"] == ("user", "pass")


class TestRESTAPIConnectorValidation:
    """Test configuration validation."""

    def test_pagination_config_validation_page(self):
        """Test PAGE pagination config validation."""
        with pytest.raises(RESTAPIError, match="page_size must be a positive integer"):
            RESTAPIConnector(
                base_url="https://api.example.com",
                pagination_type="page",
                pagination_config={"page_size": -1},
            )

    def test_pagination_config_validation_offset(self):
        """Test OFFSET pagination config validation."""
        with pytest.raises(RESTAPIError, match="limit must be a positive integer"):
            RESTAPIConnector(
                base_url="https://api.example.com",
                pagination_type="offset",
                pagination_config={"limit": 0},
            )

    def test_data_path_extraction(self):
        """Test nested data path extraction."""
        with patch("backend.connectors.rest_api.requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.json.return_value = {
                "response": {
                    "items": [{"id": 1}, {"id": 2}]
                }
            }
            mock_response.headers = {}
            mock_session.request.return_value = mock_response

            connector = RESTAPIConnector(
                base_url="https://api.example.com",
            )

            items = list(connector.fetch_data("/users", data_path="response.items"))

            assert len(items) == 2
            assert items[0]["id"] == 1


class TestRESTAPIConnectorRateLimit:
    """Test rate limiting."""

    @patch("backend.connectors.rest_api.time.sleep")
    @patch("backend.connectors.rest_api.time.time")
    def test_rate_limiting(self, mock_time, mock_sleep):
        """Test that rate limiting works correctly."""
        # Mock time to simulate rapid requests
        mock_time.side_effect = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

        with patch("backend.connectors.rest_api.requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.json.return_value = {"data": [{"id": 1}]}
            mock_response.headers = {}
            mock_session.request.return_value = mock_response

            connector = RESTAPIConnector(
                base_url="https://api.example.com",
                rate_limit=3,  # 3 requests per minute
            )

            # Make 4 requests - 4th should trigger rate limit
            for _ in range(4):
                list(connector.fetch_data("/users"))

            # Sleep should be called when rate limit is hit
            assert mock_sleep.called


class TestRESTAPISource:
    """Test dlt source creation."""

    def test_rest_api_source_creation(self):
        """Test creating REST API source with multiple endpoints."""
        endpoints = [
            {
                "name": "users",
                "path": "/api/users",
                "data_path": "data",
                "primary_key": "id",
            },
            {
                "name": "orders",
                "path": "/api/orders",
                "data_path": "results",
                "primary_key": "order_id",
                "write_disposition": "merge",
            },
        ]

        source = rest_api_source(
            base_url="https://api.example.com",
            endpoints=endpoints,
            auth_type="bearer",
            auth_config={"token": "test_token"},
            pagination_type="page",
            pagination_config={"page_size": 50},
        )

        assert len(source) == 2
        assert source[0].name == "users"
        assert source[1].name == "orders"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
