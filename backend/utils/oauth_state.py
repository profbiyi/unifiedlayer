"""
OAuth state management using Redis.

Provides secure state token generation and validation for OAuth2 flows.
State tokens are stored in Redis with a short TTL to prevent CSRF attacks.
"""
import secrets
import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

import redis

from backend.config import settings

logger = logging.getLogger(__name__)

# State token TTL (10 minutes - OAuth flow should complete within this time)
STATE_TTL = timedelta(minutes=10)

# Redis key prefix for OAuth state tokens
OAUTH_STATE_PREFIX = "oauth_state:"


def _get_redis_client() -> redis.Redis:
    """Get Redis client for OAuth state storage."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def generate_oauth_state(
    user_id: int,
    organization_id: int,
    provider: str,
    extra_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a secure OAuth state token and store it in Redis.

    Args:
        user_id: ID of the user initiating the OAuth flow
        organization_id: Organization ID for the connection
        provider: OAuth provider name (e.g., 'xero', 'truelayer', 'hmrc')
        extra_data: Optional additional data to store with the state

    Returns:
        Secure random state token
    """
    # Generate cryptographically secure random token
    state_token = secrets.token_urlsafe(32)

    # Data to store
    state_data = {
        "user_id": user_id,
        "organization_id": organization_id,
        "provider": provider,
    }
    if extra_data:
        state_data["extra"] = extra_data

    try:
        client = _get_redis_client()
        key = f"{OAUTH_STATE_PREFIX}{state_token}"
        client.setex(
            key,
            STATE_TTL,
            json.dumps(state_data),
        )
        logger.debug(f"Generated OAuth state for {provider}: {state_token[:8]}...")
    except redis.RedisError as e:
        logger.error(f"Failed to store OAuth state in Redis: {e}")
        raise RuntimeError("Failed to initialize OAuth flow") from e

    return state_token


def validate_oauth_state(state_token: str, expected_provider: str) -> Optional[Dict[str, Any]]:
    """
    Validate an OAuth state token and retrieve the associated data.

    The state token is deleted after successful validation (one-time use).

    Args:
        state_token: The state token received from OAuth callback
        expected_provider: The expected OAuth provider

    Returns:
        State data dict if valid, None otherwise

    Raises:
        ValueError: If state is invalid, expired, or provider doesn't match
    """
    if not state_token:
        raise ValueError("Missing OAuth state token")

    try:
        client = _get_redis_client()
        key = f"{OAUTH_STATE_PREFIX}{state_token}"

        # Get and delete atomically (prevents replay attacks)
        state_json = client.getdel(key)

        if not state_json:
            raise ValueError("Invalid or expired OAuth state token")

        state_data = json.loads(state_json)

        # Verify provider matches
        if state_data.get("provider") != expected_provider:
            logger.warning(
                f"OAuth provider mismatch: expected {expected_provider}, "
                f"got {state_data.get('provider')}"
            )
            raise ValueError("Invalid OAuth state: provider mismatch")

        return state_data

    except redis.RedisError as e:
        logger.error(f"Failed to validate OAuth state from Redis: {e}")
        raise RuntimeError("Failed to validate OAuth flow") from e
    except json.JSONDecodeError:
        raise ValueError("Corrupted OAuth state data")


def cleanup_oauth_state(state_token: str) -> bool:
    """
    Clean up an OAuth state token (for error handling/cancellation).

    Args:
        state_token: The state token to clean up

    Returns:
        True if token was found and deleted, False otherwise
    """
    if not state_token:
        return False

    try:
        client = _get_redis_client()
        key = f"{OAUTH_STATE_PREFIX}{state_token}"
        return bool(client.delete(key))
    except redis.RedisError as e:
        logger.error(f"Failed to cleanup OAuth state: {e}")
        return False
