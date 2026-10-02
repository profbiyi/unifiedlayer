"""Tests for the timezone-safe datetime helpers."""
from datetime import datetime, timezone, timedelta

from backend.utils.datetimes import ensure_aware, utcnow


def test_ensure_aware_treats_naive_as_utc():
    naive = datetime(2026, 1, 1, 12, 0, 0)  # no tzinfo
    out = ensure_aware(naive)
    assert out.tzinfo is timezone.utc
    assert out == datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_ensure_aware_passes_through_aware():
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert ensure_aware(aware) is aware


def test_ensure_aware_none():
    assert ensure_aware(None) is None


def test_naive_vs_aware_comparison_would_raise_without_helper():
    # This is the exact failure mode the helper prevents (password reset / is_expired).
    naive = datetime(2026, 1, 1, tzinfo=None)
    aware = datetime.now(timezone.utc)
    raised = False
    try:
        _ = naive < aware
    except TypeError:
        raised = True
    assert raised, "sanity: naive < aware must raise"
    # with the helper it is safe
    assert ensure_aware(naive) < aware


def test_utcnow_is_aware():
    now = utcnow()
    assert now.tzinfo is timezone.utc


def test_expiry_check_pattern():
    # a stored (naive) expiry in the past is correctly seen as expired
    past_naive = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)
    assert ensure_aware(past_naive) < datetime.now(timezone.utc)
