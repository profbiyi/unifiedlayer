"""
API Key management routes.

Provides endpoints for creating, listing, and revoking API keys
for programmatic access to the UnifiedLayer API.
"""
import secrets
import hashlib
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.pipeline import User
from backend.models.api_key import APIKey

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# --- Schemas ---

class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="A descriptive name for the key")
    scopes: Optional[List[str]] = Field(None, description="Optional list of permission scopes")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration datetime (UTC)")


class APIKeyCreateResponse(BaseModel):
    id: int
    name: str
    key: str = Field(..., description="The full API key. This is only shown once.")
    key_prefix: str
    scopes: Optional[List[str]]
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyListItem(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: Optional[List[str]]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyRevokeResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    message: str


# --- Endpoints ---

@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key.

    Generates a random 32-byte hex key with the prefix `dp_live_`.
    The full key is returned **only once** in this response. Only a
    SHA-256 hash is stored in the database.
    """
    # Generate key: dp_live_ + 32 random hex chars (16 bytes)
    raw_hex = secrets.token_hex(16)
    plain_key = f"dp_live_{raw_hex}"

    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    key_prefix = plain_key[:12]  # "dp_live_" + first 4 hex chars

    api_key = APIKey(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        name=body.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=body.scopes,
        expires_at=body.expires_at,
        is_active=True,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=plain_key,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get("", response_model=List[APIKeyListItem])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for the current user.

    Returns key metadata (prefix, name, timestamps) but never the full key.
    """
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
    ).order_by(APIKey.created_at.desc()).all()

    return keys


@router.delete("/{key_id}", response_model=APIKeyRevokeResponse)
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke an API key by setting is_active to false.

    The key record is preserved for audit purposes but can no longer
    be used for authentication.
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.is_active = False
    db.commit()

    return APIKeyRevokeResponse(
        id=api_key.id,
        name=api_key.name,
        is_active=False,
        message="API key revoked successfully",
    )
