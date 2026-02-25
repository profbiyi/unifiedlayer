"""
Tests for UK connectors (GoCardless, Xero, Open Banking, HMRC MTD).
"""
from unittest.mock import MagicMock

import pytest

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
        # metadata is a class attribute, not an instance method
        meta = GoCardlessConnector.metadata
        assert meta.name == "gocardless"
        assert meta.category == "payment"

    def test_config_schema(self):
        c = self._make_connector()
        schema = c.get_config_schema()
        # Returns flat dict: {"access_token": {"required": True, ...}, ...}
        assert "access_token" in schema
        assert schema["access_token"]["required"] is True
        assert "environment" in schema

    def test_test_connection_success(self):
        c = self._make_connector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"creditors": [{"id": "CR123"}]}
        c._session.get = MagicMock(return_value=mock_resp)
        result = c.test_connection()
        assert result is True

    def test_test_connection_failure(self):
        c = self._make_connector()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        c._session.get = MagicMock(return_value=mock_resp)
        with pytest.raises(ConnectionError):
            c.test_connection()

    def test_discover_schema(self):
        c = self._make_connector()
        schema = c.discover_schema()
        # Returns list of dicts with "name" key
        names = [t["name"] for t in schema]
        assert "payments" in names
        # Verify payments entry has an "id" column
        payments = next(t for t in schema if t["name"] == "payments")
        assert any(col["name"] == "id" for col in payments["columns"])

    def test_extract_payments(self):
        c = self._make_connector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "payments": [
                {
                    "id": "PM001",
                    "amount": 1000,
                    "currency": "GBP",
                    "status": "confirmed",
                    "links": {"mandate": "MD001"},
                },
            ],
            "meta": {"cursors": {"after": None}, "limit": 50},
        }
        c._session.get = MagicMock(return_value=mock_resp)
        # extract() takes tables as a list, not a string
        rows = list(c.extract(tables=["payments"]))
        assert len(rows) == 1
        assert rows[0]["id"] == "PM001"
        # _flatten_record converts links.mandate -> links_mandate (not mandate_id)
        assert rows[0]["links_mandate"] == "MD001"

    def test_to_dlt_resource(self):
        c = self._make_connector()
        # to_dlt_resource creates a lazy DltResource; extract is not called yet
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
        meta = XeroConnector.metadata
        assert meta.name == "xero"
        assert meta.category == "accounting"

    def test_config_schema(self):
        c = self._make_connector()
        schema = c.get_config_schema()
        assert "access_token" in schema
        assert schema["access_token"]["required"] is True
        assert "tenant_id" in schema
        assert schema["tenant_id"]["required"] is True

    def test_test_connection_success(self):
        c = self._make_connector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"Organisations": [{"Name": "Test Org"}]}
        c._session.get = MagicMock(return_value=mock_resp)
        result = c.test_connection()
        assert result is True

    def test_discover_schema(self):
        c = self._make_connector()
        schema = c.discover_schema()
        names = [t["name"] for t in schema]
        assert "invoices" in names
        assert "contacts" in names

    def test_extract_invoices(self):
        c = self._make_connector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "Invoices": [
                {"InvoiceID": "INV001", "Type": "ACCREC", "Total": 500.00, "Status": "AUTHORISED"},
            ],
        }
        mock_resp.raise_for_status = MagicMock()
        c._session.get = MagicMock(return_value=mock_resp)
        rows = list(c.extract(tables=["invoices"]))
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
        meta = OpenBankingConnector.metadata
        assert meta.name == "open_banking"
        assert meta.category == "banking"

    def test_config_schema(self):
        c = self._make_connector()
        schema = c.get_config_schema()
        assert "access_token" in schema
        assert schema["access_token"]["required"] is True

    def test_test_connection_success(self):
        c = self._make_connector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [{"account_id": "acc123"}]}
        c._session.get = MagicMock(return_value=mock_resp)
        result = c.test_connection()
        assert result is True

    def test_discover_schema(self):
        c = self._make_connector()
        schema = c.discover_schema()
        names = [t["name"] for t in schema]
        assert "accounts" in names
        assert "transactions" in names

    def test_extract_accounts(self):
        c = self._make_connector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {"account_id": "acc001", "display_name": "Current Account", "currency": "GBP"},
            ],
        }
        c._session.get = MagicMock(return_value=mock_resp)
        rows = list(c.extract(tables=["accounts"]))
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
        meta = HMRCMTDConnector.metadata
        assert meta.name == "hmrc_mtd"
        assert meta.category == "tax"

    def test_config_schema(self):
        c = self._make_connector()
        schema = c.get_config_schema()
        assert "access_token" in schema
        assert schema["access_token"]["required"] is True
        assert "vrn" in schema
        assert schema["vrn"]["required"] is True

    def test_test_connection_success(self):
        c = self._make_connector()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"obligations": [{"periodKey": "#001"}]}
        c._session.get = MagicMock(return_value=mock_resp)
        result = c.test_connection()
        assert result is True

    def test_discover_schema(self):
        c = self._make_connector()
        schema = c.discover_schema()
        names = [t["name"] for t in schema]
        assert "vat_obligations" in names
        assert "vat_returns" in names

    def test_extract_vat_obligations(self):
        # Use lookback_months=1 to produce a single date chunk (one API call)
        c = self._make_connector(lookback_months=1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "obligations": [
                {
                    "periodKey": "#001",
                    "start": "2025-01-01",
                    "end": "2025-03-31",
                    "status": "F",
                    "due": "2025-05-07",
                },
            ],
        }
        c._session.get = MagicMock(return_value=mock_resp)
        rows = list(c.extract(tables=["vat_obligations"]))
        assert len(rows) == 1
        assert rows[0]["periodKey"] == "#001"
