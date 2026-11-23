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
    build_workspace,
    complete_guide_step,
    dismiss_action,
    get_guide_progress,
    next_best_action,
    snooze_action,
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


@router.get("/workbank/{item_id}/workspace")
def guided_workspace(item_id: str) -> dict:
    """Fase 2 — Guided Earning Workspace: journey + guide + verification + resume."""
    item = get_workbank().get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work-bank item not found")
    try:
        start_guide(item_id)
    except Exception as exc:
        logger.warning("guided_earning start failed for %s: %s", item_id, exc)
    return build_workspace(item, get_guide_progress(item_id))


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


@router.post("/workbank/{item_id}/snooze")
def guided_snooze(item_id: str, body: dict | None = None) -> dict:
    """Posponer: hide from NBA for N hours (default 24)."""
    hours = int((body or {}).get("hours") or 24)
    return {"item_id": item_id, "progress": snooze_action(item_id, hours=hours)}


@router.post("/workbank/{item_id}/dismiss")
def guided_dismiss(item_id: str, body: dict | None = None) -> dict:
    """Descartar: exclude from NBA (history preserved; reversible via progress reset)."""
    return {"item_id": item_id, "progress": dismiss_action(item_id, reason=str((body or {}).get("reason") or ""))}
