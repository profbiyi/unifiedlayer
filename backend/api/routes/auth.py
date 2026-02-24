"""
Authentication API routes.
"""
import logging
import secrets
from datetime import timedelta, datetime, timezone
from uuid import uuid4
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, status, Form, Response, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import httpx

from backend.database import get_db
from backend.schemas import UserCreate, UserResponse
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
import redis
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def log_auth_event(
    db: Session,
    action: str,
    user_id: int = None,
    organization_id: int = None,
    request: Request = None,
    details: dict = None,
) -> None:
    """
    Log an authentication event to the audit log.

    Args:
        db: Database session
        action: Action type (login_success, login_failed, logout, password_reset, etc.)
        user_id: User ID if known
        organization_id: Organization ID if known
        request: FastAPI request for IP/user agent extraction
        details: Additional details to log
    """
    from backend.models.audit import AuditLog
    from backend.middleware import get_client_ip, _parse_trusted_proxies

    ip_address = None
    user_agent = None

    if request:
        trusted_proxies = _parse_trusted_proxies()
        ip_address = get_client_ip(request, trusted_proxies)
        user_agent = request.headers.get("user-agent", "")[:500]

    try:
        audit_log = AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource_type="auth",
            resource_id=str(user_id) if user_id else None,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log auth event: {e}")
        # Don't fail the request if audit logging fails
        db.rollback()

# Redis-backed OAuth state storage
_redis_client = None
OAUTH_STATE_PREFIX = "oauth_state:"
OAUTH_STATE_TTL = 600  # 10 minutes


def _get_redis_client():
    """Get or create Redis client for OAuth state storage."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def _store_oauth_state(state: str, data: dict) -> None:
    """Store OAuth state in Redis with TTL."""
    client = _get_redis_client()
    key = f"{OAUTH_STATE_PREFIX}{state}"
    client.setex(key, OAUTH_STATE_TTL, json.dumps(data, default=str))


def _get_oauth_state(state: str) -> dict | None:
    """Retrieve and delete OAuth state from Redis (one-time use)."""
    client = _get_redis_client()
    key = f"{OAUTH_STATE_PREFIX}{state}"
    data = client.get(key)
    if data:
        client.delete(key)  # One-time use - delete after retrieval
        return json.loads(data)
    return None


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return JWT token.
    Sets HTTPOnly cookie for secure authentication.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        username: User email (username field)
        password: User password
        db: Database session

    Returns:
        Access token and user info
    """
    from datetime import datetime, timezone
    from backend.models.pipeline import Organization

    logger.info(f"Login attempt for: {username}")

    user = authenticate_user(db, username, password)

    if not user:
        # Check if user exists for audit logging
        from backend.models.pipeline import User as UserModel
        debug_user = db.query(UserModel).filter(
            (UserModel.email == username) | (UserModel.username == username)
        ).first()

        # Log failed login attempt
        log_auth_event(
            db=db,
            action="login_failed",
            user_id=debug_user.id if debug_user else None,
            organization_id=debug_user.organization_id if debug_user else None,
            request=request,
            details={"username": username, "reason": "invalid_credentials" if debug_user else "user_not_found"},
        )

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

    # Log successful login
    log_auth_event(
        db=db,
        action="login_success",
        user_id=user.id,
        organization_id=user.organization_id,
        request=request,
        details={"2fa_required": user.two_factor_enabled},
    )

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

    return {"access_token": access_token, "token_type": "bearer", "user": UserResponse.from_orm_with_roles(user)}


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
        User information with roles
    """
    return UserResponse.from_orm_with_roles(current_user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    """
    Logout current user by clearing the authentication cookie and blacklisting the token.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        current_user: Current authenticated user

    Returns:
        Success message
    """
    from backend.utils.token_blacklist import add_token_to_blacklist

    # Get the token from cookie or header
    token = request.cookies.get("token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    # Add token to blacklist if we have it
    if token:
        try:
            # Decode to get JTI and expiration
            from jose import jwt
            # Decode without verification since we just want the claims
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                # Calculate remaining TTL
                expires_in = int(exp - datetime.now(timezone.utc).timestamp())
                if expires_in > 0:
                    add_token_to_blacklist(token, expires_in, jti)
                    logger.info(f"Token blacklisted on logout for user {current_user.id}")
        except Exception as e:
            logger.warning(f"Could not blacklist token on logout: {e}")

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

    # Find user with valid token and lock the row to prevent race conditions
    # This ensures only one concurrent request can reset the password
    user = db.query(User).filter(
        User.password_reset_token == token
    ).with_for_update().first()

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


# =============================================================================
# Google OAuth Endpoints
# =============================================================================

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleLinkRequest(BaseModel):
    """Request to link Google account to existing user."""
    code: str
    state: str


@router.get("/google/login")
async def google_login(
    redirect_uri: str = Query(None, description="Optional custom redirect URI after OAuth"),
):
    """
    Initiate Google OAuth login flow.

    Redirects user to Google's OAuth consent screen.

    Args:
        redirect_uri: Optional frontend URL to redirect to after successful auth

    Returns:
        Redirect to Google OAuth consent screen
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state with metadata in Redis (auto-expires after 10 minutes)
    _store_oauth_state(state, {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "redirect_uri": redirect_uri or settings.FRONTEND_URL,
        "action": "login"
    })

    # Build Google OAuth URL
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI or f"{settings.FRONTEND_URL}/api/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Handle Google OAuth callback.

    Exchanges authorization code for tokens, retrieves user info,
    and either logs in existing user or creates new account.

    Args:
        code: Authorization code from Google
        state: State parameter for CSRF validation
        error: Error message if OAuth was denied
        db: Database session

    Returns:
        Redirect to frontend with access token or error
    """
    from backend.models.pipeline import Organization

    # Handle OAuth errors
    if error:
        logger.warning("Google OAuth error: %s", error)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=oauth_denied"
        )

    # Validate state token (retrieved from Redis, auto-deleted after use)
    state_data = _get_oauth_state(state)
    if not state_data:
        logger.warning("Invalid or expired OAuth state token")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=invalid_state"
        )

    redirect_uri = state_data.get("redirect_uri", settings.FRONTEND_URL)
    state_data.get("action", "login")

    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI or f"{settings.FRONTEND_URL}/api/auth/google/callback",
                },
            )

            if token_response.status_code != 200:
                logger.error("Failed to exchange code for token: %s", token_response.text)
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/login?error=token_exchange_failed"
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # Get user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if userinfo_response.status_code != 200:
                logger.error("Failed to get user info: %s", userinfo_response.text)
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/login?error=userinfo_failed"
                )

            google_user = userinfo_response.json()

    except Exception as e:
        logger.exception("Google OAuth error: %s", str(e))
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=oauth_error"
        )

    google_id = google_user.get("id")
    email = google_user.get("email")
    google_user.get("name", "")

    if not email:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=email_required"
        )

    # Check if user exists by Google ID
    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        # Check if user exists by email (link accounts)
        user = db.query(User).filter(User.email == email).first()

        if user:
            # Link Google account to existing user
            user.google_id = google_id
            user.oauth_provider = "google"
            user.email_verified = True  # Google emails are verified
            db.commit()
            logger.info("Linked Google account to existing user: %s", email)
        else:
            # Create new user - but we need an organization
            # For OAuth signups, we'll create a personal org or require invitation
            # For now, return error - self-registration is disabled
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=registration_disabled&email={email}"
            )

    # Check if user is active and organization is active
    if not user.is_active:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=account_disabled"
        )

    if user.organization and not user.organization.is_active:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=organization_disabled"
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    # Check if this is first login of an org admin (onboarding)
    if user.is_org_admin() and user.organization:
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        if org and not org.admin_onboarded:
            org.admin_onboarded = True
            org.admin_onboarded_at = datetime.now(timezone.utc)

    db.commit()

    # Generate access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires,
    )

    # Redirect to frontend with token
    return RedirectResponse(
        url=f"{redirect_uri}/login?token={jwt_token}"
    )


@router.post("/google/link")
async def google_link_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get URL to link Google account to current user.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        Google OAuth URL for account linking
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    if current_user.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account is already linked"
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state with user ID for linking in Redis (auto-expires after 10 minutes)
    _store_oauth_state(state, {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "redirect_uri": f"{settings.FRONTEND_URL}/settings",
        "action": "link",
        "user_id": str(current_user.id)
    })

    # Build Google OAuth URL
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI or f"{settings.FRONTEND_URL}/api/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/google/link/callback")
async def google_link_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Handle Google OAuth callback for account linking.

    Args:
        code: Authorization code from Google
        state: State parameter with user ID
        error: Error message if OAuth was denied
        db: Database session

    Returns:
        Redirect to settings page with success/error message
    """
    if error:
        logger.warning("Google OAuth link error: %s", error)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=oauth_denied"
        )

    # Validate state token (retrieved from Redis, auto-deleted after use)
    state_data = _get_oauth_state(state)
    if not state_data or state_data.get("action") != "link":
        logger.warning("Invalid or expired OAuth state token for linking")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=invalid_state"
        )

    user_id = state_data.get("user_id")
    if not user_id:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=invalid_state"
        )

    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI or f"{settings.FRONTEND_URL}/api/auth/google/callback",
                },
            )

            if token_response.status_code != 200:
                logger.error("Failed to exchange code for token: %s", token_response.text)
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/settings?error=token_exchange_failed"
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # Get user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if userinfo_response.status_code != 200:
                logger.error("Failed to get user info: %s", userinfo_response.text)
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/settings?error=userinfo_failed"
                )

            google_user = userinfo_response.json()

    except Exception as e:
        logger.exception("Google OAuth link error: %s", str(e))
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=oauth_error"
        )

    google_id = google_user.get("id")
    google_email = google_user.get("email")

    # Check if this Google account is already linked to another user
    existing_user = db.query(User).filter(User.google_id == google_id).first()
    if existing_user and existing_user.id != user_id:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=google_already_linked"
        )

    # Get the user and link Google account
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=user_not_found"
        )

    user.google_id = google_id
    user.oauth_provider = "google"
    db.commit()

    logger.info("Linked Google account %s to user %s", google_email, user.email)

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/settings?google_linked=true"
    )


@router.delete("/google/unlink")
async def google_unlink_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unlink Google account from current user.

    User must have a password set to unlink (otherwise they'd be locked out).

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    if not current_user.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Google account is linked"
        )

    # Check if user has a password set (required to unlink)
    if not current_user.hashed_password or current_user.hashed_password == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must set a password before unlinking Google account"
        )

    current_user.google_id = None
    if current_user.oauth_provider == "google":
        current_user.oauth_provider = None

    db.commit()

    return {"message": "Google account unlinked successfully"}
