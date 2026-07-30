"""Rate limit middleware — per-IP + per-user-id rate limiting."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cores.auth.auth import verify_token
from cores.gateway.rate_limit import get_rate_limiter

logger = logging.getLogger("ownex.api.rate_limit")

NO_LIMIT_PREFIXES = {"/api/health", "/api/version", "/api/docs", "/api/openapi.json", "/api/redoc"}


def _resolve_identity(request: Request) -> str:
    client_ip = request.client.host if request.client else "unknown"
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            data = verify_token(auth[7:])
            if data:
                return data.get("sub", client_ip)
        except Exception as exc:
            logger.warning("Failed to verify token for rate limit: %s", exc)
    return client_ip


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in NO_LIMIT_PREFIXES:
            return await call_next(request)

        identity = _resolve_identity(request)
        key = f"{path}:{identity}"
        limiter = get_rate_limiter()

        if not limiter.consume(key):
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests", "retry_after": "1s"},
                headers={"X-RateLimit-Remaining": "0"},
            )

        remaining = limiter.remaining(key)
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(int(remaining))
        return response
