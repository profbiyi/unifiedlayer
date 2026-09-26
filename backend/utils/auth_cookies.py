"""
Auth cookie helpers.

The access token and refresh token are delivered as httpOnly cookies so that
JavaScript can never read them — an XSS on the frontend then cannot exfiltrate a
session (the browser still attaches the cookie automatically, but the token value
is out of reach).

This requires the browser to treat the API as same-origin with the app; in
production that is arranged by the Next.js rewrite that proxies ``/api/*`` to the
backend, so these cookies are first-party. SameSite=Lax is the CSRF defense: the
API only mutates on non-GET requests, and Lax cookies are not sent on cross-site
non-GET requests.
"""
from __future__ import annotations

from fastapi import Response

from backend.config import settings

ACCESS_COOKIE = "token"
REFRESH_COOKIE = "refresh_token"


def _is_prod() -> bool:
    return settings.ENVIRONMENT == "production"


# Cookies are host-only (no Domain attribute). With the same-origin Next.js proxy
# the app and API share a host, so a host-only cookie is attached correctly in dev,
# test, and production — and it avoids the domain-mismatch pitfalls of pinning a
# Domain (e.g. "localhost") that a different request host would reject.


def set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=_is_prod(),
        path="/",
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax",
        secure=_is_prod(),
        path="/",
    )


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set both auth cookies on a response (login / 2FA verify / refresh)."""
    set_access_cookie(response, access_token)
    set_refresh_cookie(response, refresh_token)


def clear_auth_cookies(response: Response) -> None:
    """Clear both auth cookies (logout)."""
    for key in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(
            key=key,
            path="/",
            samesite="lax",
        )
