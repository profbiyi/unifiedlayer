"""
Tests for backfill orchestration + the Postgres ranged-extraction helpers.

The live end-to-end (real Postgres slice -> destination) is exercised separately;
here we cover identifier quoting (injection-safety), strategy inference, chunk
fan-out counting, and JSON-safe bound serialization — all without a DB.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import backend.tasks.backfill_tasks as bt
from backend.services.backfill_extract import _qident, _split_table


def test_qident_escapes_embedded_quotes():
    assert _qident("created_at") == '"created_at"'
    # a name trying to break out is neutralised by doubling the quote
    assert _qident('x"; DROP TABLE y;--') == '"x""; DROP TABLE y;--"'


def test_split_table_defaults_to_public():
    assert _split_table("events") == ("public", "events")
    assert _split_table("analytics.events") == ("analytics", "events")


def test_serialize_bound_is_json_safe():
    dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert bt._serialize_bound(dt) == dt.isoformat()
    assert bt._serialize_bound(42) == 42


def _ctx():
    return {
        "source_type": "postgres",
        "source_config": {"host": "h", "database": "d", "user": "u", "password": "p"},
        "dest_type": "duckdb",
        "dest_config": {"database_path": "/tmp/x.duckdb"},
        "pipeline_name": "p",
    }


def test_plan_and_dispatch_key_strategy_fans_out_chunks():
    with patch.object(bt, "_pipeline_context", return_value=_ctx()), patch(
        "backend.services.backfill_extract.get_range_bounds", return_value=(1, 10, 10)
    ), patch.object(bt.run_backfill_chunk, "delay") as delay:
        out = bt.plan_and_dispatch_backfill(1, "public.events", "id", chunk_size=4)

    assert out["strategy"] == "key"
    assert out["chunks"] == 3  # [1,5),[5,9),[9,11)
    assert out["dispatched"] == 3
    assert delay.call_count == 3
    # bounds passed to the task are plain ints (JSON-safe)
    first = delay.call_args_list[0].args
    assert first[0] == 1 and first[1] == "public.events" and first[2] == "id"
    assert first[3] == 1 and first[4] == 5


def test_plan_and_dispatch_infers_time_strategy_from_timestamp_bounds():
    lo = datetime(2020, 1, 1, tzinfo=timezone.utc)
    hi = datetime(2020, 1, 20, tzinfo=timezone.utc)
    with patch.object(bt, "_pipeline_context", return_value=_ctx()), patch(
        "backend.services.backfill_extract.get_range_bounds", return_value=(lo, hi, 100)
    ), patch.object(bt.run_backfill_chunk, "delay") as delay:
        out = bt.plan_and_dispatch_backfill(1, "events", "created_at", window_days=10)

    assert out["strategy"] == "time"
    assert out["dispatched"] == delay.call_count
    assert delay.call_count >= 2
    # time bounds are serialized to ISO strings
    assert isinstance(delay.call_args_list[0].args[3], str)


def test_plan_and_dispatch_empty_table_dispatches_nothing():
    with patch.object(bt, "_pipeline_context", return_value=_ctx()), patch(
        "backend.services.backfill_extract.get_range_bounds", return_value=(None, None, 0)
    ), patch.object(bt.run_backfill_chunk, "delay") as delay:
        out = bt.plan_and_dispatch_backfill(1, "events", "id")

    assert out["chunks"] == 0 and out["dispatched"] == 0
    delay.assert_not_called()


def test_non_postgres_source_raises():
    ctx = _ctx()
    ctx["source_type"] = "stripe"
    with patch.object(bt, "_pipeline_context", return_value=ctx):
        try:
            bt.plan_and_dispatch_backfill(1, "events", "id")
            assert False, "expected NotImplementedError"
        except NotImplementedError:
            pass
