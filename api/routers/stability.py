"""Stability Guardian API — consolidated SYSTEM STATUS panel.

Reuses existing engines instead of duplicating them:

- HealthCenter (core/health)       → Core / Memory / Agents / Security checks
- CapabilityRegistry (core/capabilities) → Tools panel
- backup engine (core/backup)      → Storage panel (latest backup, size)
- UpdateManager (core/update)      → Updates panel (available / none)
- core/version                     → current version + codename
- version history (core/system/version_engine) → rollback availability

GET /api/stability/status — single endpoint, full SYSTEM STATUS.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException

from core.backup.engine import backup_status
from core.capabilities.registry import get_capability_registry
from core.health.engine import get_health_center
from core.update.engine import UpdateManager
from core.version import OWNEX_CODENAME, OWNEX_VERSION

logger = logging.getLogger("orion.stability")

router = APIRouter(prefix="/api/stability", tags=["stability"])


def _rollback_status() -> dict[str, Any]:
    """Rollback availability from the update engine history."""
    try:
        history = UpdateManager().get_history(limit=3)
        return {
            "rollback_available": len(history) > 1,
            "previous_versions": [h.get("version") for h in history[1:]],
            "history_count": len(history),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Version history unavailable: %s", exc)
        return {"rollback_available": False, "previous_versions": [], "history_count": 0}


@router.get("/tools")
def tool_ecosystem() -> dict[str, Any]:
    """Tool Ecosystem inventory: metadata, usage frequency, keep/remove decisions."""
    from cores.tools.ecosystem import get_tool_ecosystem

    try:
        ecosystem = get_tool_ecosystem()
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "summary": ecosystem.summary(),
            "tools": ecosystem.inventory(),
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Tool ecosystem failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Tool ecosystem failed: {exc}") from exc


@router.get("/status")
def stability_status() -> dict[str, Any]:
    """Full SYSTEM STATUS panel: Core, Memory, Agents, Tools, Storage, Security, Updates."""
    try:
        center = get_health_center()
        health = center.unified_summary()

        # Panel grouping: map check names to protocol sections
        def _section(names: list[str]) -> dict[str, Any]:
            details = {n: v for n, v in health["checks"]["details"].items() if n in names}
            return {
                "healthy": all(details.values()) if details else None,
                "checks": details,
            }

        tools = get_capability_registry().stats()
        storage = backup_status()
        try:
            updates = UpdateManager().status()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Update status unavailable: %s", exc)
            updates = {"update_available": None, "current_version": OWNEX_VERSION}

        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "version": {"current": OWNEX_VERSION, "codename": OWNEX_CODENAME},
            "system": {
                "status": health["status"],
                "score": health["score"],
                "uptime_seconds": health["process"]["uptime_seconds"],
                "memory_rss_mb": health["process"]["memory_rss_mb"],
                "cpu_percent": health["process"]["cpu_percent"],
            },
            "sections": {
                "core": _section(["event_bus", "scheduler", "database", "hook_registry"]),
                "memory": _section(["memory"]),
                "agents": _section(["agent_bus", "agents_health"]),
                "security": _section(["identity_vault"]),
                "tools": {
                    "healthy": tools.get("broken", 0) == 0,
                    "integrated": tools.get("unique_capabilities", 0),
                    "active": tools.get("active", 0),
                    "broken": tools.get("broken", 0),
                    "categories": tools.get("categories", []),
                },
                "storage": {
                    "healthy": storage.get("total_backups", 0) > 0,
                    "total_backups": storage.get("total_backups", 0),
                    "latest_backup": storage.get("latest_backup"),
                    "total_backup_size_mb": storage.get("total_backup_size_mb", 0.0),
                },
                "updates": {
                    "available": updates.get("update_available"),
                    "remote_version": updates.get("remote_version"),
                    "last_checked": updates.get("last_checked"),
                    "rollback": _rollback_status(),
                },
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Stability status failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Stability status failed: {exc}") from exc
