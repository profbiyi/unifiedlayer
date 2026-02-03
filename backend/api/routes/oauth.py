"""
OAuth2 callback routes for UK connectors (Xero, TrueLayer, HMRC MTD).
"""
import logging
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import settings
from backend.database import get_db
from backend.models.pipeline import DataSource, SourceType, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["OAuth"])

# ---------------------------------------------------------------------------
# Xero OAuth2
# ---------------------------------------------------------------------------

XERO_AUTH_URL = "https://login.xero.com/identity/connect/authorize"
XERO_TOKEN_URL = "https://identity.xero.com/connect/token"
XERO_CONNECTIONS_URL = "https://api.xero.com/connections"


@router.get("/xero/authorize")
async def xero_authorize(current_user: User = Depends(get_current_user)):
    """Generate Xero OAuth2 authorization URL."""
    if not settings.XERO_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Xero OAuth not configured")

    params = {
        "response_type": "code",
        "client_id": settings.XERO_CLIENT_ID,
        "redirect_uri": f"{settings.FRONTEND_URL}/oauth/xero/callback",
        "scope": "openid profile email accounting.transactions accounting.contacts accounting.settings offline_access",
        "state": str(current_user.organization_id),
    }
    return RedirectResponse(url=f"{XERO_AUTH_URL}?{urlencode(params)}")


@router.get("/xero/callback")
async def xero_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Exchange Xero authorization code for tokens and store in DataSource."""
    organization_id = int(state)

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            XERO_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{settings.FRONTEND_URL}/oauth/xero/callback",
            },
            auth=(settings.XERO_CLIENT_ID, settings.XERO_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            logger.error(f"Xero token exchange failed: {token_response.text}")
            raise HTTPException(status_code=400, detail="Failed to exchange Xero authorization code")

        tokens = token_response.json()

        # Fetch tenant (organisation) connections
        connections_response = await client.get(
            XERO_CONNECTIONS_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        tenant_id = None
        if connections_response.status_code == 200:
            connections = connections_response.json()
            if connections:
                tenant_id = connections[0].get("tenantId")

    config = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type"),
        "expires_in": tokens.get("expires_in"),
        "tenant_id": tenant_id,
    }

    # Create or update DataSource
    data_source = (
        db.query(DataSource)
        .filter(
            DataSource.organization_id == organization_id,
            DataSource.source_type == SourceType.XERO,
        )
        .first()
    )

    if data_source:
        data_source.config = config
        data_source.is_active = True
    else:
        data_source = DataSource(
            organization_id=organization_id,
            name="Xero",
            source_type=SourceType.XERO,
            config=config,
            is_active=True,
        )
        db.add(data_source)

    db.commit()
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/sources?connected=xero")


# ---------------------------------------------------------------------------
# TrueLayer (Open Banking) OAuth2
# ---------------------------------------------------------------------------

TRUELAYER_AUTH_URL = "https://auth.truelayer.com"
TRUELAYER_TOKEN_URL = "https://auth.truelayer.com/connect/token"
TRUELAYER_SANDBOX_AUTH_URL = "https://auth.truelayer-sandbox.com"
TRUELAYER_SANDBOX_TOKEN_URL = "https://auth.truelayer-sandbox.com/connect/token"


def _truelayer_urls() -> tuple[str, str]:
    """Return auth and token URLs based on environment."""
    if settings.ENVIRONMENT in ("production", "staging"):
        return TRUELAYER_AUTH_URL, TRUELAYER_TOKEN_URL
    return TRUELAYER_SANDBOX_AUTH_URL, TRUELAYER_SANDBOX_TOKEN_URL


@router.get("/truelayer/authorize")
async def truelayer_authorize(current_user: User = Depends(get_current_user)):
    """Generate TrueLayer OAuth2 authorization URL."""
    if not settings.TRUELAYER_CLIENT_ID:
        raise HTTPException(status_code=500, detail="TrueLayer OAuth not configured")

    auth_url, _ = _truelayer_urls()
    params = {
        "response_type": "code",
        "client_id": settings.TRUELAYER_CLIENT_ID,
        "redirect_uri": f"{settings.FRONTEND_URL}/oauth/truelayer/callback",
        "scope": "info accounts balance transactions",
        "state": str(current_user.organization_id),
    }
    if settings.ENVIRONMENT not in ("production", "staging"):
        params["enable_mock"] = "true"

    return RedirectResponse(url=f"{auth_url}/?{urlencode(params)}")


@router.get("/truelayer/callback")
async def truelayer_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Exchange TrueLayer authorization code for tokens and store in DataSource."""
    organization_id = int(state)
    _, token_url = _truelayer_urls()

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{settings.FRONTEND_URL}/oauth/truelayer/callback",
                "client_id": settings.TRUELAYER_CLIENT_ID,
                "client_secret": settings.TRUELAYER_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            logger.error(f"TrueLayer token exchange failed: {token_response.text}")
            raise HTTPException(status_code=400, detail="Failed to exchange TrueLayer authorization code")

        tokens = token_response.json()

    config = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type"),
        "expires_in": tokens.get("expires_in"),
    }

    data_source = (
        db.query(DataSource)
        .filter(
            DataSource.organization_id == organization_id,
            DataSource.source_type == SourceType.OPEN_BANKING,
        )
        .first()
    )

    if data_source:
        data_source.config = config
        data_source.is_active = True
    else:
        data_source = DataSource(
            organization_id=organization_id,
            name="TrueLayer (Open Banking)",
            source_type=SourceType.OPEN_BANKING,
            config=config,
            is_active=True,
        )
        db.add(data_source)

    db.commit()
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/sources?connected=truelayer")


# ---------------------------------------------------------------------------
# HMRC MTD OAuth2
# ---------------------------------------------------------------------------

HMRC_AUTH_URL = "https://www.tax.service.gov.uk/oauth/authorize"
HMRC_TOKEN_URL = "https://api.service.hmrc.gov.uk/oauth/token"
HMRC_SANDBOX_AUTH_URL = "https://test-www.tax.service.gov.uk/oauth/authorize"
HMRC_SANDBOX_TOKEN_URL = "https://test-api.service.hmrc.gov.uk/oauth/token"


def _hmrc_urls() -> tuple[str, str]:
    """Return auth and token URLs based on environment."""
    if settings.ENVIRONMENT in ("production", "staging"):
        return HMRC_AUTH_URL, HMRC_TOKEN_URL
    return HMRC_SANDBOX_AUTH_URL, HMRC_SANDBOX_TOKEN_URL


@router.get("/hmrc/authorize")
async def hmrc_authorize(current_user: User = Depends(get_current_user)):
    """Generate HMRC MTD OAuth2 authorization URL."""
    if not settings.HMRC_CLIENT_ID:
        raise HTTPException(status_code=500, detail="HMRC OAuth not configured")

    auth_url, _ = _hmrc_urls()
    params = {
        "response_type": "code",
        "client_id": settings.HMRC_CLIENT_ID,
        "redirect_uri": f"{settings.FRONTEND_URL}/oauth/hmrc/callback",
        "scope": "read:vat write:vat",
        "state": str(current_user.organization_id),
    }
    return RedirectResponse(url=f"{auth_url}?{urlencode(params)}")


@router.get("/hmrc/callback")
async def hmrc_callback(
    code: str = Query(...),
    state: str = Query(...),
    vrn: str = Query(default=None),
    db: Session = Depends(get_db),
):
    """Exchange HMRC authorization code for tokens and store in DataSource."""
    organization_id = int(state)
    _, token_url = _hmrc_urls()

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{settings.FRONTEND_URL}/oauth/hmrc/callback",
                "client_id": settings.HMRC_CLIENT_ID,
                "client_secret": settings.HMRC_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            logger.error(f"HMRC token exchange failed: {token_response.text}")
            raise HTTPException(status_code=400, detail="Failed to exchange HMRC authorization code")

        tokens = token_response.json()

    config = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type"),
        "expires_in": tokens.get("expires_in"),
        "vrn": vrn,
    }

    data_source = (
        db.query(DataSource)
        .filter(
            DataSource.organization_id == organization_id,
            DataSource.source_type == SourceType.HMRC_MTD,
        )
        .first()
    )

    if data_source:
        data_source.config = config
        data_source.is_active = True
    else:
        data_source = DataSource(
            organization_id=organization_id,
            name="HMRC MTD",
            source_type=SourceType.HMRC_MTD,
            config=config,
            is_active=True,
        )
        db.add(data_source)

    db.commit()
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/sources?connected=hmrc")
