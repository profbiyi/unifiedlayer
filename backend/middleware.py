"""
Security and rate limiting middleware.

Provides request rate limiting, security headers,
and request validation middleware.
"""
import time
from typing import Dict, Optional, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from backend.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.

    Implements token bucket algorithm for rate limiting.
    """

    def __init__(self, app, requests_per_minute: int = 100):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute in seconds

        # Storage: {ip_address: [(timestamp, count)]}
        self.request_counts: Dict[str, list] = defaultdict(list)

    def _clean_old_requests(self, ip_address: str, current_time: float) -> None:
        """
        Remove requests outside the current time window.

        Args:
            ip_address: Client IP address
            current_time: Current timestamp
        """
        if ip_address in self.request_counts:
            self.request_counts[ip_address] = [
                (timestamp, count)
                for timestamp, count in self.request_counts[ip_address]
                if current_time - timestamp < self.window_size
            ]

    def _get_request_count(self, ip_address: str, current_time: float) -> int:
        """
        Get number of requests in current window.

        Args:
            ip_address: Client IP address
            current_time: Current timestamp

        Returns:
            Number of requests in current window
        """
        self._clean_old_requests(ip_address, current_time)

        if ip_address not in self.request_counts:
            return 0

        return sum(count for _, count in self.request_counts[ip_address])

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response

        Raises:
            HTTPException: If rate limit exceeded
        """
        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Check rate limit
        request_count = self._get_request_count(client_ip, current_time)

        if request_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(self.window_size)},
            )

        # Record this request
        self.request_counts[client_ip].append((current_time, 1))

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - request_count - 1)
        )
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_size))

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware.

    Adds security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Add security headers to response.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response with security headers
        """
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Request size limit middleware.

    Prevents large request bodies that could cause DoS.
    """

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        """
        Initialize request size limiter.

        Args:
            app: FastAPI application
            max_size: Maximum request size in bytes
        """
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        """
        Check request size.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response

        Raises:
            HTTPException: If request too large
        """
        # Check Content-Length header
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > self.max_size:
            logger.warning(
                f"Request size ({content_length} bytes) exceeds limit ({self.max_size} bytes)"
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request body too large. Maximum size is {self.max_size} bytes.",
            )

        return await call_next(request)


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Stricter rate limiting for authentication endpoints.

    Applies aggressive rate limits to prevent brute force attacks on:
    - /auth/login
    - /auth/forgot-password
    - /auth/reset-password
    - /auth/register
    """

    # Auth endpoints with their specific limits (requests per minute)
    AUTH_ENDPOINTS = {
        "/auth/login": 10,  # 10 login attempts per minute
        "/auth/forgot-password": 5,  # 5 password reset requests per minute
        "/auth/reset-password": 5,  # 5 password reset attempts per minute
        "/auth/register": 5,  # 5 registration attempts per minute
        "/invitations/accept": 10,  # 10 invitation accepts per minute
    }

    def __init__(self, app):
        """Initialize auth rate limiter."""
        super().__init__(app)
        self.window_size = 60  # 1 minute in seconds
        # Storage: {endpoint: {ip_address: [(timestamp, count)]}}
        self.request_counts: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

    def _get_endpoint_key(self, path: str) -> Optional[str]:
        """Check if path matches any auth endpoint."""
        for endpoint in self.AUTH_ENDPOINTS:
            if path.startswith(endpoint):
                return endpoint
        return None

    def _clean_old_requests(self, endpoint: str, ip_address: str, current_time: float) -> None:
        """Remove requests outside the current time window."""
        if ip_address in self.request_counts[endpoint]:
            self.request_counts[endpoint][ip_address] = [
                (timestamp, count)
                for timestamp, count in self.request_counts[endpoint][ip_address]
                if current_time - timestamp < self.window_size
            ]

    def _get_request_count(self, endpoint: str, ip_address: str, current_time: float) -> int:
        """Get number of requests in current window for specific endpoint."""
        self._clean_old_requests(endpoint, ip_address, current_time)

        if ip_address not in self.request_counts[endpoint]:
            return 0

        return sum(count for _, count in self.request_counts[endpoint][ip_address])

    async def dispatch(self, request: Request, call_next):
        """Process request with auth-specific rate limiting."""
        # Only apply to POST requests on auth endpoints
        if request.method != "POST":
            return await call_next(request)

        endpoint_key = self._get_endpoint_key(request.url.path)
        if not endpoint_key:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check X-Forwarded-For header (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        current_time = time.time()
        limit = self.AUTH_ENDPOINTS[endpoint_key]

        # Check rate limit
        request_count = self._get_request_count(endpoint_key, client_ip, current_time)

        if request_count >= limit:
            logger.warning(
                f"Auth rate limit exceeded for IP: {client_ip} on endpoint: {endpoint_key}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Please wait before trying again.",
                headers={"Retry-After": str(self.window_size)},
            )

        # Record this request
        self.request_counts[endpoint_key][client_ip].append((current_time, 1))

        # Process request
        response = await call_next(request)

        # Add rate limit headers for auth endpoints
        response.headers["X-Auth-RateLimit-Limit"] = str(limit)
        response.headers["X-Auth-RateLimit-Remaining"] = str(max(0, limit - request_count - 1))
        response.headers["X-Auth-RateLimit-Reset"] = str(int(current_time + self.window_size))

        return response


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    IP whitelist middleware (optional).

    Restricts access to whitelisted IP addresses.
    """

    def __init__(self, app, allowed_ips: Optional[list] = None):
        """
        Initialize IP whitelist.

        Args:
            app: FastAPI application
            allowed_ips: List of allowed IP addresses (None = allow all)
        """
        super().__init__(app)
        self.allowed_ips = set(allowed_ips) if allowed_ips else None

    async def dispatch(self, request: Request, call_next):
        """
        Check IP whitelist.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response

        Raises:
            HTTPException: If IP not whitelisted
        """
        # If no whitelist configured, allow all
        if not self.allowed_ips:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else None

        # Check X-Forwarded-For header (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        if client_ip not in self.allowed_ips:
            logger.warning(f"Access denied for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return await call_next(request)
