"""Pulse Cycle API Router — Work Cycle for AI Work (Pulse) using existing modules.

Endpoints:
- POST /api/cycles/pulse/start — iniciar Work Cycle
- GET /api/cycles/pulse/status — estado actual de la fase
- PUT /api/cycles/pulse/stage/{stage} — avanzar a siguiente etapa
- POST /api/cycles/pulse/task/{task_id}/learning — capturar aprendizaje
- GET /api/cycles/pulse/dashboard — CEO dashboard view
- GET /api/cycles/pulse/knowledge — entradas de conocimiento recientes
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.cycles.pulse import get_pulse_cycle

router = APIRouter(prefix="/api/cycles/pulse", tags=["pulse-cycle"])

pulse_cycle = get_pulse_cycle()


@router.post("/start")
def start():
    """Start the Pulse Work Cycle."""
    return pulse_cycle.start_cycle()


@router.get("/status")
def status():
    """Get current Pulse cycle status with tasks."""
    return pulse_cycle.get_cycle_status()


@router.put("/stage/{stage}")
def advance_stage(stage: str, body: dict[str, Any] | None = None):
    """Advance to the next stage."""
    cycle = pulse_cycle.ensure_cycle()
    task = pulse_cycle.advance_stage(int(cycle.id), stage, body or {})
    if not task:
        raise HTTPException(status_code=404, detail="Stage not found")
    return {"stage": stage, "next": task.name if task else None}


@router.post("/task/{task_id}/learning")
def capture_task_learning(task_id: int):
    """Capture knowledge from a task outcome."""
    learning = pulse_cycle.capture_learning(task_id)
    if not learning:
        raise HTTPException(status_code=404, detail="Task not found or no learning captured")
    return {"task_id": task_id, "learning": learning}


@router.get("/dashboard")
def get_dashboard():
    """Get CEO dashboard view for the Pulse Cycle."""
    return pulse_cycle.get_dashboard()


@router.get("/knowledge")
def get_knowledge(limit: int = 50):
    """Get recent knowledge entries."""
    return pulse_cycle.get_knowledge(limit)


@router.get("/knowledge/type/{learning_type}")
def get_knowledge_by_type(learning_type: str):
    """Get knowledge entries by learning type."""
    return pulse_cycle.get_knowledge_by_type(learning_type)


@router.get("/knowledge/platform/{platform}")
def get_knowledge_by_platform(platform: str):
    """Get knowledge entries by platform."""
    return pulse_cycle.get_knowledge_by_platform(platform)
