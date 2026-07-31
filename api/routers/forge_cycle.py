"""Forge Cycle API Router — Work Cycle v1 for Development (OWNEX) using existing modules.

Endpoints:
- POST /api/cycles/forge/start — iniciar Work Cycle
- GET /api/cycles/forge/status — estado actual de la fase
- PUT /api/cycles/forge/stage/{stage} — avanzar a siguiente etapa
- POST /api/cycles/forge/submission/{submission_id}/learning — capturar aprendizaje
- POST /api/cycles/forge/review/{review_id}/learning — capturar aprendizaje de review
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.cycles.forge import get_forge_cycle

router = APIRouter(prefix="/api/cycles/forge", tags=["forge-cycle"])

forge_cycle = get_forge_cycle()


@router.post("/start")
def start():
    """Start the Forge Work Cycle."""
    return forge_cycle.start_cycle()


@router.get("/status")
def status():
    """Get current Forge cycle status with tasks."""
    return forge_cycle.get_cycle_status()


@router.put("/stage/{stage}")
def advance_stage(stage: str, body: dict[str, Any] | None = None):
    """Advance to the next stage."""
    cycle = forge_cycle.ensure_cycle()
    task = forge_cycle.advance_stage(int(cycle.id), stage, body or {})
    if not task:
        raise HTTPException(status_code=404, detail="Stage not found")
    return {"stage": stage, "next": task.name if task else None}


@router.post("/submission/{submission_id}/learning")
def capture_submission_learning(submission_id: int):
    """Capture knowledge from a submission outcome."""
    learning = forge_cycle.capture_learning(submission_id)
    if not learning:
        raise HTTPException(status_code=404, detail="Submission not found or no learning captured")
    return {"submission_id": submission_id, "learning": learning}


@router.post("/review/{review_id}/learning")
def capture_review_learning(review_id: int):
    """Capture learning from a code review."""
    learning = forge_cycle.capture_review_learning(review_id)
    if not learning:
        raise HTTPException(status_code=404, detail="Review not found or no learning captured")
    return {"review_id": review_id, "learning": learning}


@router.get("/dashboard")
def get_dashboard():
    """Get CEO dashboard view for the Forge Cycle."""
    return forge_cycle.get_dashboard()


@router.get("/knowledge")
def get_knowledge(limit: int = 50):
    """Get recent knowledge entries."""
    return forge_cycle.get_knowledge(limit)


@router.get("/knowledge/type/{learning_type}")
def get_knowledge_by_type(learning_type: str):
    """Get knowledge entries by learning type."""
    return forge_cycle.get_knowledge_by_type(learning_type)


@router.get("/knowledge/platform/{platform}")
def get_knowledge_by_platform(platform: str):
    """Get knowledge entries by platform."""
    return forge_cycle.get_knowledge_by_platform(platform)
