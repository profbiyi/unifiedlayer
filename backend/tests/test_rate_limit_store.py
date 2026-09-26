"""Tests for the shared rate-limit counter (in-memory fallback path).

These force the in-memory branch by pointing _get_redis at an unreachable client,
so they run without a live Redis.
"""
import backend.utils.rate_limit_store as rls


def setup_function():
    rls.reset()
    # force the in-memory branch regardless of any ambient Redis
    rls._redis_client = False


def teardown_function():
    rls.reset()
    rls._redis_client = None


def test_hit_increments_within_window():
    now = 1_000_000.0
    counts = [rls.hit("k", 60, now + i) for i in range(5)]  # same 60s bucket
    assert counts == [1, 2, 3, 4, 5]


def test_hit_resets_in_next_window():
    now = 1_000_000.0
    assert rls.hit("k", 60, now) == 1
    assert rls.hit("k", 60, now + 10) == 2
    # cross into the next fixed window -> counter restarts
    assert rls.hit("k", 60, now + 65) == 1


def test_keys_are_independent():
    now = 1_000_000.0
    assert rls.hit("a", 60, now) == 1
    assert rls.hit("b", 60, now) == 1
    assert rls.hit("a", 60, now) == 2


def test_limit_semantics_allow_exactly_limit():
    # caller rejects when hit() return value EXCEEDS the limit, so `limit` requests pass
    now = 1_000_000.0
    limit = 3
    allowed = [rls.hit("x", 60, now) for _ in range(4)]
    passed = [c for c in allowed if c <= limit]
    rejected = [c for c in allowed if c > limit]
    assert len(passed) == 3 and rejected == [4]
