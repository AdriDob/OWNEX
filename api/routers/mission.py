"""Mission Control API — unified hub that aggregates state across all ORION modules."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter

from core.app_registry import get_app_registry
from core.health.engine import get_health_center

logger = logging.getLogger("orion.mission")
router = APIRouter(prefix="/api/mission", tags=["mission"])


@router.get("/status")
async def mission_status():
    """Unified status snapshot — one call to know everything."""
    health = _get_health()
    registry = get_app_registry()
    apps_status = _get_apps_status(registry)
    next_action = _get_next_action()
    priorities = _get_priorities(registry)
    ingress = _get_ingress()
    return {
        "system": {
            "health_score": health.get("score", 0),
            "status": health.get("status", "unknown"),
            "timestamp": datetime.now(UTC).isoformat(),
        },
        "apps": apps_status,
        "next_action": next_action,
        "priorities": priorities,
        "ingress": ingress,
    }


@router.get("/priorities")
async def mission_priorities():
    """Only what needs attention — sorted by importance."""
    priorities = _get_priorities(get_app_registry())
    return {"priorities": priorities}


def _get_health() -> dict:
    try:
        hc = get_health_center()
        latest = hc.latest()
        if latest:
            return {
                "score": round(latest.score * 100),  # 0-100 for frontend
                "status": latest.status.value if hasattr(latest.status, "value") else latest.status,
                "checks": len(latest.checks),
            }
    except Exception as exc:
        logger.warning("[MISSION] Failed to read health: %s", exc)
    return {"score": 0, "status": "unknown", "checks": 0}


def _get_apps_status(registry) -> list[dict]:
    apps = []
    for app in registry.list_apps():
        apps.append(
            {
                "id": app.id,
                "name": app.name,
                "icon": app.icon,
                "version": app.version,
                "description": app.description,
                "has_db": bool(app.db_path),
                "providers": len(app.providers),
            }
        )
    return apps


def _get_next_action() -> dict | None:
    try:
        from cores.orion.next_action import get_next_action

        action = get_next_action()
        if action:
            return {
                "title": action.get("title", "Revisar sistema"),
                "why_now": action.get("reasoning", action.get("why_now", "")),
                "effort": action.get("effort", "medium"),
                "estimated_reward": action.get("estimated_reward", 0),
            }
    except Exception as exc:
        logger.warning("[MISSION] Next action unavailable: %s", exc)
    return None


def _get_priorities(registry) -> list[dict]:
    """Collect attention items from all modules."""
    priorities: list[dict] = []

    # Backup status
    try:
        from core.backup.engine import get_backup_engine

        be = get_backup_engine()
        backups = be.list_backups()
        if backups:
            latest = backups[0]
            created_at = datetime.fromisoformat(latest["created_at"])
            age = (datetime.now(UTC) - created_at).total_seconds() / 3600
            if age > 48:
                priorities.append(
                    {
                        "type": "backup",
                        "severity": "warning",
                        "title": "Backup desactualizado",
                        "detail": f"Último backup hace {int(age)} horas",
                    }
                )
        else:
            priorities.append(
                {
                    "type": "backup",
                    "severity": "high",
                    "title": "Sin backups",
                    "detail": "Nunca se realizó un backup del sistema",
                }
            )
    except Exception as exc:
        logger.warning("[MISSION] Backup check failed: %s", exc)

    # Unread notifications
    try:
        from cores.notifications.hub import get_notification_hub

        hub = get_notification_hub()
        unread = hub.unread_count()
        if unread > 0:
            priorities.append(
                {
                    "type": "notification",
                    "severity": "info",
                    "title": f"{unread} notificaciones sin leer",
                    "detail": "Revisar centro de notificaciones",
                }
            )
    except Exception:
        logger.warning("[MISSION] Notification check unavailable")

    # AEGIS pending targets
    try:
        from core.database.manager import get_db_manager

        db = get_db_manager().get_session("aegis")
        pending = db.execute("SELECT COUNT(*) FROM aegis_targets WHERE status = 'pending'").scalar() or 0
        open_findings = db.execute("SELECT COUNT(*) FROM aegis_vuln_findings WHERE status = 'open'").scalar() or 0
        db.close()
        if pending > 0:
            priorities.append(
                {
                    "type": "aegis",
                    "severity": "medium",
                    "title": f"{pending} targets pendientes en AEGIS",
                    "detail": "Ejecutar escaneo de reconocimiento",
                }
            )
        if open_findings > 0:
            priorities.append(
                {
                    "type": "aegis",
                    "severity": "high" if open_findings > 5 else "medium",
                    "title": f"{open_findings} findings abiertos en AEGIS",
                    "detail": "Revisar y clasificar vulnerabilidades",
                }
            )
    except Exception:
        logger.warning("[MISSION] AEGIS status unavailable")

    # Unconfirmed CATEYE findings
    try:
        from database import db as catdb

        findings = catdb.query(
            "SELECT COUNT(*) as cnt FROM findings WHERE status NOT IN ('confirmed', 'false_positive')"
        )
        if findings and findings[0]["cnt"] > 0:
            cnt = findings[0]["cnt"]
            priorities.append(
                {
                    "type": "cateye",
                    "severity": "medium",
                    "title": f"{cnt} hallazgos sin confirmar en CATEYE",
                    "detail": "Validar hallazgos pendientes",
                }
            )
    except Exception:
        logger.warning("[MISSION] CATEYE findings unavailable")

    return sorted(priorities, key=lambda p: {"high": 0, "warning": 1, "medium": 2, "info": 3}.get(p["severity"], 4))


def _get_ingress() -> dict:
    total_pending = 0
    total_confirmed = 0
    total_earned = 0
    try:
        from database import db as catdb

        rows = catdb.query(
            "SELECT SUM(CASE WHEN status = 'confirmed' THEN estimated_payout ELSE 0 END) as confirmed, SUM(CASE WHEN status = 'pending' THEN estimated_payout ELSE 0 END) as pending, SUM(estimated_payout) as total FROM findings"
        )
        if rows:
            r = rows[0]
            total_confirmed = r.get("confirmed", 0) or 0
            total_pending = r.get("pending", 0) or 0
            total_earned = r.get("total", 0) or 0
    except Exception:
        logger.warning("[MISSION] Ingress data unavailable")
    return {
        "confirmed": round(total_confirmed, 2),
        "pending": round(total_pending, 2),
        "total_earned": round(total_earned, 2),
    }
