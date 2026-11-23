"""Guided Earning API — execution guides + next best action.

Orientation layer over the Work Bank: tells the owner exactly what to do,
where to go, and what OWNEX can do automatically — without inventing URLs,
credentials, or payment methods.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from core.opportunity.guided_earning import (
    build_execution_guide,
    complete_guide_step,
    get_guide_progress,
    next_best_action,
    start_guide,
)
from cores.direct_work_engine.workbank import get_workbank

logger = logging.getLogger("ownex.api.guided_earning")

router = APIRouter(prefix="/api/guided-earning", tags=["guided-earning"])


@router.get("/next")
def guided_next() -> dict:
    """The single most useful next action toward first verified revenue."""
    return next_best_action()


@router.get("/workbank/{item_id}/guide")
def guided_guide(item_id: str) -> dict:
    """Full Opportunity Execution Guide for one Work Bank item."""
    item = get_workbank().get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work-bank item not found")
    try:
        start_guide(item_id)
    except Exception as exc:  # progress store is best-effort; guide still serves
        logger.warning("guided_earning start failed for %s: %s", item_id, exc)
    return build_execution_guide(item, get_guide_progress(item_id))


@router.get("/workbank/{item_id}/progress")
def guided_progress(item_id: str) -> dict:
    item = get_workbank().get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work-bank item not found")
    return {"item_id": item_id, "progress": get_guide_progress(item_id)}


@router.post("/workbank/{item_id}/steps/{step_id}/complete")
def guided_complete_step(item_id: str, step_id: str) -> dict:
    """Record owner-confirmed step completion (idempotent)."""
    try:
        return {"item_id": item_id, "progress": complete_guide_step(item_id, step_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Work-bank item not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
