"""WorkerCore API — Control the autonomous work orchestrator.

Endpoints for starting, stopping, monitoring, and approving work items
in the 8-phase loop: DISCOVER→EVALUATE→SELECT→PREPARE→EXECUTE→
VALIDATE→DELIVER→LEARN.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("ownex.api.worker_core")

router = APIRouter(prefix="/api/worker", tags=["worker-core"])


def _get_worker():  # type: ignore[no-untyped-def]
    """Get WorkerCore singleton, raising 503 if not initialized."""
    from cores.worker_core import get_worker_core

    return get_worker_core()


# ── Status ────────────────────────────────────────────────────────────


@router.get("/status")
async def worker_status() -> dict[str, Any]:
    """Get current worker status including metrics and active work items."""
    worker = _get_worker()
    return worker.get_status()


# ── Lifecycle ─────────────────────────────────────────────────────────


@router.post("/start")
async def worker_start() -> dict[str, Any]:
    """Start the autonomous work loop."""
    worker = _get_worker()
    if worker._running:
        return {"status": "already_running", "state": worker.state.value}

    # Ensure engines are connected
    if not worker._discovery_engine:
        worker.connect_real_engines()

    await worker.start()
    logger.info("WorkerCore started via API")
    return {"status": "started", "state": worker.state.value}


@router.post("/stop")
async def worker_stop() -> dict[str, Any]:
    """Stop the autonomous work loop gracefully."""
    worker = _get_worker()
    if not worker._running:
        return {"status": "already_stopped", "state": worker.state.value}

    await worker.stop()
    logger.info("WorkerCore stopped via API")
    return {"status": "stopped", "state": worker.state.value}


@router.post("/pause")
async def worker_pause() -> dict[str, Any]:
    """Pause the worker (stops new cycles, keeps current work)."""
    worker = _get_worker()
    await worker.pause()
    return {"status": "paused", "state": worker.state.value}


@router.post("/resume")
async def worker_resume() -> dict[str, Any]:
    """Resume a paused worker."""
    worker = _get_worker()
    await worker.resume()
    return {"status": "resumed", "state": worker.state.value}


# ── Goal ──────────────────────────────────────────────────────────────


class GoalRequest(BaseModel):
    description: str = Field("", description="Human-readable goal description")
    target_monthly_usd: float = Field(5000.0, description="Target monthly revenue in USD")
    min_reward_usd: float = Field(10.0, description="Minimum reward to consider")
    max_risk_score: float = Field(0.8, description="Maximum risk score (0-1)")
    preferred_categories: list[str] = Field(default_factory=list, description="Preferred work categories")


@router.post("/goal")
async def set_goal(body: GoalRequest) -> dict[str, Any]:
    """Set the worker's goal (target revenue, risk tolerance, categories)."""
    from cores.worker_core.models import WorkGoal

    worker = _get_worker()
    goal = WorkGoal(
        description=body.description,
        target_monthly_usd=body.target_monthly_usd,
        min_reward_usd=body.min_reward_usd,
        max_risk_score=body.max_risk_score,
        preferred_categories=body.preferred_categories,
    )
    worker.set_goal(goal)
    return {"status": "goal_set", "goal": worker.get_status()["goal"]}


# ── Work Item Management ──────────────────────────────────────────────


@router.get("/work-items")
async def list_work_items() -> dict[str, Any]:
    """List all work items with their current state."""
    worker = _get_worker()
    items = []
    for w in worker.work_items.values():
        items.append(
            {
                "id": w.id,
                "title": w.title,
                "phase": w.phase.value,
                "state": w.state.value,
                "platform": w.platform,
                "category": w.category,
                "estimated_reward_usd": w.estimated_reward_usd,
                "expected_value_usd_per_hour": w.expected_value_usd_per_hour,
                "acceptance_probability": w.acceptance_probability,
                "human_action_required": w.human_action_required,
                "human_action_description": w.human_action_description,
                "error": w.error,
                "artifacts": w.artifacts,
                "checkpoints": len(w.checkpoints),
            }
        )
    return {"items": items, "total": len(items)}


@router.get("/work-items/{work_id}")
async def get_work_item(work_id: str) -> dict[str, Any]:
    """Get details of a specific work item."""
    worker = _get_worker()
    w = worker.work_items.get(work_id)
    if not w:
        raise HTTPException(status_code=404, detail=f"Work item {work_id} not found")
    return {
        "id": w.id,
        "title": w.title,
        "description": w.description,
        "phase": w.phase.value,
        "state": w.state.value,
        "platform": w.platform,
        "category": w.category,
        "estimated_reward_usd": w.estimated_reward_usd,
        "estimated_hours": w.estimated_hours,
        "expected_value_usd_per_hour": w.expected_value_usd_per_hour,
        "acceptance_probability": w.acceptance_probability,
        "risk_score": w.risk_score,
        "human_action_required": w.human_action_required,
        "human_action_description": w.human_action_description,
        "approved_by_human": w.approved_by_human,
        "error": w.error,
        "artifacts": w.artifacts,
        "evidence": w.evidence,
        "checkpoints": w.checkpoints,
    }


# ── Approval ──────────────────────────────────────────────────────────


@router.post("/work-items/{work_id}/approve")
async def approve_work(work_id: str) -> dict[str, Any]:
    """Approve a work item that requires human action."""
    worker = _get_worker()
    success = worker.approve_work(work_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Work item {work_id} not found")
    return {"status": "approved", "work_id": work_id}


@router.post("/work-items/{work_id}/reject")
async def reject_work(work_id: str, reason: str = "Rejected by user") -> dict[str, Any]:
    """Reject a work item."""
    worker = _get_worker()
    success = worker.reject_work(work_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail=f"Work item {work_id} not found")
    return {"status": "rejected", "work_id": work_id, "reason": reason}


# ── Metrics ───────────────────────────────────────────────────────────


@router.get("/metrics")
async def worker_metrics() -> dict[str, Any]:
    """Get worker performance metrics."""
    worker = _get_worker()
    return {
        "cycles_completed": worker.metrics.cycles_completed,
        "work_completed": worker.metrics.work_items_completed,
        "work_failed": worker.metrics.work_items_failed,
        "total_revenue_usd": worker.metrics.total_revenue_usd,
        "avg_ev_usd_per_hour": worker.metrics.avg_expected_value_usd_per_hour,
        "session_cost_usd": worker._session_cost_usd,
        "workflow_costs": worker._workflow_costs,
        "circuit_breakers": {
            name: cb.snapshot() if hasattr(cb, "snapshot") else {} for name, cb in worker._circuit_breakers.items()
        },
    }


# ── Audit Trail ───────────────────────────────────────────────────────


@router.get("/audit")
async def worker_audit(workflow_id: str | None = None, limit: int = 50) -> dict[str, Any]:
    """Get audit trail entries."""
    try:
        from cores.worker_core.audit import get_recent_audit, get_workflow_audit

        entries = get_workflow_audit(workflow_id, limit=limit) if workflow_id else get_recent_audit(limit=limit)
        return {"entries": entries, "count": len(entries)}
    except Exception as exc:
        return {"entries": [], "count": 0, "error": str(exc)}


# ── Checkpoints ───────────────────────────────────────────────────────


@router.get("/checkpoints")
async def worker_checkpoints() -> dict[str, Any]:
    """Get persisted checkpoints for crash recovery."""
    try:
        from cores.worker_core.persistence import get_active_work_items, get_latest_checkpoint

        active = get_active_work_items()
        checkpoints = []
        for work_id in active:
            cp = get_latest_checkpoint(work_id)
            if cp:
                checkpoints.append(
                    {
                        "work_item_id": work_id,
                        "phase": getattr(cp, "phase", "unknown"),
                        "completed": getattr(cp, "phase_completed", False),
                        "error": getattr(cp, "error", None),
                        "retry_count": getattr(cp, "retry_count", 0),
                    }
                )
        return {"checkpoints": checkpoints, "count": len(checkpoints)}
    except Exception as exc:
        return {"checkpoints": [], "count": 0, "error": str(exc)}
