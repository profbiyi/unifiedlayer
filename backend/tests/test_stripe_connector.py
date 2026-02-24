"""Tests for Stripe payment connector."""
from unittest.mock import MagicMock, patch

import pytest

from backend.connectors.sdk.base import AuthType, PaginationType


def _make_config(**creds):
    """Helper to create mock config."""
    config = MagicMock()
    config.credentials = creds
    config.get.side_effect = lambda key, default=None: creds.get(key, default)
    config.require.side_effect = lambda key: creds[key]
    return config


class TestStripeMetadata:
    def test_stripe_metadata(self):
        from backend.connectors.stripe_connector import StripeSDKConnector

        meta = StripeSDKConnector.metadata
        assert meta.name == "stripe"
        assert meta.display_name == "Stripe"
        assert meta.category == "payment"
        assert "charges" in meta.supported_tables
        assert "customers" in meta.supported_tables
        assert "invoices" in meta.supported_tables
        assert "subscriptions" in meta.supported_tables
        assert AuthType.BEARER in meta.capabilities.auth_types
        assert meta.capabilities.pagination_type == PaginationType.CURSOR


class TestStripeConfigSchema:
    def test_stripe_config_schema(self):
        from backend.connectors.stripe_connector import StripeSDKConnector

        connector = StripeSDKConnector.__new__(StripeSDKConnector)
        schema = connector.get_config_schema()
        assert "api_key" in schema["properties"]
        assert "api_key" in schema["required"]
        assert schema["properties"]["api_key"]["secret"] is True


class TestStripeTestConnection:
    def test_stripe_test_connection_success(self):
        from backend.connectors.stripe_connector import StripeSDKConnector

        connector = StripeSDKConnector.__new__(StripeSDKConnector)
        connector.config = _make_config(api_key="sk_test_123")
        connector.setup()

        with patch.object(connector._connector, "_make_request") as mock_req:
            mock_req.return_value = {
                "available": [{"amount": 10000, "currency": "gbp"}],
                "pending": [{"amount": 5000, "currency": "gbp"}],
            }
            result = connector.test_connection()

        assert result["success"] is True
        assert "GBP" in result["message"]

    def test_stripe_test_connection_failure(self):
        from backend.connectors.stripe_connector import StripeSDKConnector, StripeAPIError

        connector = StripeSDKConnector.__new__(StripeSDKConnector)
        connector.config = _make_config(api_key="sk_test_invalid")
        connector.setup()

        with patch.object(connector._connector, "_make_request") as mock_req:
            mock_req.side_effect = StripeAPIError("Invalid API key")
            result = connector.test_connection()

        assert result["success"] is False
        assert "Invalid API key" in result["message"]


class TestStripeExtract:
    def test_stripe_extract_charges(self):
        from backend.connectors.stripe_connector import StripeSDKConnector

        connector = StripeSDKConnector.__new__(StripeSDKConnector)
        connector.config = _make_config(api_key="sk_test_123")
        connector.setup()

        mock_charges = [
            {"id": "ch_1", "amount": 1000, "currency": "gbp"},
            {"id": "ch_2", "amount": 2000, "currency": "gbp"},
        ]

        with patch.object(connector._connector, "_paginate") as mock_paginate:
            mock_paginate.return_value = iter(mock_charges)
            charges = list(connector.extract("charges"))

        assert len(charges) == 2
        assert charges[0]["id"] == "ch_1"
        mock_paginate.assert_called_once_with("/charges")

    def test_stripe_extract_customers(self):
        from backend.connectors.stripe_connector import StripeSDKConnector

        connector = StripeSDKConnector.__new__(StripeSDKConnector)
        connector.config = _make_config(api_key="sk_test_123")
        connector.setup()

        mock_customers = [
            {"id": "cus_1", "email": "test@example.com"},
        ]

        with patch.object(connector._connector, "_paginate") as mock_paginate:
            mock_paginate.return_value = iter(mock_customers)
            customers = list(connector.extract("customers"))

        assert len(customers) == 1
        assert customers[0]["email"] == "test@example.com"

    def test_stripe_extract_invalid_table(self):
        from backend.connectors.stripe_connector import StripeSDKConnector

        connector = StripeSDKConnector.__new__(StripeSDKConnector)
        connector.config = _make_config(api_key="sk_test_123")
        connector.setup()

        with pytest.raises(ValueError, match="Unknown table"):
            list(connector.extract("invalid_table"))


class TestStripePagination:
    def test_stripe_pagination(self):
        from backend.connectors.stripe_connector import StripeConnector

        connector = StripeConnector(api_key="sk_test_123")

        # Mock responses for two pages
        page1 = {
            "data": [{"id": "ch_1"}, {"id": "ch_2"}],
            "has_more": True,
        }
        page2 = {
            "data": [{"id": "ch_3"}],
            "has_more": False,
        }

        with patch.object(connector, "_make_request") as mock_req:
            mock_req.side_effect = [page1, page2]
            results = list(connector._paginate("/charges"))

        assert len(results) == 3
        assert results[0]["id"] == "ch_1"
        assert results[2]["id"] == "ch_3"

        # Verify pagination params
        calls = mock_req.call_args_list
        assert calls[0][1]["params"]["limit"] == 100
        assert calls[1][1]["params"]["starting_after"] == "ch_2"


class TestStripeRateLimiting:
    def test_stripe_rate_limit_tracking(self):
        from backend.connectors.stripe_connector import StripeConnector

        connector = StripeConnector(api_key="sk_test_123")

        # Initially no requests tracked
        assert len(connector.request_times) == 0

        # After rate limit check, time is recorded
        connector._check_rate_limit()
        assert len(connector.request_times) == 1


class TestStripeSource:
    def test_stripe_source_returns_resources(self):
        from backend.connectors.stripe_connector import stripe_source

        with patch("backend.connectors.stripe_connector.StripeConnector") as MockConnector:
            mock_instance = MagicMock()
            MockConnector.return_value = mock_instance

            resources = stripe_source(api_key="sk_test_123")

        # Should return 8 resources (all tables)
        assert len(resources) == 8

    def test_stripe_source_with_table_filter(self):
        from backend.connectors.stripe_connector import stripe_source

        with patch("backend.connectors.stripe_connector.StripeConnector") as MockConnector:
            mock_instance = MagicMock()
            MockConnector.return_value = mock_instance

            resources = stripe_source(
                api_key="sk_test_123",
                tables=["charges", "customers"]
            )

        # Should return only 2 resources
        assert len(resources) == 2
