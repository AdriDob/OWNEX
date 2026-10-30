"""Capital API — $1M engine endpoints.

Endpoints for capital tracking, projections, goals, and scenarios.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/capital", tags=["capital"])


class UpdateStateRequest(BaseModel):
    net_worth: float | None = None
    cash: float | None = None
    savings: float | None = None
    investments: float | None = None
    monthly_income: float | None = None
    monthly_expenses: float | None = None


class AddGoalRequest(BaseModel):
    name: str
    target_amount: float
    category: str = "general"
    priority: int = 5
    monthly_contribution: float = 0.0
    notes: str = ""


class UpdateGoalRequest(BaseModel):
    current_amount: float | None = None
    monthly_contribution: float | None = None


@router.get("/dashboard")
async def get_dashboard():
    """Get complete capital dashboard with state, goals, projections, scenarios."""
    from cores.capital.engine import get_capital_engine

    engine = get_capital_engine()
    return engine.get_dashboard()


@router.post("/state")
async def update_state(request: UpdateStateRequest):
    """Update capital state."""
    from cores.capital.engine import get_capital_engine

    engine = get_capital_engine()
    engine.update_state(
        net_worth=request.net_worth,
        cash=request.cash,
        savings=request.savings,
        investments=request.investments,
        monthly_income=request.monthly_income,
        monthly_expenses=request.monthly_expenses,
    )
    return {"status": "ok", "state": engine.state.to_dict()}


@router.get("/goals")
async def get_goals():
    """Get all financial goals."""
    from cores.capital.engine import get_capital_engine

    engine = get_capital_engine()
    return {"goals": [g.to_dict() for g in engine.goals]}


@router.post("/goals")
async def add_goal(request: AddGoalRequest):
    """Add a new financial goal."""
    from cores.capital.engine import get_capital_engine

    engine = get_capital_engine()
    goal = engine.add_goal(
        name=request.name,
        target_amount=request.target_amount,
        category=request.category,
        priority=request.priority,
        monthly_contribution=request.monthly_contribution,
        notes=request.notes,
    )
    return {"status": "ok", "goal": goal.to_dict()}


@router.put("/goals/{goal_id}")
async def update_goal(goal_id: str, request: UpdateGoalRequest):
    """Update a financial goal."""
    from cores.capital.engine import get_capital_engine

    engine = get_capital_engine()
    goal = engine.update_goal(
        goal_id=goal_id,
        current_amount=request.current_amount,
        monthly_contribution=request.monthly_contribution,
    )
    if not goal:
        return {"error": f"Goal {goal_id} not found"}
    return {"status": "ok", "goal": goal.to_dict()}


@router.get("/goals/{goal_id}/projection")
async def get_goal_projection(goal_id: str, months: int = 120):
    """Get projection for a specific goal."""
    from cores.capital.engine import get_capital_engine

    engine = get_capital_engine()
    return engine.get_goal_projections(goal_id, months=months)


@router.get("/projections")
async def get_projections():
    """Get projections for all scenarios."""
    from cores.capital.engine import get_capital_engine

    engine = get_capital_engine()
    return engine.get_all_projections()


@router.get("/million-path")
async def get_million_path():
    """Get the path to $1M with scenarios and required contributions."""
    from cores.capital.engine import get_capital_engine

    engine = get_capital_engine()
    dashboard = engine.get_dashboard()
    return {
        "target": dashboard["million_target"],
        "current": dashboard["state"]["net_worth"],
        "gap": dashboard["gap_to_million"],
        "progress_pct": dashboard["progress_to_million"],
        "scenarios": dashboard["projections"],
        "required_monthly_5yr": dashboard["required_monthly_5yr"],
    }
