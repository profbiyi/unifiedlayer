"""
Tests for backfill chunk planning (pure, no I/O).

Chunks must tile [start, end) with no overlap and no gaps, so a parallel
backfill loads every row exactly once.
"""
from datetime import datetime, timedelta, timezone

import pytest

from backend.services.backfill_planner import (
    choose_partition_column,
    plan_key_chunks,
    plan_time_chunks,
)


def test_time_chunks_tile_range_without_gaps_or_overlap():
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2020, 1, 10, tzinfo=timezone.utc)
    plan = plan_time_chunks("created_at", start, end, timedelta(days=3))

    assert plan.kind == "time"
    assert plan.chunk_count == 3  # 3+3+3 then clamp -> [1-4),[4-7),[7-10)
    # contiguous: each chunk's end == next chunk's start
    for a, b in zip(plan.chunks, plan.chunks[1:]):
        assert a.end == b.start
    # covers the whole range exactly
    assert plan.chunks[0].start == start
    assert plan.chunks[-1].end == end


def test_time_chunks_final_window_clamped_to_end():
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2020, 1, 8, tzinfo=timezone.utc)  # 7 days, window 3 -> 3+3+1
    plan = plan_time_chunks("created_at", start, end, timedelta(days=3))
    assert plan.chunk_count == 3
    assert plan.chunks[-1].start == datetime(2020, 1, 7, tzinfo=timezone.utc)
    assert plan.chunks[-1].end == end


def test_time_chunks_reject_bad_input():
    s = datetime(2020, 1, 2, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        plan_time_chunks("c", s, s - timedelta(days=1), timedelta(days=1))
    with pytest.raises(ValueError):
        plan_time_chunks("c", s, s + timedelta(days=1), timedelta(0))


def test_time_chunks_respect_max_chunks_guardrail():
    s = datetime(2020, 1, 1, tzinfo=timezone.utc)
    e = datetime(2030, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        plan_time_chunks("c", s, e, timedelta(days=1), max_chunks=100)


def test_key_chunks_tile_inclusive_range_as_half_open():
    plan = plan_key_chunks("id", 1, 10, 4)  # [1,5),[5,9),[9,11)
    assert plan.kind == "key"
    assert [(c.start, c.end) for c in plan.chunks] == [(1, 5), (5, 9), (9, 11)]
    # exclusive end past max_key so row id=10 is included
    assert plan.chunks[-1].end == 11
    for a, b in zip(plan.chunks, plan.chunks[1:]):
        assert a.end == b.start


def test_key_chunks_single_chunk_when_small():
    plan = plan_key_chunks("id", 1, 3, 100)
    assert plan.chunk_count == 1
    assert (plan.chunks[0].start, plan.chunks[0].end) == (1, 4)


def test_key_chunks_reject_bad_input():
    with pytest.raises(ValueError):
        plan_key_chunks("id", 1, 10, 0)
    with pytest.raises(ValueError):
        plan_key_chunks("id", 10, 1, 5)


def test_choose_partition_column_prefers_timestamp():
    cols = [
        {"name": "id", "type": "integer"},
        {"name": "created_at", "type": "timestamp with time zone"},
        {"name": "name", "type": "varchar"},
    ]
    choice = choose_partition_column(cols)
    assert choice == {"name": "created_at", "strategy": "time"}


def test_choose_partition_column_falls_back_to_integer_id():
    cols = [
        {"name": "id", "type": "bigint"},
        {"name": "name", "type": "text"},
    ]
    choice = choose_partition_column(cols)
    assert choice == {"name": "id", "strategy": "key"}


def test_choose_partition_column_none_when_unsuitable():
    cols = [
        {"name": "name", "type": "text"},
        {"name": "email", "type": "varchar"},
    ]
    assert choose_partition_column(cols) is None
