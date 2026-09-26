"""
Shared rate-limit counters.

Rate limiting must be consistent across every web process/replica, otherwise the
effective limit is (configured limit x replica count) and it resets whenever a
process restarts. This module keeps the counters in Redis (atomic INCR + EXPIRE,
one fixed window bucket per key) so all replicas share the same view, and falls
back to a per-process in-memory counter when Redis is unavailable — degrade,
never crash.

Same Redis-with-fallback pattern as the anomaly-alert dedup store.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_redis_client: Any = None
# in-memory fallback: bucket key -> (count, expires_at)
_mem: Dict[str, Tuple[int, float]] = {}
_mem_lock = threading.Lock()


def _get_redis() -> Any:
    """Return a live Redis client, or None if Redis can't be reached."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis

            from backend.config import settings

            client = redis.Redis.from_url(
                settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1
            )
            client.ping()
            _redis_client = client
        except Exception as exc:  # noqa: BLE001 — degrade to in-memory, never crash
            logger.warning(
                "Rate limiter: Redis unavailable (%s); using in-memory fallback", exc
            )
            _redis_client = False
    return _redis_client or None


def hit(key: str, window_seconds: int, now: Optional[float] = None) -> int:
    """Count one request against ``key`` in the current fixed window.

    Returns the number of hits in this window so far, including this one, so the
    caller rejects when the return value exceeds the limit.
    """
    now = time.time() if now is None else now
    bucket = int(now // window_seconds)
    bkey = f"rl:{key}:{bucket}"

    r = _get_redis()
    if r is not None:
        try:
            pipe = r.pipeline()
            pipe.incr(bkey, 1)
            pipe.expire(bkey, window_seconds)
            count = pipe.execute()[0]
            return int(count)
        except Exception as exc:  # noqa: BLE001 — fall back rather than fail the request
            logger.warning("Rate limiter Redis hit failed (%s); using in-memory", exc)

    with _mem_lock:
        count, exp = _mem.get(bkey, (0, now + window_seconds))
        if now >= exp:
            count, exp = 0, now + window_seconds
        count += 1
        _mem[bkey] = (count, exp)
        # opportunistic cleanup so the dict can't grow without bound
        if len(_mem) > 10000:
            for k, (_, e) in list(_mem.items()):
                if now >= e:
                    _mem.pop(k, None)
        return count


def reset() -> None:
    """Clear the in-memory fallback state (used by tests)."""
    with _mem_lock:
        _mem.clear()
