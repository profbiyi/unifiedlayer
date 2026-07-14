"""Tests for African payment connectors and MongoDB connector."""
from unittest.mock import MagicMock, patch


from backend.connectors.sdk.base import AuthType


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


# ---------------------------------------------------------------------------
# Mono (African open banking)
# ---------------------------------------------------------------------------

class TestMonoMetadata:
    def test_mono_metadata(self):
        from backend.connectors.mono import MonoConnector

        meta = MonoConnector.metadata
        assert meta.name == "mono"
        assert meta.category == "banking"
        assert "transactions" in meta.supported_tables
        assert "accounts" in meta.supported_tables
        assert "identity" in meta.supported_tables
        assert AuthType.API_KEY in meta.capabilities.auth_types


class TestMonoConfigSchema:
    def test_mono_config_schema(self):
        from backend.connectors.mono import MonoConnector

        connector = MonoConnector.__new__(MonoConnector)
        schema = connector.get_config_schema()
        assert "secret_key" in schema["properties"]
        assert "secret_key" in schema["required"]
        assert "account_ids" in schema["properties"]
        assert "account_ids" not in schema["required"]


class TestMonoSetup:
    def test_account_ids_parsed_from_comma_separated_string(self):
        from backend.connectors.mono import MonoConnector

        connector = MonoConnector.__new__(MonoConnector)
        connector.config = _make_config(secret_key="sk_test", account_ids="acc_1, acc_2 ,acc_3")
        connector.setup()
        assert connector.account_ids == ["acc_1", "acc_2", "acc_3"]

    def test_empty_account_ids_means_all(self):
        from backend.connectors.mono import MonoConnector

        connector = MonoConnector.__new__(MonoConnector)
        connector.config = _make_config(secret_key="sk_test")
        connector.setup()
        assert connector.account_ids == []


class TestMonoTestConnection:
    def test_mono_test_connection_with_account(self):
        from backend.connectors.mono import MonoConnector

        connector = MonoConnector.__new__(MonoConnector)
        connector.config = _make_config(secret_key="sk_test", account_ids="acc_123")
        connector.setup()

        with patch.object(connector, "_request") as mock_req:
            mock_req.return_value = {"status": "successful", "data": {"account": {"id": "acc_123"}}}
            result = connector.test_connection()

        assert result["success"] is True
        assert "acc_123" in result["message"]

    def test_mono_test_connection_lists_accounts(self):
        from backend.connectors.mono import MonoConnector

        connector = MonoConnector.__new__(MonoConnector)
        connector.config = _make_config(secret_key="sk_test")
        connector.setup()

        with patch.object(connector, "_request") as mock_req:
            mock_req.return_value = {
                "status": "successful",
                "data": [{"account": {"id": "acc_1"}}, {"account": {"id": "acc_2"}}],
            }
            result = connector.test_connection()

        assert result["success"] is True
        assert "2 linked account" in result["message"]

    def test_mono_test_connection_failure(self):
        from backend.connectors.mono import MonoConnector, MonoAPIError

        connector = MonoConnector.__new__(MonoConnector)
        connector.config = _make_config(secret_key="sk_bad", account_ids="acc_123")
        connector.setup()

        with patch.object(connector, "_request") as mock_req:
            mock_req.side_effect = MonoAPIError("Mono API error 401: invalid key")
            result = connector.test_connection()

        assert result["success"] is False
        assert "401" in result["message"]


class TestMonoExtract:
    def test_extract_transactions_paginates_and_tags_account(self):
        from backend.connectors.mono import MonoConnector

        connector = MonoConnector.__new__(MonoConnector)
        connector.config = _make_config(secret_key="sk_test", account_ids="acc_1")
        connector.setup()

        pages = [
            {
                "status": "successful",
                "data": [{"id": "txn_1", "amount": 5000}, {"id": "txn_2", "amount": 1200}],
                "meta": {"pages": 2},
            },
            {
                "status": "successful",
                "data": [{"id": "txn_3", "amount": 800}],
                "meta": {"pages": 2},
            },
        ]

        with patch.object(connector, "_request") as mock_req:
            mock_req.side_effect = pages
            records = list(connector.extract(tables=["transactions"]))

        assert [r["id"] for r in records] == ["txn_1", "txn_2", "txn_3"]
        assert all(r["account_id"] == "acc_1" for r in records)

    def test_extract_unknown_table_raises(self):
        from backend.connectors.mono import MonoConnector

        connector = MonoConnector.__new__(MonoConnector)
        connector.config = _make_config(secret_key="sk_test", account_ids="acc_1")
        connector.setup()

        try:
            list(connector.extract(tables=["loans"]))
            assert False, "expected ValueError"
        except ValueError as e:
            assert "loans" in str(e)
