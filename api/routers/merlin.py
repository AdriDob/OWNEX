"""MERLIN Intelligence API — brief, decisions, strategic memory."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("orion.merlin")
router = APIRouter(prefix="/api/merlin", tags=["merlin"])


@router.get("/brief")
async def merlin_brief():
    """Generate the current daily brief from system state."""
    try:
        from core.merlin import MerlinBrief

        brief = MerlinBrief()
        data = brief.generate()
        text = brief.format_text(data)
        brief.close()
        return {
            "success": True,
            "brief": text,
            "data": data,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.exception("Failed to generate MERLIN brief")
        return {"success": False, "error": str(e)}


@router.get("/decisions")
async def merlin_decisions(limit: int = 10):
    """List recent strategic decisions."""
    try:
        from core.merlin import MerlinDecisionLog, MerlinMemory

        mem = MerlinMemory()
        log = MerlinDecisionLog(memory=mem)
        insights = log.get_learning_insights()
        return {
            "success": True,
            "total_decisions": insights.get("total_decisions", 0),
            "resolved": insights.get("resolved", 0),
            "pending": insights.get("pending", 0),
            "categories": insights.get("categories", {}),
        }
    except Exception as e:
        logger.exception("Failed to get decisions")
        return {"success": False, "error": str(e)}


@router.post("/decisions")
async def record_decision(decision: dict[str, Any]):
    """Record a new strategic decision."""
    try:
        from core.merlin import MerlinDecisionLog, MerlinMemory

        mem = MerlinMemory()
        log = MerlinDecisionLog(memory=mem)
        log.record(
            decision_id=decision.get("id", f"dec_{datetime.now(timezone.utc).timestamp()}"),
            category=decision.get("category", "general"),
            description=decision.get("description", ""),
            expected_impact=decision.get("expected_impact", ""),
            confidence=decision.get("confidence", 0.5),
        )
        return {"success": True}
    except Exception as e:
        logger.exception("Failed to record decision")
        return {"success": False, "error": str(e)}


@router.get("/memory")
async def merlin_memory():
    """Get MERLIN's strategic context."""
    try:
        from core.merlin import MerlinMemory

        mem = MerlinMemory()
        ctx = mem.get_strategic_context()
        goals = mem.get_goals()
        return {
            "success": True,
            "strategic_context": ctx,
            "goals": goals,
        }
    except Exception as e:
        logger.exception("Failed to get MERLIN memory")
        return {"success": False, "error": str(e)}


@router.post("/memory/goals")
async def set_goals(goals: dict[str, Any]):
    """Set strategic goals."""
    try:
        from core.merlin import MerlinMemory

        mem = MerlinMemory()
        mem.set_goals(goals)
        return {"success": True, "goals": goals}
    except Exception as e:
        logger.exception("Failed to set goals")
        return {"success": False, "error": str(e)}
