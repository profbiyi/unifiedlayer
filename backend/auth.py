"""
Authentication and authorization utilities.

Provides JWT token generation/validation, password hashing,
and authentication dependencies for FastAPI.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging
import uuid
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.pipeline import User
from backend.models.rbac import UserRole
from backend.models.api_key import APIKey
from sqlalchemy.orm import joinedload
import hashlib
from backend.utils.token_blacklist import is_token_blacklisted

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class AuthError(Exception):
    """Custom authentication error."""
    pass


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add JTI (JWT ID) claim for unique token identification
    # This enables token blacklisting for secure logout
    jti = str(uuid.uuid4())

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token

    Returns:
        Decoded token payload

    Raises:
        AuthError: If token is invalid or blacklisted
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Check if token is blacklisted (logout, security revocation, etc.)
        jti = payload.get("jti")
        if is_token_blacklisted(token, jti):
            raise AuthError("Token has been revoked")

        return payload
    except JWTError as e:
        raise AuthError(f"Invalid token: {str(e)}")


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email/username and password.

    Args:
        db: Database session
        email: User email or username
        password: User password

    Returns:
        User object if authentication successful, None otherwise
    """
    # Try to find user by email first, then by username
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = db.query(User).filter(User.username == email).first()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> User:
    """
    FastAPI dependency to get current authenticated user.
    Supports both HTTPOnly cookies (preferred) and Authorization header.

    Args:
        request: FastAPI request object (to access cookies)
        db: Database session
        credentials: Optional HTTP Bearer credentials

    Returns:
        Current user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try to get token from cookie first (HTTPOnly, more secure)
    token = request.cookies.get("token")

    # Fall back to Authorization header (for API clients)
    if not token and credentials:
        token = credentials.credentials

    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")

        if user_id_str is None:
            raise credentials_exception

        # Convert string user_id back to int
        user_id = int(user_id_str)

    except (AuthError, ValueError, TypeError):
        raise credentials_exception

    # Load user with roles and organization eagerly for RBAC
    user = db.query(User).options(
        joinedload(User.user_roles).joinedload(UserRole.role),
        joinedload(User.organization)
    ).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Check if organization is active (hard shutdown by super admin)
    # Super admins are exempt - they need to manage the platform
    if user.organization and not user.organization.is_active:
        if not user.is_superuser and not user.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your organization has been deactivated. Please contact support.",
            )

    return user


async def get_current_user_or_api_key(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> User:
    """
    FastAPI dependency that authenticates via JWT Bearer token OR X-API-Key header.

    Checks Bearer JWT first (existing flow). If no Bearer token is present,
    falls back to X-API-Key header authentication. The API key is hashed with
    SHA-256 and looked up in the api_keys table.

    Returns:
        The authenticated User object.

    Raises:
        HTTPException: If neither authentication method succeeds.
    """
    # 1. Try Bearer JWT token first (cookie or Authorization header)
    token = request.cookies.get("token")
    if not token and credentials:
        token = credentials.credentials

    if token:
        try:
            payload = decode_access_token(token)
            user_id_str: str = payload.get("sub")
            if user_id_str is not None:
                user_id = int(user_id_str)
                user = db.query(User).options(
                    joinedload(User.user_roles).joinedload(UserRole.role),
                    joinedload(User.organization)
                ).filter(User.id == user_id).first()
                if user and user.is_active:
                    if user.organization and not user.organization.is_active:
                        if not user.is_superuser and not user.is_super_admin():
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="Your organization has been deactivated. Please contact support.",
                            )
                    return user
        except (AuthError, ValueError, TypeError):
            pass  # Fall through to API key check

    # 2. Try X-API-Key header
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        if not api_key_header.startswith("dp_live_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format",
            )

        key_hash = hashlib.sha256(api_key_header.encode()).hexdigest()
        api_key_record = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active,
        ).first()

        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        if not api_key_record.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired",
            )

        # Update last_used_at
        api_key_record.last_used_at = datetime.now(timezone.utc)
        db.commit()

        # Load associated user
        user = db.query(User).options(
            joinedload(User.user_roles).joinedload(UserRole.role),
            joinedload(User.organization)
        ).filter(User.id == api_key_record.user_id).first()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with API key is inactive",
            )

        if user.organization and not user.organization.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your organization has been deactivated. Please contact support.",
            )

        return user

    # Neither method worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency to get current active user.

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency to require superuser privileges.

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    # Support both old is_superuser flag and new RBAC system
    if not (current_user.is_superuser or current_user.is_super_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )
    return current_user


async def require_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency to require SUPER_ADMIN role.

    Args:
        current_user: Current user

    Returns:
        Current user (must be super admin)

    Raises:
        HTTPException: If user is not a super admin
    """
    if not current_user.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


async def require_org_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency to require ORG_ADMIN role or higher.

    Args:
        current_user: Current user

    Returns:
        Current user (must be org admin or super admin)

    Raises:
        HTTPException: If user is not an admin
    """
    if not (current_user.is_super_admin() or current_user.is_org_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin access required",
        )
    return current_user


def get_request_info(request: Request) -> Dict[str, Any]:
    """
    Extract useful information from request for audit logging.

    Args:
        request: FastAPI request

    Returns:
        Dict with ip_address and user_agent
    """
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.

    Args:
        api_key: Plain text API key

    Returns:
        SHA-256 hash of the key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()
