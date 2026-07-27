"""
Tests for the connection-tester registry fallback.

`test_connection()` has hand-written testers for a handful of source types; for
the rest it now dispatches to the connector's own `test_connection()` via the
ConnectorRegistry. These tests verify that dispatch + return normalization
(dict / bool / exception) without needing real provider credentials.
"""
from unittest.mock import MagicMock

import backend.connectors.sdk.registry as reg
# Aliased so pytest doesn't collect the imported function as a test case.
from backend.utils.connection_tester import test_connection as run_connection_test


def _patch_registry(monkeypatch, *, found: bool, connector=None):
    """Point ConnectorRegistry.get/instantiate at a fake connector (or nothing)."""
    monkeypatch.setattr(
        reg.ConnectorRegistry,
        "get",
        classmethod(lambda cls, name: (object if found else None)),
    )
    if connector is not None:
        monkeypatch.setattr(
            reg.ConnectorRegistry,
            "instantiate",
            classmethod(lambda cls, name, config: connector),
        )


def test_registry_dispatch_dict_success(monkeypatch):
    fake = MagicMock()
    fake.test_connection.return_value = {"success": True, "message": "Connected to Stripe"}
    _patch_registry(monkeypatch, found=True, connector=fake)

    ok, msg = run_connection_test("stripe", {"api_key": "sk_test_x"})

    assert ok is True
    assert "Connected to Stripe" in msg
    fake.test_connection.assert_called_once()


def test_registry_dispatch_dict_failure(monkeypatch):
    fake = MagicMock()
    fake.test_connection.return_value = {"success": False, "message": "Invalid API key"}
    _patch_registry(monkeypatch, found=True, connector=fake)

    ok, msg = run_connection_test("paystack", {"secret_key": "sk_test_bad"})

    assert ok is False
    assert "Invalid API key" in msg


def test_registry_dispatch_bool_true(monkeypatch):
    fake = MagicMock()
    fake.test_connection.return_value = True
    _patch_registry(monkeypatch, found=True, connector=fake)

    ok, msg = run_connection_test("xero", {"access_token": "tok"})

    assert ok is True
    assert msg


def test_registry_dispatch_bool_false(monkeypatch):
    fake = MagicMock()
    fake.test_connection.return_value = False
    _patch_registry(monkeypatch, found=True, connector=fake)

    ok, _ = run_connection_test("gocardless", {"access_token": "bad"})

    assert ok is False


def test_registry_dispatch_exception_is_failure_not_crash(monkeypatch):
    fake = MagicMock()
    fake.test_connection.side_effect = RuntimeError("401 Unauthorized")
    _patch_registry(monkeypatch, found=True, connector=fake)

    ok, msg = run_connection_test("flutterwave", {"secret_key": "bad"})

    assert ok is False
    assert "401 Unauthorized" in msg


def test_unregistered_type_reports_not_verified(monkeypatch):
    # Not a registered connector and not a hand-written tester → neutral, honest.
    _patch_registry(monkeypatch, found=False)

    ok, msg = run_connection_test("salesforce", {"token": "x"})

    assert ok is True
    assert "not verified" in msg.lower()
