"""
Redis-based JWT token blacklist for secure logout functionality.

This module provides functions to blacklist JWT tokens, enabling immediate
token invalidation upon logout or security events.
"""
import logging
import hashlib
from typing import Optional

import redis
from backend.config import settings

logger = logging.getLogger(__name__)

# Redis key prefix for blacklisted tokens
TOKEN_BLACKLIST_PREFIX = "token_blacklist:"

# Global Redis client (lazy initialization)
_redis_client: Optional[redis.Redis] = None


def _get_redis_client() -> redis.Redis:
    """
    Get or create Redis client for token blacklist operations.

    Returns:
        Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def _get_token_key(token_identifier: str) -> str:
    """
    Generate Redis key for a token identifier.

    Args:
        token_identifier: JTI claim or hashed token

    Returns:
        Redis key for the token
    """
    return f"{TOKEN_BLACKLIST_PREFIX}{token_identifier}"


def get_token_identifier(token: str, jti: Optional[str] = None) -> str:
    """
    Get a unique identifier for a token.

    Uses JTI claim if available, otherwise falls back to SHA-256 hash of the token.

    Args:
        token: The JWT token string
        jti: Optional JTI claim from the token payload

    Returns:
        Unique identifier for the token
    """
    if jti:
        return jti
    # Fallback to token hash for tokens without JTI
    return hashlib.sha256(token.encode()).hexdigest()


def add_token_to_blacklist(token: str, expires_in: int, jti: Optional[str] = None) -> bool:
    """
    Add a token to the Redis blacklist.

    The token is stored with a TTL equal to its remaining lifetime, ensuring
    automatic cleanup after the token would have expired anyway.

    Args:
        token: The JWT token string
        expires_in: Remaining lifetime of the token in seconds
        jti: Optional JTI claim from the token payload

    Returns:
        True if successfully blacklisted, False otherwise
    """
    if expires_in <= 0:
        # Token is already expired, no need to blacklist
        logger.debug("Token already expired, skipping blacklist")
        return True

    try:
        client = _get_redis_client()
        token_id = get_token_identifier(token, jti)
        key = _get_token_key(token_id)

        # Store with TTL equal to token's remaining lifetime
        # Value "1" indicates blacklisted
        client.setex(key, expires_in, "1")

        logger.info("Token blacklisted successfully (TTL: %d seconds)", expires_in)
        return True

    except redis.RedisError as e:
        logger.error("Failed to blacklist token: %s", str(e))
        return False
    except Exception as e:
        logger.exception("Unexpected error blacklisting token: %s", str(e))
        return False


def is_token_blacklisted(token: str, jti: Optional[str] = None) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        token: The JWT token string
        jti: Optional JTI claim from the token payload

    Returns:
        True if the token is blacklisted, False otherwise
    """
    try:
        client = _get_redis_client()
        token_id = get_token_identifier(token, jti)
        key = _get_token_key(token_id)

        result = client.exists(key)
        return bool(result)

    except redis.RedisError as e:
        logger.error("Failed to check token blacklist: %s", str(e))
        # Fail open or fail closed based on security requirements
        # Here we fail open to prevent lockout on Redis issues
        # For higher security environments, consider returning True (fail closed)
        return False
    except Exception as e:
        logger.exception("Unexpected error checking token blacklist: %s", str(e))
        return False


def remove_token_from_blacklist(token: str, jti: Optional[str] = None) -> bool:
    """
    Remove a token from the blacklist (rarely needed, mainly for testing).

    Args:
        token: The JWT token string
        jti: Optional JTI claim from the token payload

    Returns:
        True if successfully removed, False otherwise
    """
    try:
        client = _get_redis_client()
        token_id = get_token_identifier(token, jti)
        key = _get_token_key(token_id)

        client.delete(key)
        return True

    except redis.RedisError as e:
        logger.error("Failed to remove token from blacklist: %s", str(e))
        return False
    except Exception as e:
        logger.exception("Unexpected error removing token from blacklist: %s", str(e))
        return False
