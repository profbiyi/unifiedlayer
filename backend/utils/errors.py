"""
Standardized error response format.

Provides consistent error response structure across the API
with error codes, request correlation, and timestamps.
"""
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """
    Standardized error response format.

    Attributes:
        code: Error code identifier (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        message: Human-readable error message
        status: HTTP status code
        request_id: Correlation ID for request tracing (optional)
        timestamp: ISO 8601 timestamp when error occurred
        details: Additional error details (optional)
    """
    code: str
    message: str
    status: int
    request_id: Optional[str] = None
    timestamp: str = None
    details: Optional[Dict[str, Any]] = None

    def __init__(self, **data):
        if "timestamp" not in data or data.get("timestamp") is None:
            data["timestamp"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        super().__init__(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {
            "code": self.code,
            "message": self.message,
            "status": self.status,
            "timestamp": self.timestamp,
        }
        if self.request_id:
            result["request_id"] = self.request_id
        if self.details:
            result["details"] = self.details
        return result


class ErrorCodes:
    """
    Standard error codes for the API.

    Use these constants to ensure consistent error codes across the application.
    """
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    CONFLICT = "CONFLICT"
    BAD_REQUEST = "BAD_REQUEST"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Domain-specific errors
    CONNECTION_FAILED = "CONNECTION_FAILED"
    PIPELINE_FAILED = "PIPELINE_FAILED"
    PIPELINE_NOT_FOUND = "PIPELINE_NOT_FOUND"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    DESTINATION_NOT_FOUND = "DESTINATION_NOT_FOUND"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    BILLING_ERROR = "BILLING_ERROR"


def get_request_id(request) -> Optional[str]:
    """
    Extract request ID from request state.

    Args:
        request: FastAPI/Starlette Request object

    Returns:
        Request ID string or None if not available
    """
    try:
        return getattr(request.state, 'request_id', None)
    except AttributeError:
        return None
