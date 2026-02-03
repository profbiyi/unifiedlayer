"""
Destination Discovery API routes.

Endpoints for testing destination connections before saving.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models.pipeline import User
from backend.auth import get_current_user
from backend.utils.connection_tester import test_destination_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/destinations/discovery", tags=["Destination Discovery"])


class DestinationTestRequest(BaseModel):
    """Request to test a destination connection."""
    destination_type: str
    config: Dict[str, Any]


class DestinationTestResponse(BaseModel):
    """Response from destination connection test."""
    success: bool
    message: str
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/test-connection", response_model=DestinationTestResponse)
async def test_connection(
    request: DestinationTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test a destination connection.

    Validates credentials and connectivity without storing configuration.
    """
    logger.info(f"Testing destination connection for type: {request.destination_type}")

    try:
        # Use the connection tester
        success, message = test_destination_connection(
            request.destination_type,
            request.config
        )

        if success:
            return DestinationTestResponse(
                success=True,
                message=message,
                metadata={
                    "destination_type": request.destination_type,
                }
            )
        else:
            return DestinationTestResponse(
                success=False,
                message=message,
                error=message,
            )

    except Exception as e:
        logger.error(f"Destination connection test failed: {str(e)}", exc_info=True)
        return DestinationTestResponse(
            success=False,
            message="Connection test failed",
            error=str(e),
        )
