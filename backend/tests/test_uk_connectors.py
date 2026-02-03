"""
Tests for UK connectors (GoCardless, Xero, Open Banking, HMRC MTD).
"""
import pytest
from unittest.mock import patch, MagicMock
import json

from backend.connectors.gocardless import GoCardlessConnector
from backend.connectors.xero import XeroConnector
from backend.connectors.open_banking import OpenBankingConnector
from backend.connectors.hmrc_mtd import HMRCMTDConnector


# ── GoCardless ──────────────────────────────────────────────────────

class TestGoCardlessConnector:
    def _make_connector(self, **overrides):
        config = {"access_token": "sandbox_test_token", "environment": "sandbox"}
        config.update(overrides)
        return GoCardlessConnector(config)

    def test_metadata(self):
        c = self._make_connector()
        meta = c.get_metadata()
        assert meta.name == "gocardless"
        assert "payments" in meta.supported_tables

    def test_config_schema(self):
        c = self._make_connector()
        schema = c.get_config_schema()
        assert "access_token" in schema["required"]
        assert "environment" in schema["properties"]

    @patch("backend.connectors.gocardless.requests.get")
    def test_test_connection_success(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"creditors": [{"id": "CR123"}]})
        c = self._make_connector()
        result = c.test_connection()
        assert result["success"] is True

    @patch("backend.connectors.gocardless.requests.get")
    def test_test_connection_failure(self, mock_get):
        mock_get.return_value = MagicMock(status_code=401, text="Unauthorized")
        c = self._make_connector()
        result = c.test_connection()
        assert result["success"] is False

    def test_discover_schema(self):
        c = self._make_connector()
        schema = c.discover_schema()
        assert "payments" in schema
        assert "id" in schema["payments"]

    @patch("backend.connectors.gocardless.requests.get")
    def test_extract_payments(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "payments": [
                    {"id": "PM001", "amount": 1000, "currency": "GBP", "status": "confirmed", "links": {"mandate": "MD001"}},
                ],
                "meta": {"cursors": {"after": None}, "limit": 50},
            },
        )
        c = self._make_connector()
        rows = list(c.extract("payments"))
        assert len(rows) == 1
        assert rows[0]["id"] == "PM001"
        assert rows[0]["mandate_id"] == "MD001"

    def test_to_dlt_resource(self):
        c = self._make_connector()
        resource = c.to_dlt_resource(table_name="payments")
        assert resource is not None


# ── Xero ────────────────────────────────────────────────────────────

class TestXeroConnector:
    def _make_connector(self, **overrides):
        config = {
            "access_token": "test_xero_token",
            "tenant_id": "test-tenant-id",
            "client_id": "xero_client",
            "client_secret": "xero_secret",
            "refresh_token": "xero_refresh",
        }
        config.update(overrides)
        return XeroConnector(config)

    def test_metadata(self):
        c = self._make_connector()
        meta = c.get_metadata()
        assert meta.name == "xero"
        assert "invoices" in meta.supported_tables

    def test_config_schema(self):
        c = self._make_connector()
        schema = c.get_config_schema()
        assert "access_token" in schema["required"]
        assert "tenant_id" in schema["required"]

    @patch("backend.connectors.xero.requests.get")
    def test_test_connection_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"Organisations": [{"Name": "Test Org"}]},
        )
        c = self._make_connector()
        result = c.test_connection()
        assert result["success"] is True

    def test_discover_schema(self):
        c = self._make_connector()
        schema = c.discover_schema()
        assert "invoices" in schema
        assert "contacts" in schema

    @patch("backend.connectors.xero.requests.get")
    def test_extract_invoices(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "Invoices": [
                    {"InvoiceID": "INV001", "Type": "ACCREC", "Total": 500.00, "Status": "AUTHORISED"},
                ],
            },
        )
        c = self._make_connector()
        rows = list(c.extract("invoices"))
        assert len(rows) == 1
        assert rows[0]["InvoiceID"] == "INV001"


# ── Open Banking ────────────────────────────────────────────────────

class TestOpenBankingConnector:
    def _make_connector(self, **overrides):
        config = {
            "access_token": "test_truelayer_token",
            "client_id": "tl_client",
            "client_secret": "tl_secret",
            "refresh_token": "tl_refresh",
        }
        config.update(overrides)
        return OpenBankingConnector(config)

    def test_metadata(self):
        c = self._make_connector()
        meta = c.get_metadata()
        assert meta.name == "open_banking"
        assert "transactions" in meta.supported_tables

    def test_config_schema(self):
        c = self._make_connector()
        schema = c.get_config_schema()
        assert "access_token" in schema["required"]

    @patch("backend.connectors.open_banking.requests.get")
    def test_test_connection_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"results": [{"account_id": "acc123"}]},
        )
        c = self._make_connector()
        result = c.test_connection()
        assert result["success"] is True

    def test_discover_schema(self):
        c = self._make_connector()
        schema = c.discover_schema()
        assert "accounts" in schema
        assert "transactions" in schema

    @patch("backend.connectors.open_banking.requests.get")
    def test_extract_accounts(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "results": [
                    {"account_id": "acc001", "display_name": "Current Account", "currency": "GBP"},
                ],
            },
        )
        c = self._make_connector()
        rows = list(c.extract("accounts"))
        assert len(rows) == 1
        assert rows[0]["account_id"] == "acc001"


# ── HMRC MTD ────────────────────────────────────────────────────────

class TestHMRCMTDConnector:
    def _make_connector(self, **overrides):
        config = {
            "access_token": "test_hmrc_token",
            "vrn": "123456789",
            "client_id": "hmrc_client",
            "client_secret": "hmrc_secret",
            "refresh_token": "hmrc_refresh",
        }
        config.update(overrides)
        return HMRCMTDConnector(config)

    def test_metadata(self):
        c = self._make_connector()
        meta = c.get_metadata()
        assert meta.name == "hmrc_mtd"
        assert "vat_obligations" in meta.supported_tables

    def test_config_schema(self):
        c = self._make_connector()
        schema = c.get_config_schema()
        assert "access_token" in schema["required"]
        assert "vrn" in schema["required"]

    @patch("backend.connectors.hmrc_mtd.requests.get")
    def test_test_connection_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"obligations": [{"periodKey": "#001"}]},
        )
        c = self._make_connector()
        result = c.test_connection()
        assert result["success"] is True

    def test_discover_schema(self):
        c = self._make_connector()
        schema = c.discover_schema()
        assert "vat_obligations" in schema
        assert "vat_returns" in schema

    @patch("backend.connectors.hmrc_mtd.requests.get")
    def test_extract_vat_obligations(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "obligations": [
                    {"periodKey": "#001", "start": "2025-01-01", "end": "2025-03-31", "status": "F", "due": "2025-05-07"},
                ],
            },
        )
        c = self._make_connector()
        rows = list(c.extract("vat_obligations"))
        assert len(rows) == 1
        assert rows[0]["periodKey"] == "#001"
