"""ORION Core — platform-level FastAPI routers.

These endpoints are mounted by the ORION Platform shell and
are independent of any specific app.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from core.app_registry import get_app_registry
from core.database.manager import get_db_manager
from core.scheduler.scheduler import get_core_scheduler

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
            "frontend_routes": [
                {"path": r["path"], "name": r["name"]} for r in app.frontend_routes
            ],
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

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "apps": registry.status(),
        "databases": db.list_databases(),
        "scheduler_jobs": len(scheduler._jobs) if hasattr(scheduler, "_jobs") else 0,
    }
