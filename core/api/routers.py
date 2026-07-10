"""ORION Core — platform-level FastAPI routers.

These endpoints are mounted by the ORION Platform shell and
are independent of any specific app.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.app_registry import get_app_registry
from core.database.manager import get_db_manager
from core.decision_journal import get_decisions as dj_get
from core.decision_journal import record_outcome as dj_outcome
from core.extension.hooks import get_hook_registry
from core.extension.registry import get_extension_registry
from core.health.engine import get_health_center
from core.integrations import init_integration_registry
from core.scheduler.scheduler import get_core_scheduler
from core.secrets.manager import get_secrets_manager

logger = logging.getLogger("orion.core.api")
router = APIRouter(prefix="/api/core", tags=["core"])


@router.get("/apps")
async def list_apps():
    """List all registered ORION Platform apps."""
    registry = get_app_registry()
    apps = registry.list_apps()
    return [
        {
            "id": app.id,
            "name": app.name,
            "version": app.version,
            "description": app.description,
            "icon": app.icon,
            "order": app.order,
            "has_agent": app.agent_class is not None,
            "has_db": bool(app.db_path),
            "frontend_routes": [{"path": r["path"], "name": r["name"]} for r in app.frontend_routes],
            "widgets": app.widgets,
            "providers": app.providers,
            "requires_auth": app.requires_auth,
            "hidden": app.hidden,
        }
        for app in apps
    ]


@router.get("/status")
async def core_status():
    """Platform-wide health status."""
    registry = get_app_registry()
    db = get_db_manager()
    scheduler = get_core_scheduler()
    ext_registry = get_extension_registry()

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "apps": registry.status(),
        "extensions": ext_registry.status(),
        "databases": db.list_databases(),
        "scheduler_jobs": len(scheduler._jobs) if hasattr(scheduler, "_jobs") else 0,
    }


# ── Extension endpoints ──────────────────────────────


@router.get("/extensions")
async def list_extensions():
    """List all discovered extensions and their status."""
    registry = get_extension_registry()
    return registry.status()


@router.post("/extensions/{extension_id}/load")
async def load_extension(extension_id: str):
    """Load (activate) an extension."""
    registry = get_extension_registry()
    ok = registry.load(extension_id)
    return {"extension_id": extension_id, "loaded": ok}


@router.post("/extensions/{extension_id}/unload")
async def unload_extension(extension_id: str):
    """Unload (deactivate) an extension."""
    registry = get_extension_registry()
    ok = registry.unload(extension_id)
    return {"extension_id": extension_id, "unloaded": ok}


@router.get("/hooks")
async def list_hooks():
    """List all registered hook points and their handlers."""
    registry = get_hook_registry()
    return {"hooks": registry.list_hooks()}


@router.get("/capabilities")
async def list_capabilities():
    """List all registered capabilities."""
    from core.extension.capabilities import get_capability_registry

    registry = get_capability_registry()
    return {"capabilities": registry.list_capabilities()}


# ── Secrets endpoints ────────────────────────────────


class SecretRequest(BaseModel):
    value: str


@router.get("/secrets")
async def list_secrets():
    """List secret keys (not values)."""
    manager = get_secrets_manager()
    return {"keys": manager.list_keys()}


@router.get("/secrets/health")
async def secrets_health():
    """Check if secrets backend is available."""
    manager = get_secrets_manager()
    return {"secrets": manager.health()}


@router.get("/secrets/{key}")
async def get_secret(key: str):
    """Get a secret value."""
    manager = get_secrets_manager()
    try:
        value = manager.get_or_raise(key)
        return {"key": key, "value": value, "found": True}
    except KeyError:
        return JSONResponse({"key": key, "found": False, "error": "Secret not found"}, status_code=404)


@router.put("/secrets/{key}")
async def set_secret(key: str, body: SecretRequest):
    """Store a secret."""
    manager = get_secrets_manager()
    ok = manager.set(key, body.value)
    return {"key": key, "stored": ok}


@router.delete("/secrets/{key}")
async def delete_secret(key: str):
    """Delete a secret."""
    manager = get_secrets_manager()
    ok = manager.delete(key)
    return {"key": key, "deleted": ok}


# ── Health endpoints ─────────────────────────────────


@router.get("/health")
async def platform_health():
    """Unified health status — green / yellow / red."""
    center = get_health_center()
    summary = center.summary()
    return summary


@router.post("/health/run")
async def run_health_check():
    """Run all health checks now."""
    center = get_health_center()
    snapshot = center.run_all()
    return {
        "status": snapshot.status,
        "timestamp": snapshot.timestamp.isoformat(),
        "checks": snapshot.checks,
        "details": snapshot.details,
    }


@router.get("/health/checks")
async def list_health_checks():
    """List all registered health checks."""
    center = get_health_center()
    return {"checks": center.list_checks()}


# ── Integration Center endpoints ─────────────────────


@router.get("/integrations")
async def list_integrations():
    """List all discovered integrations with current status."""
    registry = init_integration_registry()
    registry.refresh()
    return registry.summary()


@router.get("/integrations/{name}")
async def get_integration_status(name: str):
    """Get status for a single integration."""
    registry = init_integration_registry()
    status = registry.check(name)
    if status is None:
        return JSONResponse({"error": f"Integration '{name}' not found"}, status_code=404)
    return status.to_dict()


@router.post("/integrations/{name}/test")
async def test_integration(name: str):
    """Test a specific integration connection."""
    registry = init_integration_registry()
    status = registry.check(name)
    if status is None:
        return JSONResponse({"error": f"Integration '{name}' not found"}, status_code=404)
    return {
        "name": status.name,
        "status": status.status,
        "error": status.error,
        "checked_at": status.checked_at,
    }


# ── Decision Journal endpoints ──────────────────────


@router.get("/decisions")
async def list_decisions(
    app_id: str | None = None,
    agent_id: str | None = None,
    outcome: str | None = None,
    limit: int = 100,
):
    """Query the decision journal with optional filters."""
    return {"decisions": dj_get(app_id=app_id, agent_id=agent_id, outcome=outcome, limit=limit)}


@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str):
    """Get a single decision by ID."""
    decisions = dj_get(limit=1000)
    for d in decisions:
        if d["decision_id"] == decision_id:
            return d
    return JSONResponse({"error": f"Decision '{decision_id}' not found"}, status_code=404)


class OutcomeRequest(BaseModel):
    outcome: str
    reward: float = 0.0
    notes: str = ""


@router.post("/decisions/{decision_id}/outcome")
async def record_decision_outcome(decision_id: str, body: OutcomeRequest):
    """Record the outcome of a previous decision."""
    ok = dj_outcome(decision_id, outcome=body.outcome, reward=body.reward, notes=body.notes)
    if not ok:
        return JSONResponse({"error": f"Decision '{decision_id}' not found"}, status_code=404)
    return {"decision_id": decision_id, "outcome": body.outcome, "recorded": True}
