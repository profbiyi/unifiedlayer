"""
Idempotency Key Support.

Prevents duplicate operations when clients retry requests.
Stores operation results in Redis keyed by the idempotency key.
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

import redis

from backend.config import settings

logger = logging.getLogger(__name__)

# Idempotency key TTL (24 hours - standard for most payment providers)
IDEMPOTENCY_TTL = timedelta(hours=24)

# Redis key prefix
IDEMPOTENCY_PREFIX = "idempotency:"


def _get_redis_client() -> redis.Redis:
    """Get Redis client for idempotency storage."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_idempotency_result(idempotency_key: str) -> Optional[Dict[str, Any]]:
    """
    Check if a request with this idempotency key has already been processed.

    Args:
        idempotency_key: The idempotency key from X-Idempotency-Key header

    Returns:
        Stored result dict if key exists, None otherwise
    """
    if not idempotency_key:
        return None

    try:
        client = _get_redis_client()
        key = f"{IDEMPOTENCY_PREFIX}{idempotency_key}"
        data = client.get(key)

        if data:
            logger.debug(f"Idempotency cache hit: {idempotency_key[:16]}...")
            return json.loads(data)

    except redis.RedisError as e:
        logger.warning(f"Redis error checking idempotency key: {e}")

    return None


def store_idempotency_result(
    idempotency_key: str,
    status_code: int,
    response_body: Dict[str, Any],
) -> bool:
    """
    Store the result of a request for future idempotency checks.

    Args:
        idempotency_key: The idempotency key from X-Idempotency-Key header
        status_code: HTTP status code of the response
        response_body: JSON-serializable response body

    Returns:
        True if stored successfully, False otherwise
    """
    if not idempotency_key:
        return False

    try:
        client = _get_redis_client()
        key = f"{IDEMPOTENCY_PREFIX}{idempotency_key}"

        data = {
            "status_code": status_code,
            "body": response_body,
        }

        client.setex(
            key,
            IDEMPOTENCY_TTL,
            json.dumps(data, default=str),
        )

        logger.debug(f"Stored idempotency result: {idempotency_key[:16]}...")
        return True

    except redis.RedisError as e:
        logger.warning(f"Redis error storing idempotency key: {e}")
        return False


def clear_idempotency_key(idempotency_key: str) -> bool:
    """
    Clear an idempotency key (useful for cleaning up failed operations).

    Args:
        idempotency_key: The idempotency key to clear

    Returns:
        True if cleared successfully, False otherwise
    """
    if not idempotency_key:
        return False

    try:
        client = _get_redis_client()
        key = f"{IDEMPOTENCY_PREFIX}{idempotency_key}"
        return bool(client.delete(key))

    except redis.RedisError as e:
        logger.warning(f"Redis error clearing idempotency key: {e}")
        return False
