"""
Tests for to_utc_z — hand-built dict responses must emit UTC 'Z'-suffixed
timestamps so the frontend parses them as UTC, not the viewer's local time.
"""
from datetime import datetime, timezone, timedelta

from backend.schemas.base import to_utc_z


def test_none_returns_none():
    assert to_utc_z(None) is None


def test_naive_datetime_gets_z_suffix():
    dt = datetime(2026, 7, 28, 9, 49, 23, 442424)  # naive, stored as UTC
    out = to_utc_z(dt)
    assert out == "2026-07-28T09:49:23.442424Z"
    assert out.endswith("Z")


def test_utc_aware_datetime_renders_z():
    dt = datetime(2026, 7, 28, 9, 49, 23, tzinfo=timezone.utc)
    assert to_utc_z(dt) == "2026-07-28T09:49:23Z"


def test_offset_aware_datetime_converted_to_utc():
    # 11:49 at +02:00 is 09:49 UTC
    dt = datetime(2026, 7, 28, 11, 49, 23, tzinfo=timezone(timedelta(hours=2)))
    assert to_utc_z(dt) == "2026-07-28T09:49:23Z"
