"""OWNEX Internal Sessions — sesión interna para operaciones del sistema.

Diferente al auth de usuario (login/register). Este provee tokens firmados
para operaciones internas: Work Bank, conexiones, sincronización.
"""

from typing import Any

from fastapi import APIRouter, Request, Response

from cores.auth.auth_manager import get_auth_manager
from cores.auth.session_validator import get_session_validator
from cores.gateway.schemas import error, ok

# Sessions router for internalOWNEX operations
sessions_router = APIRouter(prefix="/api/internal/sessions", tags=["internal-sessions"])

TOKEN_TTL = 30 * 24 * 60 * 60  # 30 días


def _create_internal_token(device_id: str, meta: dict | None = None) -> dict[str, Any]:
    """Crear un token internoOWNEX para el device_id dado."""
    manager = get_auth_manager()
    # Usar el store del auth manager para crear una sesión interna
    session = manager._store.create_session(device_id, meta=meta or {})
    token = session.get("token", "")
    return {"token": token, "device_id": device_id, "ttl": TOKEN_TTL}


@sessions_router.post("/create")
async def create_internal_session(request: Request):
    """Crear sesiónOWNEX interna para operaciones del sistema.

    Body: {"device_id": "optional", "meta": {...}}
    Retorna: {"token": "...", "device_id": "...", "expires_at": "..."}
    """
    body = await request.json()
    device_id = body.get("device_id") or "unknown-ownex-frontend"
    meta = body.get("meta", {})

    result = _create_internal_token(device_id, meta)

    # También establecer cookie httpOnly para consistencia
    response = Response(content=None, status_code=200)
    from api.middleware.auth_middleware import _set_session_cookie

    _set_session_cookie(response, result["token"], request.url.scheme == "https")

    return ok(
        {
            "token": result["token"],
            "device_id": result["device_id"],
            "expires_at": int(__import__("time").time()) + TOKEN_TTL,
        }
    )


@sessions_router.post("/validate")
async def validate_internal_session(request: Request):
    """Validar sesiónOWNEX interna.

    Body: {"token": "..."}
    Retorna: validación completa del token
    """
    body = await request.json()
    token = body.get("token", "")

    if not token:
        return error("token requerido", version="1.0")

    validator = get_session_validator()
    result = validator.validate(token)

    if not result.valid:
        return error(result.reason or "Sesión inválida o expirada", version="1.0")

    return ok(result.to_dict())


@sessions_router.post("/refresh")
async def refresh_internal_session(request: Request):
    """Refrescar sesiónOWNEX interna.

    Body: {"token": "..."}
    Retorna: nuevo token si la refresh es válida
    """
    body = await request.json()
    token = body.get("token", "")

    if not token:
        return error("token requerido", version="1.0")

    manager = get_auth_manager()
    result = manager.refresh("ownex-internal", token)

    if result is None:
        return error("Token inválido o expirado", version="1.0")

    return ok({"token": result.get("token", ""), "expires_at": int(__import__("time").time()) + TOKEN_TTL})
