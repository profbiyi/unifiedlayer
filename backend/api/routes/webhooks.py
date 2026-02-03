"""
Webhook ingestion routes.

Public endpoints for receiving push events from payment providers.
Authenticated endpoint for listing webhook events.
"""
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional, List
from ipaddress import ip_address, ip_network

from fastapi import APIRouter, Request, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.auth import get_current_user
from backend.models.pipeline import User
from backend.models.webhook import WebhookEvent, WebhookEventStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Safaricom M-Pesa IP ranges (production)
MPESA_ALLOWED_NETWORKS = [
    ip_network("196.201.214.0/24"),
    ip_network("196.201.213.0/24"),
    ip_network("196.201.212.0/24"),
]


def _verify_paystack_signature(payload_body: bytes, signature: str) -> bool:
    """Verify Paystack webhook signature using HMAC SHA-512."""
    secret = settings.PAYSTACK_WEBHOOK_SECRET or settings.PAYSTACK_SECRET_KEY
    if not secret:
        logger.warning("No Paystack secret configured for webhook verification")
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_flutterwave_signature(signature: str) -> bool:
    """Verify Flutterwave webhook by comparing verif-hash header."""
    secret = settings.FLUTTERWAVE_WEBHOOK_SECRET
    if not secret:
        logger.warning("No Flutterwave webhook secret configured")
        return False
    return hmac.compare_digest(secret, signature)


def _verify_gocardless_signature(payload_body: bytes, signature: str) -> bool:
    """Verify GoCardless webhook signature using HMAC SHA-256."""
    secret = settings.GOCARDLESS_WEBHOOK_SECRET if hasattr(settings, "GOCARDLESS_WEBHOOK_SECRET") else None
    if not secret:
        logger.warning("No GoCardless webhook secret configured")
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_mpesa_ip(client_ip: str) -> bool:
    """Verify the request originates from Safaricom IP ranges."""
    try:
        addr = ip_address(client_ip)
        return any(addr in network for network in MPESA_ALLOWED_NETWORKS)
    except ValueError:
        return False


@router.post("/{source_type}", status_code=status.HTTP_200_OK)
async def receive_webhook(
    source_type: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public endpoint to receive webhook events from payment providers.

    Verifies the signature/origin for each source type, stores the event,
    and returns 200 immediately. Processing happens asynchronously.

    Supported source types: paystack, flutterwave, gocardless, mpesa.
    Stripe webhooks are handled separately in billing routes.
    """
    valid_sources = {"paystack", "flutterwave", "gocardless", "mpesa"}
    if source_type not in valid_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported source type: {source_type}. Supported: {', '.join(sorted(valid_sources))}",
        )

    payload_body = await request.body()
    payload_json = await request.json()

    # Extract signature and verify based on source type
    signature_value: Optional[str] = None
    verified = False

    if source_type == "paystack":
        signature_value = request.headers.get("X-Paystack-Signature", "")
        verified = _verify_paystack_signature(payload_body, signature_value)

    elif source_type == "flutterwave":
        signature_value = request.headers.get("verif-hash", "")
        verified = _verify_flutterwave_signature(signature_value)

    elif source_type == "gocardless":
        signature_value = request.headers.get("Webhook-Signature", "")
        verified = _verify_gocardless_signature(payload_body, signature_value)

    elif source_type == "mpesa":
        client_ip = request.client.host if request.client else ""
        verified = _verify_mpesa_ip(client_ip)
        signature_value = f"ip:{client_ip}"

    if not verified:
        logger.warning(f"Webhook signature verification failed for {source_type}")
        # Still store the event but mark as failed
        event = WebhookEvent(
            source_type=source_type,
            event_type=payload_json.get("event", payload_json.get("type", "unknown")),
            payload=payload_json,
            signature=signature_value,
            status=WebhookEventStatus.FAILED,
            error_message="Signature verification failed",
        )
        db.add(event)
        db.commit()
        # Return 200 to prevent retries from providers that interpret non-200 as failure
        return {"status": "received", "verified": False}

    # Determine event type from payload (varies by provider)
    if source_type == "paystack":
        event_type = payload_json.get("event", "unknown")
    elif source_type == "flutterwave":
        event_type = payload_json.get("event", payload_json.get("event.type", "unknown"))
    elif source_type == "gocardless":
        events = payload_json.get("events", [])
        event_type = events[0].get("action", "unknown") if events else "unknown"
    elif source_type == "mpesa":
        event_type = payload_json.get("TransactionType", payload_json.get("ResultType", "unknown"))
    else:
        event_type = "unknown"

    event = WebhookEvent(
        source_type=source_type,
        event_type=str(event_type),
        payload=payload_json,
        signature=signature_value,
        status=WebhookEventStatus.RECEIVED,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info(f"Webhook event stored: {source_type}/{event_type} (id={event.id})")

    return {"status": "received", "verified": True, "event_id": str(event.public_id)}


@router.get("/events", status_code=status.HTTP_200_OK)
async def list_webhook_events(
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    event_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List webhook events for the current user's organization.

    Requires authentication.
    """
    query = db.query(WebhookEvent).filter(
        WebhookEvent.organization_id == current_user.organization_id
    )

    if source_type:
        query = query.filter(WebhookEvent.source_type == source_type)

    if event_status:
        query = query.filter(WebhookEvent.status == event_status)

    total = query.count()
    events = (
        query.order_by(WebhookEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [
            {
                "id": str(ev.public_id),
                "source_type": ev.source_type,
                "event_type": ev.event_type,
                "status": ev.status.value if ev.status else None,
                "error_message": ev.error_message,
                "processed_at": ev.processed_at,
                "created_at": ev.created_at,
            }
            for ev in events
        ],
    }
