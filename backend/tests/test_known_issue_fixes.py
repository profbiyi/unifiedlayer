"""
Tests for the known-issue hardening pass:
- anomaly dedup is Redis-backed (shared across workers) with an in-memory fallback
- org-wide summary emails are gated off by default
"""
from unittest.mock import MagicMock, patch

import backend.tasks.anomaly_tasks as at
import backend.tasks.summary_tasks as st


def test_anomaly_dedup_uses_redis_when_available():
    fake = MagicMock()
    fake.exists.return_value = 0
    with patch.object(at, "_get_redis", return_value=fake):
        assert at._is_duplicate("p1:volume") is False
        at._mark_sent("p1:volume")
        fake.set.assert_called_once()
        # TTL is set (seconds) so the entry self-expires
        assert fake.set.call_args.kwargs.get("ex") == at.DEDUP_TTL_HOURS * 3600
        fake.exists.return_value = 1
        assert at._is_duplicate("p1:volume") is True


def test_anomaly_dedup_falls_back_to_memory_without_redis():
    at._sent_alerts.clear()
    with patch.object(at, "_get_redis", return_value=None):
        assert at._is_duplicate("p2:latency") is False
        at._mark_sent("p2:latency")
        assert at._is_duplicate("p2:latency") is True


def test_summaries_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SUMMARIES_ENABLED", raising=False)
    assert st._summaries_enabled() is False


def test_summaries_enabled_when_env_true(monkeypatch):
    monkeypatch.setenv("SUMMARIES_ENABLED", "true")
    assert st._summaries_enabled() is True
    monkeypatch.setenv("SUMMARIES_ENABLED", "false")
    assert st._summaries_enabled() is False


def test_daily_summary_skips_when_disabled(monkeypatch):
    monkeypatch.delenv("SUMMARIES_ENABLED", raising=False)
    # Must NOT open a DB session or send anything when disabled.
    with patch.object(st, "SessionLocal") as sess:
        out = st.send_daily_summaries.apply(args=[]).get()
    assert out.get("skipped") is True
    sess.assert_not_called()
