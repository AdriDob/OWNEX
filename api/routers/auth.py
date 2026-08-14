from fastapi import APIRouter, Header, Query, Request, Response

from api.middleware.auth_middleware import SESSION_COOKIE
from cores.audit_log import log_event
from cores.auth.auth_manager import get_auth_manager
from cores.auth.session_validator import get_session_validator
from cores.gateway.rate_limit import get_rate_limiter
from cores.gateway.schemas import error, ok

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = get_rate_limiter()

# Session cookie TTL matches the token TTL (30 days)
SESSION_COOKIE_MAX_AGE = 30 * 24 * 60 * 60


def _set_session_cookie(response: Response, token: str, secure: bool) -> None:
    """Set the httpOnly session cookie. The token remains available in the
    response body so the Bearer flow keeps working (incremental migration:
    cookie and header coexist, header wins in the middleware)."""
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
    )


@router.post("/login")
async def login(request: Request, response: Response):
    body = await request.json()
    device_id = body.get("device_id", "unknown")
    device_info = body.get("device_info", {})
    if not isinstance(device_info, dict):
        device_info = {"raw": str(device_info)}

    manager = get_auth_manager()
    result = manager.authenticate(device_id, device_info)

    if isinstance(result, dict) and result.get("token"):
        _set_session_cookie(response, result["token"], request.url.scheme == "https")

    log_event("login", actor=device_id, detail="Device authenticated")
    return ok(result)


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    body = await request.json()
    device_id = body.get("device_id")
    refresh_token = body.get("refresh_token")

    if not device_id or not refresh_token:
        return error("device_id and refresh_token required", version="1.0")

    manager = get_auth_manager()
    result = manager.refresh(device_id, refresh_token)

    if result is None:
        return error("Invalid or expired refresh token", version="1.0")

    if isinstance(result, dict) and result.get("token"):
        _set_session_cookie(response, result["token"], request.url.scheme == "https")

    return ok(result)


@router.post("/logout")
async def logout(request: Request, response: Response):
    device_id = ""
    try:
        body = await request.json()
        if isinstance(body, dict):
            device_id = body.get("device_id", "")
    except Exception:
        device_id = ""

    if device_id:
        manager = get_auth_manager()
        manager.logout(device_id)

    response.delete_cookie(SESSION_COOKIE, path="/")

    log_event("logout", actor=device_id or "unknown", detail="Device logged out")
    return ok({"status": "logged_out", "device_id": device_id})


@router.get("/me")
async def get_me(authorization: str | None = Header(None)):
    if not authorization:
        return error("Authorization header required", version="1.0")

    token = authorization.replace("Bearer ", "")
    validator = get_session_validator()
    result = validator.validate(token)

    if not result.valid:
        return error(result.reason or "Invalid session", version="1.0")

    return ok(
        {
            "device_id": result.device_id,
            "user_id": result.user_id,
            "authenticated": True,
        }
    )


@router.post("/validate")
async def validate_session(request: Request):
    body = await request.json()
    token = body.get("token", "")

    if not token:
        return error("token required", version="1.0")

    validator = get_session_validator()
    result = validator.validate(token)

    return ok(result.to_dict())


@router.get("/session")
async def get_session(device_id: str = Query(None)):
    if not device_id:
        return error("device_id query parameter required", version="1.0")

    manager = get_auth_manager()
    session = manager.get_session(device_id)

    if session is None:
        return error("Session not found", version="1.0")

    return ok(
        {
            "device_id": session["device_id"],
            "created_at": session.get("created_at"),
            "last_seen": session.get("last_seen"),
            "meta": session.get("meta", {}),
        }
    )


@router.get("/devices")
async def list_devices():
    manager = get_auth_manager()
    devices = manager.list_devices()
    return ok({"devices": devices, "total": len(devices)})


@router.get("/stats")
async def auth_stats():
    manager = get_auth_manager()
    return ok(manager.get_stats())


@router.post("/secure-token")
async def store_secure_token(request: Request):
    body = await request.json()
    device_id = body.get("device_id")
    token = body.get("token")

    if not device_id or not token:
        return error("device_id and token required", version="1.0")

    manager = get_auth_manager()
    manager.store_secure_token(device_id, token)

    log_event("token_stored", actor=device_id, detail="Secure token stored")
    return ok({"status": "stored"})


@router.get("/secure-token")
async def get_secure_token(device_id: str = Query(None)):
    if not device_id:
        return error("device_id query parameter required", version="1.0")

    manager = get_auth_manager()
    token = manager.get_secure_token(device_id)

    if token is None:
        return error("No secure token found", version="1.0")

    return ok({"token": token, "device_id": device_id})
