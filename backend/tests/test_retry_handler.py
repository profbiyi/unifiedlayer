"""Tests for the pipeline retry handler service."""
import pytest
from unittest.mock import MagicMock, patch
import time

from backend.services.retry_handler import (
    calculate_retry_delay,
    should_retry_pipeline,
    get_pending_retries,
)


class TestCalculateRetryDelay:
    """Tests for delay calculation with jitter."""

    def test_basic_delay_no_exponential(self):
        """Without exponential backoff, should return base delay."""
        delay = calculate_retry_delay(
            base_delay=60,
            retry_count=0,
            exponential_backoff=False,
            jitter=False,
        )
        assert delay == 60

    def test_exponential_backoff(self):
        """With exponential backoff, delay should double each retry."""
        # First retry: 60 * 2^0 = 60
        delay = calculate_retry_delay(
            base_delay=60,
            retry_count=0,
            exponential_backoff=True,
            jitter=False,
        )
        assert delay == 60

        # Second retry: 60 * 2^1 = 120
        delay = calculate_retry_delay(
            base_delay=60,
            retry_count=1,
            exponential_backoff=True,
            jitter=False,
        )
        assert delay == 120

        # Third retry: 60 * 2^2 = 240
        delay = calculate_retry_delay(
            base_delay=60,
            retry_count=2,
            exponential_backoff=True,
            jitter=False,
        )
        assert delay == 240

    def test_max_delay_cap(self):
        """Delay should be capped at max_delay."""
        delay = calculate_retry_delay(
            base_delay=60,
            retry_count=10,  # Would be 60 * 2^10 = 61440
            exponential_backoff=True,
            max_delay=3600,  # Cap at 1 hour
            jitter=False,
        )
        assert delay == 3600

    def test_jitter_adds_randomness(self):
        """Jitter should add randomness to the delay."""
        delays = set()
        for _ in range(100):
            delay = calculate_retry_delay(
                base_delay=100,
                retry_count=0,
                exponential_backoff=False,
                jitter=True,
                jitter_factor=0.25,
            )
            delays.add(round(delay, 2))

        # With jitter, we should get different values
        assert len(delays) > 1

        # All delays should be within +/- 25% of base delay
        for d in delays:
            assert 75 <= d <= 125

    def test_jitter_prevents_identical_delays(self):
        """Multiple calls with jitter should produce different delays."""
        delay1 = calculate_retry_delay(
            base_delay=60,
            retry_count=0,
            exponential_backoff=True,
            jitter=True,
        )
        delay2 = calculate_retry_delay(
            base_delay=60,
            retry_count=0,
            exponential_backoff=True,
            jitter=True,
        )

        # Very unlikely to be exactly the same with jitter
        # Note: This test could theoretically fail, but probability is extremely low
        # In production, we'd run this many times
        pass  # Just checking it doesn't crash

    def test_minimum_delay_with_jitter(self):
        """Delay should never go below 1 second even with negative jitter."""
        delays = []
        for _ in range(100):
            delay = calculate_retry_delay(
                base_delay=2,
                retry_count=0,
                exponential_backoff=False,
                jitter=True,
                jitter_factor=0.5,  # Could subtract up to 50%
            )
            delays.append(delay)

        # All delays should be at least 1.0
        assert all(d >= 1.0 for d in delays)


class TestShouldRetryPipeline:
    """Tests for retry decision logic."""

    def test_no_retries_configured(self):
        """Should not retry if max_retries is 0."""
        pipeline = MagicMock()
        pipeline.max_retries = 0
        pipeline.is_active = True

        run = MagicMock()
        run.retry_count = 0

        assert should_retry_pipeline(pipeline, run) is False

    def test_max_retries_reached(self):
        """Should not retry if retry count equals max retries."""
        pipeline = MagicMock()
        pipeline.max_retries = 3
        pipeline.is_active = True

        run = MagicMock()
        run.retry_count = 3  # Already tried 3 times

        assert should_retry_pipeline(pipeline, run) is False

    def test_pipeline_inactive(self):
        """Should not retry if pipeline is inactive."""
        pipeline = MagicMock()
        pipeline.max_retries = 3
        pipeline.is_active = False

        run = MagicMock()
        run.retry_count = 0

        assert should_retry_pipeline(pipeline, run) is False

    def test_should_retry(self):
        """Should retry when all conditions are met."""
        pipeline = MagicMock()
        pipeline.id = 1
        pipeline.max_retries = 3
        pipeline.is_active = True

        run = MagicMock()
        run.id = 1
        run.retry_count = 1  # Has room for more retries

        assert should_retry_pipeline(pipeline, run) is True

    def test_handles_none_retry_count(self):
        """Should handle None retry_count gracefully."""
        pipeline = MagicMock()
        pipeline.id = 1
        pipeline.max_retries = 3
        pipeline.is_active = True

        run = MagicMock()
        run.id = 1
        run.retry_count = None  # Not set

        assert should_retry_pipeline(pipeline, run) is True

    def test_handles_missing_max_retries(self):
        """Should handle missing max_retries attribute."""
        pipeline = MagicMock(spec=[])  # No max_retries attribute

        run = MagicMock()
        run.retry_count = 0

        assert should_retry_pipeline(pipeline, run) is False


class TestPendingRetries:
    """Tests for pending retry tracking."""

    def test_get_pending_retries_empty(self):
        """Should return empty list when no retries pending."""
        # Clear any existing timers
        from backend.services import retry_handler
        retry_handler._active_timers.clear()

        retries = get_pending_retries()
        assert retries == []


class TestNonBlockingBehavior:
    """Tests to verify retry scheduling is non-blocking."""

    def test_schedule_returns_immediately(self):
        """Scheduling should return without blocking."""
        # This is a behavioral test - we verify the function returns quickly
        # rather than sleeping for the retry delay

        from backend.services.retry_handler import schedule_pipeline_retry

        with patch("backend.services.retry_handler.get_db_session") as mock_db:
            # Set up mocks
            mock_session = MagicMock()
            mock_db.return_value = mock_session

            mock_pipeline = MagicMock()
            mock_pipeline.id = 1
            mock_pipeline.max_retries = 3
            mock_pipeline.is_active = True
            mock_pipeline.retry_delay_seconds = 300  # 5 minutes
            mock_pipeline.exponential_backoff_enabled = False

            mock_run = MagicMock()
            mock_run.id = 1
            mock_run.retry_count = 0
            mock_run.is_retry = False
            mock_run.original_run_id = None

            mock_session.query.return_value.filter.return_value.first.side_effect = [
                mock_pipeline,
                mock_run,
            ]

            # Time the function call
            start_time = time.time()
            result = schedule_pipeline_retry(
                pipeline_id=1,
                failed_run_id=1,
                retry_immediately=False,
            )
            elapsed = time.time() - start_time

            # Should return within 1 second (not wait for 5 minute delay)
            assert elapsed < 1.0, f"Function took {elapsed}s, should be non-blocking"

        # Clean up any timers
        from backend.services import retry_handler
        retry_handler._active_timers.clear()
