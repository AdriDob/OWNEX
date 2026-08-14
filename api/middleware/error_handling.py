import logging
import uuid

from fastapi import Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("ownex.error")

_SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' ws:; frame-ancestors 'none'; form-action 'self'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}

_GENERIC_500 = "Internal server error"


def _new_operation_id() -> str:
    return uuid.uuid4().hex


def _operation_id_of(request: Request) -> str:
    return getattr(request.state, "operation_id", None) or _new_operation_id()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.operation_id = _new_operation_id()
        try:
            response = await call_next(request)
            response.headers["X-Operation-Id"] = request.state.operation_id
            return response
        except Exception:
            logger.exception(
                "unhandled_exception operation_id=%s router=%s operation=%s",
                request.state.operation_id,
                request.url.path,
                request.method,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": _GENERIC_500, "operation_id": request.state.operation_id},
                headers={"X-Operation-Id": request.state.operation_id},
            )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Reemplaza el handler por defecto de HTTPException.

    Errores 5xx: nunca exponen el detalle interno al cliente; se loguean de
    forma estructurada (operation_id, router, operación, detalle original) y se
    devuelve un mensaje genérico. Errores 4xx: el detail es intencional y se
    preserva tal cual.
    """
    operation_id = _operation_id_of(request)
    if exc.status_code >= 500:
        logger.error(
            "http_exception operation_id=%s router=%s operation=%s status=%d detail=%s",
            operation_id,
            request.url.path,
            request.method,
            exc.status_code,
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": _GENERIC_500, "operation_id": operation_id},
            headers={"X-Operation-Id": operation_id},
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
