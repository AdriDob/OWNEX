"""Learning Loop API — Revenue learning and metrics endpoints.

Endpoints for recording actions, results, and viewing metrics.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/learning", tags=["learning"])


class RecordActionRequest(BaseModel):
    opportunity_id: str
    action_type: str
    title: str
    description: str
    human_minutes: float
    expected_value: float


class RecordResultRequest(BaseModel):
    actual_revenue: float
    status: str  # paid, rejected, submitted
    learning_tags: list[str] = []


@router.get("/dashboard")
async def get_dashboard():
    """Get complete learning loop dashboard."""
    from cores.learning.revenue_loop import get_revenue_loop

    loop = get_revenue_loop()
    return loop.get_dashboard()


@router.post("/action")
async def record_action(request: RecordActionRequest):
    """Record a human action."""
    from cores.learning.revenue_loop import get_revenue_loop

    loop = get_revenue_loop()
    record = loop.record_action(
        opportunity_id=request.opportunity_id,
        action_type=request.action_type,
        title=request.title,
        description=request.description,
        human_minutes=request.human_minutes,
        expected_value=request.expected_value,
    )
    return {"status": "ok", "action": record.to_dict()}


@router.post("/action/{action_id}/result")
async def record_result(action_id: str, request: RecordResultRequest):
    """Record the result of an action."""
    from cores.learning.revenue_loop import get_revenue_loop

    loop = get_revenue_loop()
    success = loop.record_result(
        action_id=action_id,
        actual_revenue=request.actual_revenue,
        status=request.status,
        learning_tags=request.learning_tags,
    )
    if not success:
        return {"error": f"Action {action_id} not found"}
    return {"status": "ok"}


@router.get("/totals")
async def get_totals():
    """Get total metrics across all time."""
    from cores.learning.revenue_loop import get_revenue_loop

    loop = get_revenue_loop()
    return loop.get_totals()


@router.get("/daily")
async def get_daily(days: int = 30):
    """Get daily metrics for the last N days."""
    from cores.learning.revenue_loop import get_revenue_loop

    loop = get_revenue_loop()
    return {"days": [d.to_dict() for d in loop.get_daily_metrics(days)]}


@router.get("/metrics")
async def get_key_metrics():
    """Get the two key metrics: HUMAN_MINUTES/DAY and $PAID/HOUR."""
    from cores.learning.revenue_loop import get_revenue_loop

    loop = get_revenue_loop()
    totals = loop.get_totals()
    daily_count = max(len(loop.daily), 1)

    return {
        "human_minutes_per_day": round(totals["total_human_minutes"] / daily_count, 1),
        "human_hours_per_day": round(totals["total_human_hours"] / daily_count, 2),
        "revenue_per_human_hour": totals["avg_revenue_per_hour"],
        "ev_per_human_hour": totals["avg_ev_per_hour"],
        "total_revenue": totals["total_actual_revenue"],
        "total_actions": totals["total_actions"],
        "ev_accuracy": totals["ev_accuracy"],
    }
