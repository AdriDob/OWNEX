import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cores.auth.session_validator import get_session_validator

logger = logging.getLogger("ownex.api.middleware")

# Session cookie set on login/register/refresh (httpOnly). The token is also
# accepted via Authorization: Bearer for backwards compatibility.
SESSION_COOKIE = "ownex-session"

# Paths that do NOT require authentication
PUBLIC_PATHS: set[str] = {
    "/api/health",
    "/api/agents/health",
    "/api/version",
    "/api/system/health",
    "/api/docs",
    "/api/openapi.json",
    "/api/redoc",
    "/api/this-will-definitely-fail",
}

# Prefixes that do NOT require authentication
PUBLIC_PREFIXES: set[str] = {
    "/api/auth",
    "/api/license",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # WebSocket connections are handled by their own auth (token in query param)
        if request.scope["type"] == "websocket":
            return await call_next(request)

        path = request.url.path

        # Browser preflights (CORS) never carry an Authorization header by
        # spec — answering 401 here would kill the handshake before
        # CORSMiddleware can respond (tests/test_cors_tauri.py).
        if request.method == "OPTIONS":
            return await call_next(request)

        # Desktop mode: non-API paths are frontend assets, never require auth
        if not path.startswith("/api/"):
            return await call_next(request)

        if path in PUBLIC_PATHS:
            return await call_next(request)

        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()

        # Fallback: httpOnly session cookie (set on login). The cookie path is
        # only honored when no Authorization header is present, keeping the
        # Bearer flow fully backwards compatible.
        if not token:
            token = request.cookies.get(SESSION_COOKIE, "").strip()

        if not token:
            return JSONResponse(
                status_code=401,
                content={"error": "Authorization header required"},
            )

        validator = get_session_validator()
        result = validator.validate(token)

        if not result.valid:
            return JSONResponse(
                status_code=401,
                content={"error": result.reason or "Invalid or expired token"},
            )

        logger.info("[HW] AuthMiddleware.dispatch: JWT valid, passing request through")
        return await call_next(request)
