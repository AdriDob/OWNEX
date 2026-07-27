"""Security Cycle API Router — Work Cycle v1 for Security (Rastro) using existing CATEYE modules.

Endpoints:
- POST /api/cycles/security/start — iniciar Work Cycle
- GET /api/cycles/security/status — estado actual de la fase
- PUT /api/cycles/security/stage/{stage} — avanzar a siguiente etapa
- POST /api/cycles/security/finding/{finding_id}/learning — capturar aprendizaje
- POST /api/cycles/security/payout/{payout_id}/learning — capturar aprendizaje de payout
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.cycles.security import get_security_cycle

router = APIRouter(prefix="/api/cycles/security", tags=["security-cycle"])

security_cycle = get_security_cycle()


@router.post("/start")
def start():
    """Start the Security Work Cycle."""
    return security_cycle.start_cycle()


@router.get("/status")
def status():
    """Get current Security cycle status with tasks."""
    return security_cycle.get_cycle_status()


@router.put("/stage/{stage}")
def advance_stage(stage: str, body: dict[str, Any] | None = None):
    """Advance to the next stage."""
    cycle = security_cycle.ensure_cycle()
    task = security_cycle.advance_stage(cycle.id, stage, body or {})
    if not task:
        raise HTTPException(status_code=404, detail="Stage not found")
    return {"stage": stage, "next": task.name if task else None}


@router.post("/finding/{finding_id}/learning")
def capture_finding_learning(finding_id: int):
    """Capture knowledge from a finding outcome."""
    learning = security_cycle.capture_learning(finding_id)
    if not learning:
        raise HTTPException(status_code=404, detail="Finding not found or no learning captured")
    return {"finding_id": finding_id, "learning": learning}


@router.post("/payout/{payout_id}/learning")
def capture_payout_learning(payout_id: int):
    """Capture learning from a confirmed payout."""
    learning = security_cycle.capture_payout_learning(payout_id)
    if not learning:
        raise HTTPException(status_code=404, detail="Payout not found or no learning captured")
    return {"payout_id": payout_id, "learning": learning}


@router.get("/dashboard")
def get_dashboard():
    """Get CEO dashboard view for the Security Cycle."""
    return security_cycle.get_dashboard()


@router.get("/knowledge")
def get_knowledge(limit: int = 50):
    """Get recent knowledge entries."""
    return security_cycle.get_knowledge(limit)


@router.get("/knowledge/type/{learning_type}")
def get_knowledge_by_type(learning_type: str):
    """Get knowledge entries by learning type."""
    return security_cycle.get_knowledge_by_type(learning_type)


@router.get("/knowledge/vuln/{vuln_type}")
def get_knowledge_by_vuln_type(vuln_type: str):
    """Get knowledge entries by vulnerability type."""
    return security_cycle.get_knowledge_by_vuln(vuln_type)


@router.get("/knowledge/platform/{platform}")
def get_knowledge_by_platform(platform: str):
    """Get knowledge entries by platform."""
    return security_cycle.get_knowledge_by_platform(platform)
