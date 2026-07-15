"""COPILOT API — query system-wide recommendations and agent status."""

from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger("cateye.api.copilot")

router = APIRouter(prefix="/api/copilot", tags=["copilot"])

_copilot_instance = None


def _set_copilot(instance: object) -> None:
    global _copilot_instance
    _copilot_instance = instance


@router.get("/status")
def copilot_status():
    """Return COPILOT agent status and capabilities."""
    if _copilot_instance is None:
        return {"status": "unavailable", "agent_id": None, "authority": None}
    try:
        d = _copilot_instance.to_dict()
        return {
            "status": "active",
            "agent_id": d.get("agent_id"),
            "authority": d.get("authority"),
            "config": d.get("config"),
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/recommendations")
def copilot_recommendations():
    """Get top system-wide COPILOT recommendations."""
    if _copilot_instance is None:
        return {"status": "unavailable", "recommendations": []}
    try:
        from database import db

        actions = _copilot_instance.recommend_for_system(db_factory=db.SessionLocal)
        return {"status": "ok", "recommendations": actions}
    except Exception as exc:
        logger.warning("[COPILOT] Recommendations error: %s", exc)
        return {"status": "error", "recommendations": [], "detail": str(exc)}
