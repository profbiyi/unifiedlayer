"""
Two-Factor Authentication (TOTP) API routes.

Provides endpoints for setting up, verifying, and disabling
TOTP-based two-factor authentication.
"""
import io
import base64
import logging
from datetime import timedelta

import pyotp
import qrcode
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

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

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
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled",
        )

    # Verify password
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    # Verify TOTP code
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    current_user.totp_secret = None
    current_user.two_factor_enabled = False
    db.commit()

    return {"message": "Two-factor authentication disabled successfully"}


@router.post("/verify")
async def verify_2fa_login(
    payload: Verify2FALoginRequest,
    db: Session = Depends(get_db),
):
    """
    Complete login by verifying TOTP code with a temporary token.

    Called when login returns requires_2fa: true.
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

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
