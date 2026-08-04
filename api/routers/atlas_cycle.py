"""Atlas Cycle API Router — Work Cycle for Intelligence (Atlas) using existing modules.

Endpoints:
- POST /api/cycles/atlas/start — iniciar Work Cycle
- GET /api/cycles/atlas/status — estado actual de la fase
- PUT /api/cycles/atlas/stage/{stage} — avanzar a siguiente etapa
- POST /api/cycles/atlas/task/{task_id}/learning — capturar aprendizaje
- GET /api/cycles/atlas/dashboard — CEO dashboard view
- GET /api/cycles/atlas/knowledge — entradas de conocimiento recientes
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.cycles.atlas import get_atlas_cycle

router = APIRouter(prefix="/api/cycles/atlas", tags=["atlas-cycle"])

atlas_cycle = get_atlas_cycle()


@router.post("/start")
def start():
    """Start the Atlas Work Cycle."""
    return atlas_cycle.start_cycle()


@router.get("/status")
def status():
    """Get current Atlas cycle status with tasks."""
    return atlas_cycle.get_cycle_status()


@router.put("/stage/{stage}")
def advance_stage(stage: str, body: dict[str, Any] | None = None):
    """Advance to the next stage."""
    cycle = atlas_cycle.ensure_cycle()
    task = atlas_cycle.advance_stage(int(cycle.id), stage, body or {})
    if not task:
        raise HTTPException(status_code=404, detail="Stage not found")
    return {"stage": stage, "next": task.name if task else None}


@router.post("/task/{task_id}/learning")
def capture_task_learning(task_id: int):
    """Capture knowledge from a task outcome."""
    learning = atlas_cycle.capture_learning(task_id)
    if not learning:
        raise HTTPException(status_code=404, detail="Task not found or no learning captured")
    return {"task_id": task_id, "learning": learning}


@router.get("/dashboard")
def get_dashboard():
    """Get CEO dashboard view for the Atlas Cycle."""
    return atlas_cycle.get_dashboard()


@router.get("/knowledge")
def get_knowledge(limit: int = 50):
    """Get recent knowledge entries."""
    return atlas_cycle.get_knowledge(limit)


@router.get("/knowledge/type/{learning_type}")
def get_knowledge_by_type(learning_type: str):
    """Get knowledge entries by learning type."""
    return atlas_cycle.get_knowledge_by_type(learning_type)


@router.get("/knowledge/platform/{platform}")
def get_knowledge_by_platform(platform: str):
    """Get knowledge entries by platform."""
    return atlas_cycle.get_knowledge_by_platform(platform)
