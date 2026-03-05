"""
WhatsApp Test Endpoint.

Provides a super-admin-only endpoint for verifying that the Twilio WhatsApp
integration is correctly configured.  This is intentionally a simple smoke-test
route — it must NOT be exposed to regular users.

Register in main.py:
    from backend.api.routes.whatsapp_test import router as whatsapp_test_router
    app.include_router(whatsapp_test_router, prefix="/api/v1")
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.auth import require_super_admin
from backend.models.pipeline import User
from backend.notifications import send_whatsapp_notification, WhatsAppNotificationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin - WhatsApp Test"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class WhatsAppTestRequest(BaseModel):
    """Payload for the test-whatsapp endpoint."""
    to_number: str
    """
    Recipient phone number in E.164 format, e.g. ``+2348012345678``.
    The ``whatsapp:`` Twilio scheme prefix is added automatically if absent.
    """
    message: Optional[str] = "Test from UnifiedLayer"
    """Custom message body (defaults to a standard test phrase)."""


class WhatsAppTestResponse(BaseModel):
    """Result of the test-whatsapp call."""
    success: bool
    message: str
    to_number: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/test-whatsapp",
    response_model=WhatsAppTestResponse,
    summary="Send a test WhatsApp message (super admin only)",
    description=(
        "Sends a WhatsApp message via the configured Twilio account. "
        "Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and "
        "TWILIO_WHATSAPP_FROM to be set in the environment. "
        "Only accessible to super admins."
    ),
)
async def test_whatsapp(
    request: WhatsAppTestRequest,
    current_user: User = Depends(require_super_admin),
) -> WhatsAppTestResponse:
    """
    Send a test WhatsApp message to verify Twilio credentials.

    Args:
        request: Contains ``to_number`` and an optional ``message``.
        current_user: Must be a super admin (enforced by dependency).

    Returns:
        WhatsAppTestResponse indicating delivery success or failure.
    """
    logger.info(
        "Super admin %s (id=%s) triggering WhatsApp test to %s",
        current_user.email,
        current_user.id,
        request.to_number,
    )

    title = "UnifiedLayer WhatsApp Test"
    body = request.message or "Test from UnifiedLayer"

    try:
        delivered = send_whatsapp_notification(
            to_number=request.to_number,
            title=title,
            message=body,
        )
    except WhatsAppNotificationError as exc:
        # send_whatsapp_notification already swallows these, but guard anyway.
        logger.warning("WhatsApp test failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WhatsApp delivery failed: {exc}",
        )

    if delivered:
        return WhatsAppTestResponse(
            success=True,
            message="WhatsApp message sent successfully. Check the recipient's device.",
            to_number=request.to_number,
        )

    # Delivered == False means credentials not configured or twilio not installed.
    return WhatsAppTestResponse(
        success=False,
        message=(
            "Message not sent. Check that TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "and TWILIO_WHATSAPP_FROM are set, and that the twilio package is "
            "installed (pip install 'twilio>=9.0.0')."
        ),
        to_number=request.to_number,
    )
