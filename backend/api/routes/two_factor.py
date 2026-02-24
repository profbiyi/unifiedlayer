"""
Two-Factor Authentication (TOTP) API routes.

Provides endpoints for setting up, verifying, and disabling
TOTP-based two-factor authentication.
"""
import io
import base64
import logging
from datetime import timedelta
from typing import Optional

import pyotp
import qrcode
import redis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import (
    get_current_user,
    create_access_token,
    decode_access_token,
    verify_password,
    AuthError,
)
from backend.models.pipeline import User
from backend.config import settings

logger = logging.getLogger(__name__)

# Rate limiting constants
MAX_2FA_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes

# Initialize Redis client for rate limiting
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client for rate limiting."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_client


def check_rate_limit(user_id: int, action: str = "verify") -> None:
    """
    Check if user has exceeded 2FA attempt rate limit.

    Args:
        user_id: The user ID to check
        action: The action type (verify, setup, disable)

    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    redis_client = get_redis_client()
    key = f"2fa_attempts:{action}:{user_id}"

    try:
        attempts = redis_client.get(key)
        if attempts is not None and int(attempts) >= MAX_2FA_ATTEMPTS:
            ttl = redis_client.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many 2FA attempts. Please try again in {ttl} seconds.",
                headers={"Retry-After": str(ttl)},
            )
    except redis.RedisError as e:
        # Log error but don't block the request if Redis is unavailable
        logger.warning(f"Redis error during rate limit check: {e}")


def increment_rate_limit(user_id: int, action: str = "verify") -> None:
    """
    Increment the 2FA attempt counter for a user.

    Args:
        user_id: The user ID
        action: The action type (verify, setup, disable)
    """
    redis_client = get_redis_client()
    key = f"2fa_attempts:{action}:{user_id}"

    try:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS)
        pipe.execute()
    except redis.RedisError as e:
        # Log error but don't block the request if Redis is unavailable
        logger.warning(f"Redis error during rate limit increment: {e}")


def clear_rate_limit(user_id: int, action: str = "verify") -> None:
    """
    Clear the 2FA attempt counter for a user after successful verification.

    Args:
        user_id: The user ID
        action: The action type (verify, setup, disable)
    """
    redis_client = get_redis_client()
    key = f"2fa_attempts:{action}:{user_id}"

    try:
        redis_client.delete(key)
    except redis.RedisError as e:
        # Log error but don't block the request if Redis is unavailable
        logger.warning(f"Redis error during rate limit clear: {e}")

router = APIRouter(prefix="/auth/2fa", tags=["Two-Factor Authentication"])

APP_NAME = "UnifiedLayer"


class VerifyCodeRequest(BaseModel):
    code: str


class DisableRequest(BaseModel):
    code: str
    password: str


class Verify2FALoginRequest(BaseModel):
    temp_token: str
    code: str


@router.post("/setup")
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a TOTP secret and return provisioning URI + QR code.

    Stores the secret on the user but does not enable 2FA until verified.
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled",
        )

    # Generate a new TOTP secret
    secret = pyotp.random_base32()

    # Store on user (not enabled yet)
    current_user.totp_secret = secret
    db.commit()

    # Build provisioning URI
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name=APP_NAME,
    )

    # Generate QR code as base64 PNG
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "qr_code": f"data:image/png;base64,{qr_base64}",
    }


@router.post("/verify-setup")
async def verify_setup(
    payload: VerifyCodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verify a TOTP code during setup and enable 2FA.

    Rate limited to 5 attempts per 5 minutes per user.
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled",
        )

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No 2FA setup in progress. Call /auth/2fa/setup first.",
        )

    # Check rate limit before attempting verification
    check_rate_limit(current_user.id, action="setup")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code):
        # Increment rate limit counter on failed attempt
        increment_rate_limit(current_user.id, action="setup")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Clear rate limit counter on successful verification
    clear_rate_limit(current_user.id, action="setup")

    current_user.two_factor_enabled = True
    db.commit()

    return {"message": "Two-factor authentication enabled successfully"}


@router.post("/disable")
async def disable_2fa(
    payload: DisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Disable 2FA. Requires current TOTP code and password.

    Rate limited to 5 attempts per 5 minutes per user.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled",
        )

    # Check rate limit before attempting verification
    check_rate_limit(current_user.id, action="disable")

    # Verify password
    if not verify_password(payload.password, current_user.hashed_password):
        # Increment rate limit counter on failed attempt
        increment_rate_limit(current_user.id, action="disable")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    # Verify TOTP code
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code):
        # Increment rate limit counter on failed attempt
        increment_rate_limit(current_user.id, action="disable")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Clear rate limit counter on successful verification
    clear_rate_limit(current_user.id, action="disable")

    current_user.totp_secret = None
    current_user.two_factor_enabled = False
    db.commit()

    # Send notification email about 2FA being disabled (security notification)
    try:
        from backend.notifications import email_notifier
        email_notifier.send_2fa_disabled_notification(
            to_email=current_user.email,
            user_name=current_user.full_name or current_user.username,
        )
    except Exception as e:
        # Log error but don't fail the request
        logger.warning(f"Failed to send 2FA disabled notification to {current_user.email}: {e}")

    return {"message": "Two-factor authentication disabled successfully"}


@router.post("/verify")
async def verify_2fa_login(
    payload: Verify2FALoginRequest,
    db: Session = Depends(get_db),
):
    """
    Complete login by verifying TOTP code with a temporary token.

    Called when login returns requires_2fa: true.
    Rate limited to 5 attempts per 5 minutes per user.
    """
    # Decode the temp token
    try:
        token_data = decode_access_token(payload.temp_token)
    except AuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired temporary token",
        )

    # Verify it is a 2FA pending token
    if not token_data.get("2fa_pending"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = int(token_data["sub"])

    # Check rate limit before attempting verification
    check_rate_limit(user_id, action="verify")

    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not configured for this user",
        )

    # Verify the TOTP code
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(payload.code):
        # Increment rate limit counter on failed attempt
        increment_rate_limit(user_id, action="verify")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Clear rate limit counter on successful verification
    clear_rate_limit(user_id, action="verify")

    # Issue full access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
        },
    }
