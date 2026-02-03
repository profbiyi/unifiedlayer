"""
Authentication API routes.
"""
import logging
from datetime import timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Form, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import Token, UserLogin, UserCreate, UserResponse
from backend.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_user,
    require_super_admin,
)
from backend.models.pipeline import User
from backend.config import settings
from backend.utils.email import send_verification_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return JWT token.
    Sets HTTPOnly cookie for secure authentication.

    Args:
        response: FastAPI response object
        username: User email (username field)
        password: User password
        db: Database session

    Returns:
        Access token and user info
    """
    from datetime import datetime, timezone
    from backend.models.pipeline import Organization

    user = authenticate_user(db, username, password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)

    # Check if this is the first login of an org admin (onboarding)
    if user.is_org_admin() and user.organization:
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        if org and not org.admin_onboarded:
            org.admin_onboarded = True
            org.admin_onboarded_at = datetime.now(timezone.utc)

    # Single commit for all changes
    db.commit()

    # If 2FA is enabled, return a short-lived temp token instead of full access
    if user.two_factor_enabled:
        temp_token_expires = timedelta(minutes=5)
        temp_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "2fa_pending": True},
            expires_delta=temp_token_expires,
        )
        return {"requires_2fa": True, "temp_token": temp_token}

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},  # sub must be string
        expires_delta=access_token_expires,
    )

    # Set HTTPOnly cookie for security (prevents XSS attacks)
    response.set_cookie(
        key="token",
        value=access_token,
        domain="localhost" if settings.ENVIRONMENT != "production" else None,  # Share across ports in dev
        httponly=True,  # Prevents JavaScript access
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        samesite="lax",  # CSRF protection
        secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
    )

    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Register a new user.

    **Super Admin Only** - Self-registration is disabled.
    Account creation is by invitation only via admin onboarding.

    Args:
        user_data: User registration data
        db: Database session
        current_user: Authenticated super admin

    Returns:
        Created user
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Generate email verification token
    verification_token = str(uuid4())

    # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        organization_id=user_data.organization_id,
        is_active=True,
        is_superuser=False,
        email_verified=False,
        email_verification_token=verification_token,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email (non-blocking, gracefully fails)
    try:
        send_verification_email(user.email, verification_token)
    except Exception as e:
        logger.warning("Failed to send verification email to %s: %s", user.email, str(e))

    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return current_user


@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
):
    """
    Logout current user by clearing the authentication cookie.

    Args:
        response: FastAPI response object
        current_user: Current authenticated user

    Returns:
        Success message
    """
    # Clear the authentication cookie
    response.delete_cookie(
        key="token",
        path="/",
        domain="localhost" if settings.ENVIRONMENT != "production" else None,
        samesite="lax"
    )

    return {"message": "Successfully logged out"}


@router.post("/forgot-password")
async def forgot_password(
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Request password reset email.

    Args:
        email: User's email address
        db: Database session

    Returns:
        Success message (always, to prevent email enumeration)
    """
    import secrets
    from datetime import timedelta
    from backend.notifications import email_notifier
    from backend.config import settings

    # Always return success to prevent email enumeration
    user = db.query(User).filter(User.email == email).first()

    if user:
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)

        # Set token expiration (1 hour from now)
        from datetime import timezone
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        # Save token to database
        user.password_reset_token = reset_token
        user.password_reset_expires = expires
        db.commit()

        # Send reset email
        frontend_url = settings.FRONTEND_URL
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"

        try:
            # Get organization for branding
            org = user.organization if user.organization else None

            email_notifier.send_password_reset_email(
                to_email=user.email,
                reset_link=reset_link,
                user_name=user.full_name or user.username,
                organization_name=org.name if org else None,
                logo_url=org.logo_url if org else None,
                brand_primary_color=org.brand_primary_color if org else None,
                brand_secondary_color=org.brand_secondary_color if org else None,
            )
        except Exception as e:
            # Log error but don't expose to user
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send password reset email: {str(e)}")

    # Always return success message (security best practice)
    return {
        "message": "If an account exists with that email, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    token: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Reset password using token.

    Args:
        token: Password reset token
        new_password: New password
        db: Database session

    Returns:
        Success message
    """
    from datetime import timezone

    # Find user with valid token
    user = db.query(User).filter(
        User.password_reset_token == token
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Check if token is expired
    if not user.password_reset_expires or user.password_reset_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )

    # Validate new password length
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    # Update password
    user.hashed_password = get_password_hash(new_password)

    # Clear reset token
    user.password_reset_token = None
    user.password_reset_expires = None

    db.commit()

    return {"message": "Password has been reset successfully"}


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


@router.post("/verify-email")
async def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    """
    Verify a user's email address using the verification token.

    Args:
        payload: Contains the verification token
        db: Database session

    Returns:
        Success message
    """
    user = db.query(User).filter(
        User.email_verification_token == payload.token
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    if user.email_verified:
        return {"message": "Email already verified"}

    user.email_verified = True
    user.email_verification_token = None
    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    payload: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    """
    Resend email verification link.

    Args:
        payload: Contains the user's email address
        db: Database session

    Returns:
        Success message (always, to prevent email enumeration)
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if user and not user.email_verified:
        # Generate a new token
        new_token = str(uuid4())
        user.email_verification_token = new_token
        db.commit()

        try:
            send_verification_email(user.email, new_token)
        except Exception as e:
            logger.warning("Failed to resend verification email to %s: %s", user.email, str(e))

    # Always return success to prevent email enumeration
    return {"message": "If an account exists with that email, a verification link has been sent."}
