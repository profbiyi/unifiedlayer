"""
Tests for _selected_table_names — normalizing the wizard's `tables` config into
the flat list of bare names the API connectors expect.
"""
from backend.prefect_flows.pipeline_flow import _selected_table_names


def test_wizard_dicts_to_bare_names():
    tables = [
        {"table": "stripe.customers", "sync_mode": "full_refresh"},
        {"table": "stripe.charges", "sync_mode": "full_refresh"},
    ]
    assert _selected_table_names(tables) == ["customers", "charges"]


def test_plain_name_strings_pass_through():
    assert _selected_table_names(["customers", "charges"]) == ["customers", "charges"]


def test_strips_prefix_on_string_entries():
    assert _selected_table_names(["stripe.customers"]) == ["customers"]


def test_name_key_variant():
    assert _selected_table_names([{"name": "stripe.invoices"}]) == ["invoices"]


def test_empty_or_none_returns_none():
    assert _selected_table_names([]) is None
    assert _selected_table_names(None) is None
