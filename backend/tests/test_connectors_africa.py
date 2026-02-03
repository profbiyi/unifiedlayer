"""Tests for African payment connectors and MongoDB connector."""
from unittest.mock import MagicMock, patch

import pytest

from backend.connectors.sdk.base import AuthType, PaginationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**creds):
    config = MagicMock()
    config.credentials = creds
    config.get.side_effect = lambda key, default=None: creds.get(key, default)
    config.require.side_effect = lambda key: creds[key]
    return config


# ---------------------------------------------------------------------------
# Flutterwave
# ---------------------------------------------------------------------------

class TestFlutterwaveMetadata:
    def test_flutterwave_metadata(self):
        from backend.connectors.flutterwave import FlutterwaveConnector

        meta = FlutterwaveConnector.metadata
        assert meta.name == "flutterwave"
        assert meta.category == "payment"
        assert "transactions" in meta.supported_tables
        assert AuthType.BEARER in meta.capabilities.auth_types


class TestFlutterwaveConfigSchema:
    def test_flutterwave_config_schema(self):
        from backend.connectors.flutterwave import FlutterwaveConnector

        connector = FlutterwaveConnector.__new__(FlutterwaveConnector)
        schema = connector.get_config_schema()
        assert "secret_key" in schema["properties"]
        assert "secret_key" in schema["required"]


class TestFlutterwaveTestConnection:
    def test_flutterwave_test_connection(self):
        from backend.connectors.flutterwave import FlutterwaveConnector

        connector = FlutterwaveConnector.__new__(FlutterwaveConnector)
        connector.config = _make_config(secret_key="FLWSECK-test")
        connector.setup()

        with patch.object(connector, "_request") as mock_req:
            mock_req.return_value = {"status": "success", "data": []}
            result = connector.test_connection()

        assert result["success"] is True
        assert "Connected" in result["message"]


# ---------------------------------------------------------------------------
# MTN MoMo
# ---------------------------------------------------------------------------

class TestMtnMomoMetadata:
    def test_mtn_momo_metadata(self):
        from backend.connectors.mtn_momo import MTNMoMoConnector

        meta = MTNMoMoConnector.metadata
        assert meta.name == "mtn_momo"
        assert meta.display_name == "MTN Mobile Money"
        assert meta.category == "payment"
        assert AuthType.OAUTH2 in meta.capabilities.auth_types


class TestMtnMomoTestConnection:
    def test_mtn_momo_test_connection(self):
        from backend.connectors.mtn_momo import MTNMoMoConnector

        connector = MTNMoMoConnector.__new__(MTNMoMoConnector)
        connector.config = _make_config(
            subscription_key="sub-key",
            api_user="user-id",
            api_key="api-key",
            environment="sandbox",
        )
        connector.setup()

        with patch.object(connector, "_get_token") as mock_token:
            mock_token.return_value = "fake-token"
            result = connector.test_connection()

        assert result["success"] is True
        assert "Connected" in result["message"]


# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------

class TestMongodbMetadata:
    def test_mongodb_metadata(self):
        from backend.connectors.mongodb import MongoDBConnector

        meta = MongoDBConnector.metadata
        assert meta.name == "mongodb"
        assert meta.category == "database"
        assert AuthType.BASIC in meta.capabilities.auth_types


class TestMongodbTestConnection:
    @patch("backend.connectors.mongodb.MongoClient")
    def test_mongodb_test_connection(self, mock_client_cls):
        from backend.connectors.mongodb import MongoDBConnector

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_db = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_db.list_collection_names.return_value = ["users", "orders"]

        connector = MongoDBConnector.__new__(MongoDBConnector)
        connector.config = _make_config(
            connection_string="mongodb://localhost:27017",
            database="testdb",
        )
        connector.setup()

        result = connector.test_connection()
        assert result["success"] is True
        assert "2 collection" in result["message"]
