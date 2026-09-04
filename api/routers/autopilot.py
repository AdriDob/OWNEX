from __future__ import annotations

"""Autopilot API Router - REST endpoints for autopilot control."""


from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.autopilot import get_autopilot
from cores.autopilot.daily_autopilot import get_daily_autopilot
from cores.autopilot.gates.human_gate import GateDecision

router = APIRouter(prefix="/api/autopilot", tags=["autopilot"])


class ModeSwitchRequest(BaseModel):
    mode: str  # "max_income", "best_income", "fast_income"


class GateDecisionRequest(BaseModel):
    decision: str  # "approved", "rejected", "deferred", "needs_more_info"
    notes: str = ""


@router.get("/status")
async def get_autopilot_status():
    """Get current autopilot status."""
    autopilot = get_autopilot()
    return {
        "is_running": autopilot.status.is_running,
        "started_at": autopilot.status.started_at.isoformat() if autopilot.status.started_at else None,
        "current_mode": autopilot.status.current_mode.value
        if hasattr(autopilot.status.current_mode, "value")
        else str(autopilot.status.current_mode),
        "last_cycle": autopilot.status.last_cycle.isoformat() if autopilot.status.last_cycle else None,
        "cycles_completed": autopilot.status.cycles_completed,
        "gates_pending": autopilot.status.gates_pending,
        "checks_passed": autopilot.status.checks_passed,
        "checks_failed": autopilot.status.checks_failed,
        "achievements_unlocked": autopilot.status.achievements_unlocked,
        "capital_velocity_usd_day": autopilot.status.capital_velocity_usd_day,
        "next_actions": autopilot.status.next_actions,
        "errors": autopilot.status.errors[-10:] if autopilot.status.errors else [],
    }


@router.post("/start")
async def start_autopilot():
    """Start the autopilot engine."""
    autopilot = get_autopilot()
    if autopilot.status.is_running:
        raise HTTPException(status_code=400, detail="Autopilot already running")

    await autopilot.start()
    return {"status": "started", "message": "Autopilot started successfully"}


@router.post("/stop")
async def stop_autopilot():
    """Stop the autopilot engine."""
    autopilot = get_autopilot()
    if not autopilot.status.is_running:
        raise HTTPException(status_code=400, detail="Autopilot not running")

    await autopilot.stop()
    return {"status": "stopped", "message": "Autopilot stopped successfully"}


@router.post("/mode")
async def set_income_mode(request: ModeSwitchRequest):
    """Switch income mode (max_income, best_income, fast_income)."""
    autopilot = get_autopilot()

    try:
        from cores.autopilot.config.autopilot_config import IncomeMode

        mode = IncomeMode(request.mode.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {request.mode}. Must be one of: max_income, best_income, fast_income",
        )

    await autopilot.set_income_mode(mode)
    return {"status": "success", "mode": mode.value}


@router.get("/modes")
async def get_income_modes():
    """Get all available income modes with their configurations."""
    autopilot = get_autopilot()
    return {
        "current_mode": autopilot.status.current_mode.value
        if hasattr(autopilot.status.current_mode, "value")
        else str(autopilot.status.current_mode),
        "modes": autopilot.income_mode_manager.get_all_presets() if hasattr(autopilot, "income_mode_manager") else {},
    }


@router.get("/dashboard")
async def get_dashboard():
    """Get complete dashboard data for Mission Control."""
    autopilot = get_autopilot()
    return autopilot.get_dashboard_data()


@router.get("/gates")
async def get_pending_gates():
    """Get all pending human gates."""
    autopilot = get_autopilot()
    gates = autopilot.human_gate.get_pending_gates()

    return {
        "gates": [
            {
                "gate_id": g.gate_id,
                "gate_type": g.gate_type.value if hasattr(g.gate_type, "value") else str(g.gate_type),
                "title": g.title,
                "description": g.description,
                "display_title": g.display_title,
                "amount_usd": g.amount_usd,
                "platform": g.platform,
                "auto_approvable": g.auto_approvable,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "waiting_since": g.waiting_since.isoformat() if g.waiting_since else None,
                "waiting_minutes": int(
                    (__import__("datetime").datetime.utcnow() - g.waiting_since).total_seconds() / 60
                )
                if g.waiting_since
                else 0,
            }
            for g in gates
        ],
        "stats": autopilot.human_gate.get_stats() if hasattr(autopilot.human_gate, "get_stats") else {},
    }


@router.post("/gates/{gate_id}/decision")
async def resolve_gate(gate_id: str, request: GateDecisionRequest):
    """Approve or reject a pending gate."""
    autopilot = get_autopilot()

    try:
        decision = GateDecision(request.decision.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision: {request.decision}. Must be one of: approved, rejected, deferred, needs_more_info",
        )

    success = await autopilot.approve_gate(gate_id, decision, request.notes)
    if not success:
        raise HTTPException(status_code=404, detail=f"Gate {gate_id} not found")

    return {"status": "success", "gate_id": gate_id, "decision": decision.value}


@router.post("/workbank/cycle")
async def trigger_workbank_cycle():
    """Manually trigger a WorkBank cycle."""
    autopilot = get_autopilot()
    result = await autopilot.trigger_workbank_cycle()
    return {"status": "success", "result": result}


@router.post("/capital/rebalance")
async def trigger_capital_rebalance():
    """Manually trigger capital rebalancing."""
    autopilot = get_autopilot()
    result = await autopilot.trigger_capital_rebalance()
    return {"status": "success", "result": result}


@router.get("/goals")
async def get_goals():
    """Get goal hierarchy."""
    autopilot = get_autopilot()
    if hasattr(autopilot, "goal_hierarchy") and autopilot.goal_hierarchy:
        return autopilot.goal_hierarchy.get_hierarchy_tree()
    return {"goals": [], "sprints": []}


@router.get("/achievements")
async def get_achievements():
    """Get all achievements."""
    autopilot = get_autopilot()
    if hasattr(autopilot, "achievement_engine") and autopilot.achievement_engine:
        return {
            "achievements": autopilot.achievement_engine.get_all_achievements(),
            "streaks": autopilot.achievement_engine.get_streaks_status()
            if hasattr(autopilot.achievement_engine, "get_streaks_status")
            else {},
        }
    return {"achievements": [], "streaks": {}}


@router.get("/capital/velocity")
async def get_capital_velocity():
    """Get capital velocity metrics."""
    autopilot = get_autopilot()
    if hasattr(autopilot, "capital_velocity") and autopilot.capital_velocity:
        return autopilot.capital_velocity.get_velocity()
    return {}


@router.get("/quant/status")
async def get_quant_status():
    """Get quant engine status."""
    autopilot = get_autopilot()
    if hasattr(autopilot, "quant_engine") and autopilot.quant_engine:
        return autopilot.quant_engine.get_status()
    return {"enabled": False, "mode": "off"}


@router.get("/config")
async def get_config():
    """Get current autopilot configuration."""
    autopilot = get_autopilot()
    return autopilot.config.to_dict() if hasattr(autopilot.config, "to_dict") else {"error": "Config not serializable"}


# === ONE ACTION ENDPOINT ===


@router.get("/one-action")
async def get_one_action(force_refresh: bool = False):
    """Get the ONE best action from the Daily Autopilot.

    This is the canonical endpoint for the Command Center.
    Returns exactly ONE action (or NO ACTION REQUIRED).
    """
    autopilot = get_daily_autopilot()

    if force_refresh:
        result = autopilot.run_daily_cycle(force=True)
    else:
        # Get current action or run cycle if none
        current = autopilot.get_current_action()
        if current:
            result = {"status": "cached", "action": current}
        else:
            result = autopilot.run_daily_cycle()

    return result


@router.post("/one-action/refresh")
async def refresh_one_action():
    """Force a fresh daily cycle and get the new ONE action."""
    autopilot = get_daily_autopilot()
    result = autopilot.run_daily_cycle(force=True)
    return result


@router.get("/daily-autopilot/status")
async def get_daily_autopilot_status():
    """Get the Daily Autopilot status."""
    autopilot = get_daily_autopilot()
    return autopilot.get_status()


@router.post("/daily-autopilot/cycle")
async def run_daily_cycle(force: bool = False):
    """Manually trigger the daily autopilot cycle."""
    autopilot = get_daily_autopilot()
    result = autopilot.run_daily_cycle(force=force)
    return result
