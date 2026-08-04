"""QA Cycle API Router — Work Cycle for automated QA testing using existing modules.

Endpoints:
- POST /api/cycles/qa/start — iniciar Work Cycle
- GET /api/cycles/qa/status — estado actual de la fase
- PUT /api/cycles/qa/stage/{stage} — avanzar a siguiente etapa
- POST /api/cycles/qa/cases — generar test suite desde targets/endpoints/findings
- POST /api/cycles/qa/run — ejecutar ciclo QA completo end-to-end
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.cycles.qa import get_qa_cycle

router = APIRouter(prefix="/api/cycles/qa", tags=["qa-cycle"])

qa_cycle = get_qa_cycle()


@router.post("/start")
def start():
    """Start the QA Testing Work Cycle."""
    cycle = qa_cycle.start_cycle()
    return {"id": cycle.id, "name": cycle.name, "status": cycle.status}


@router.get("/status")
def status():
    """Get current QA cycle status with tasks."""
    return qa_cycle.get_cycle_status()


@router.put("/stage/{stage}")
def advance_stage(stage: str, body: dict[str, Any] | None = None):
    """Advance to the next stage."""
    cycle = qa_cycle.ensure_cycle()
    task = qa_cycle.advance_stage(int(cycle.id), stage, body or {})
    if not task:
        raise HTTPException(status_code=404, detail="Stage not found")
    return {"stage": stage, "next": task.name if task else None}


@router.post("/cases")
def generate_cases(body: dict[str, Any] | None = None):
    """Generate a QA test suite from targets, endpoints and findings."""
    payload = body or {}
    try:
        suite = qa_cycle.generate_test_cases(
            target_ids=payload.get("target_ids"),
            endpoint_ids=payload.get("endpoint_ids"),
            finding_ids=payload.get("finding_ids"),
            include_regression=payload.get("include_regression", True),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Case generation failed: {exc}") from exc
    return suite.to_dict()


@router.post("/run")
def run_full_cycle(body: dict[str, Any] | None = None):
    """Run a complete QA cycle end-to-end: plan → execute → evidence → report → follow-up."""
    payload = body or {}
    try:
        result = qa_cycle.run_full_qa_cycle(
            target_ids=payload.get("target_ids"),
            endpoint_ids=payload.get("endpoint_ids"),
            finding_ids=payload.get("finding_ids"),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Full QA cycle failed: {exc}") from exc
    return result
