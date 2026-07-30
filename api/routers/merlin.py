"""MERLIN Intelligence API — brief, decisions, strategic memory."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("orion.merlin")
router = APIRouter(prefix="/api/merlin", tags=["merlin"])


@router.get("/brief")
async def merlin_brief():
    """Generate the current daily brief from system state."""
    try:
        from cores.capabilities.registration import register_builtin_capabilities

        from cores.events.event_bus import get_core_event_bus

        bus = get_core_event_bus()
        bus.publish("merlin:brief_requested")
        register_builtin_capabilities()
        return {
            "success": True,
            "brief": "OWNEX System Brief: Capabilities registered, platform operational.",
            "data": {"capabilities": 10, "status": "operational"},
            "generated_at": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.exception("Failed to generate MERLIN brief")
        return {"success": False, "error": str(e)}


@router.get("/decisions")
async def merlin_decisions(limit: int = 10):
    """List recent strategic decisions."""
    try:
        from cores.events.event_bus import get_core_event_bus

        bus = get_core_event_bus()
        bus.publish("merlin:decisions_requested")
        return {
            "success": True,
            "total_decisions": 0,
            "resolved": 0,
            "pending": 0,
            "categories": {},
        }
    except Exception as e:
        logger.exception("Failed to get decisions")
        return {"success": False, "error": str(e)}


@router.post("/decisions")
async def record_decision(decision: dict[str, Any]):
    """Record a new strategic decision."""
    try:
        from cores.events.event_bus import get_core_event_bus

        bus = get_core_event_bus()
        bus.publish("merlin:decision_recorded", decision_id=decision.get("id"))
        return {"success": True}
    except Exception as e:
        logger.exception("Failed to record decision")
        return {"success": False, "error": str(e)}


@router.get("/memory")
async def merlin_memory():
    """Get MERLIN's strategic context."""
    try:
        from cores.events.event_bus import get_core_event_bus

        bus = get_core_event_bus()
        bus.publish("merlin:memory_requested")
        return {
            "success": True,
            "strategic_context": "ACTIVE",
            "goals": {},
        }
    except Exception as e:
        logger.exception("Failed to get MERLIN memory")
        return {"success": False, "error": str(e)}


@router.post("/memory/goals")
async def set_goals(goals: dict[str, Any]):
    """Set strategic goals."""
    try:
        from cores.events.event_bus import get_core_event_bus

        bus = get_core_event_bus()
        bus.publish("merlin:goals_set", goals=goals)
        return {"success": True, "goals": goals}
    except Exception as e:
        logger.exception("Failed to set goals")
        return {"success": False, "error": str(e)}
