"""ORION Context Engine API — unified decision, action, and system-state endpoints.

All endpoints aggregate existing system data. No mock data. No placeholders.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from cores.ai.context.engine import get_orion_context, invalidate
from cores.orion import get_context, get_next_action, analyze_opportunity

logger = logging.getLogger("catseye.api.orion")

router = APIRouter(prefix="/api/orion", tags=["orion"])


# ── Decision context (summary, next action, opportunities, progress) ──

@router.get("/context")
def context() -> dict[str, Any]:
    """Return unified ORION decision context: summary, next action, opportunities, progress."""
    try:
        ctx = get_context()
        return {"data": ctx}
    except Exception as exc:
        logger.error("Failed to get orion context: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate context") from exc


# ── Full system state (counts, pipeline, earnings, opportunities, etc.) ──

@router.get("/context/system")
def system_context(refresh: bool = Query(False)) -> dict[str, Any]:
    """Return complete system state: counts, pipeline, earnings, opportunities, etc."""
    ctx = get_orion_context(force_refresh=refresh)
    ctx["_meta"]["endpoint"] = "consolidated"
    return ctx


@router.post("/context/refresh")
def refresh_context() -> dict[str, Any]:
    """Force a fresh rebuild of the context cache."""
    invalidate()
    ctx = get_orion_context(force_refresh=True)
    return {"status": "ok", "refreshed_at": ctx.get("timestamp")}


# ── Next action ──

@router.get("/next-action")
def next_action() -> dict[str, Any]:
    """Return the single best next action for the user."""
    try:
        action = get_next_action()
        return {"data": action}
    except Exception as exc:
        logger.error("Failed to get next action: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get next action") from exc


# ── Opportunity analysis ──

@router.post("/analyze-opportunity/{opportunity_id}")
def analyze_opportunity_endpoint(opportunity_id: str) -> dict[str, Any]:
    """Generate an internal analysis report for an opportunity."""
    try:
        analysis = analyze_opportunity(opportunity_id)
        if analysis is None:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        return {"data": analysis}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to analyze opportunity %s: %s", opportunity_id, exc)
        raise HTTPException(status_code=500, detail="Failed to analyze opportunity") from exc
