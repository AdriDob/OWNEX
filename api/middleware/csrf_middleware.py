"""CSRF middleware using double-submit cookie pattern.

A cryptographically random token is set as a cookie (`csrf-token`) on GET
requests.  State-changing requests (POST, PUT, DELETE, PATCH) must include
the same token in the `X-CSRF-Token` header.  The server compares the two —
no server-side session store needed.

Safe methods (GET, HEAD, OPTIONS, TRACE) are exempt.
Disabled only when CATEYE_CSRF_DISABLED=1 (explicit opt-out).
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("cateye.csrf")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
COOKIE_NAME = "csrf-token"
HEADER_NAME = "X-CSRF-Token"
TOKEN_BYTES = 32

EXEMPT_PATHS = frozenset({
    "/api/health",
    "/api/license/activate",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/desktop-session",
})


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # WebSocket connections bypass CSRF (token in query param or handled separately)
        if request.scope["type"] == "websocket":
            return await call_next(request)

        # Disabled only when explicitly opted out
        if os.environ.get("CATEYE_CSRF_DISABLED"):
            return await call_next(request)

        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        if request.method in SAFE_METHODS:
            response = await call_next(request)
            if request.method == "GET" and not request.cookies.get(COOKIE_NAME):
                token = secrets.token_hex(TOKEN_BYTES)
                response.set_cookie(
                    key=COOKIE_NAME,
                    value=token,
                    httponly=True,
                    samesite="lax",
                    max_age=3600,
                )
            return response

        cookie_token = request.cookies.get(COOKIE_NAME, "")
        header_token = request.headers.get(HEADER_NAME, "")

        if not cookie_token or not header_token:
            logger.warning("CSRF check failed: missing cookie or header")
            return Response("CSRF validation failed", status_code=403)

        if not hmac.compare_digest(cookie_token, header_token):
            logger.warning("CSRF check failed: token mismatch")
            return Response("CSRF validation failed", status_code=403)

        return await call_next(request)
