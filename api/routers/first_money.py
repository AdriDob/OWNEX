"""First Money Workflow API router.

Zero-to-Earning: tracks progress from $0 to first earning.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from cores.first_money.tracker import get_first_money_tracker

router = APIRouter(prefix="/first-money", tags=["first-money"])


@router.get("/progress")
async def get_first_money_progress() -> dict[str, Any]:
    """Get full progress dashboard for First Money workflow."""
    tracker = get_first_money_tracker()
    return tracker.get_dashboard_data()


@router.get("/next-action")
async def get_next_action() -> dict[str, Any]:
    """Get the next recommended action based on current stage."""
    tracker = get_first_money_tracker()
    action = tracker.get_next_action()
    if not action:
        return {
            "action": "complete",
            "title": "First Money Complete!",
            "description": "All stages completed. Start next cycle.",
        }
    return action


@router.post("/stage/{stage}/start")
async def start_stage(stage: str, platform: str | None = None, metadata: dict | None = None) -> dict[str, Any]:
    """Start a specific stage."""
    tracker = get_first_money_tracker()
    try:
        from cores.first_money.tracker import FirstMoneyStage

        stage_enum = FirstMoneyStage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}") from None
    success = tracker.start_stage(stage_enum, platform=platform, metadata=metadata)
    if not success:
        raise HTTPException(status_code=400, detail="Could not start stage")
    return {"success": True, "stage": stage, "platform": platform}


@router.post("/stage/{stage}/complete")
async def complete_stage(stage: str, notes: str = "", metadata: dict | None = None) -> dict[str, Any]:
    """Complete a specific stage."""
    tracker = get_first_money_tracker()
    try:
        from cores.first_money.tracker import FirstMoneyStage

        stage_enum = FirstMoneyStage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}") from None
    success = tracker.complete_stage(stage_enum, notes=notes, metadata=metadata)
    if not success:
        raise HTTPException(status_code=400, detail="Could not complete stage")
    return {"success": True, "stage": stage}


@router.post("/stage/{stage}/block")
async def block_stage(stage: str, reason: str) -> dict[str, Any]:
    """Block a stage with a reason."""
    tracker = get_first_money_tracker()
    try:
        from cores.first_money.tracker import FirstMoneyStage

        stage_enum = FirstMoneyStage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}") from None
    success = tracker.block_stage(stage_enum, reason)
    if not success:
        raise HTTPException(status_code=400, detail="Could not block stage")
    return {"success": True, "stage": stage, "reason": reason}


@router.post("/first-revenue")
async def record_first_revenue(amount: float, platform: str, notes: str = "") -> dict[str, Any]:
    """Record the first real revenue earned."""
    tracker = get_first_money_tracker()
    success = tracker.record_first_revenue(amount, platform, notes)
    if not success:
        raise HTTPException(status_code=400, detail="Could not record revenue")
    return {"success": True, "amount": amount, "platform": platform}


@router.post("/analysis")
async def record_analysis(estimated_vs_actual: dict[str, Any], notes: str = "") -> dict[str, Any]:
    """Record post-earning analysis (estimated vs actual)."""
    tracker = get_first_money_tracker()
    success = tracker.record_analysis(estimated_vs_actual, notes)
    if not success:
        raise HTTPException(status_code=400, detail="Could not record analysis")
    return {"success": True}


@router.post("/next-recommendation")
async def record_next_recommendation(recommendation: dict[str, Any]) -> dict[str, Any]:
    """Record next opportunity recommendation and reset for next cycle."""
    tracker = get_first_money_tracker()
    success = tracker.recommend_next(recommendation)
    if not success:
        raise HTTPException(status_code=400, detail="Could not record recommendation")
    return {"success": True, "recommendation": recommendation}


@router.get("/stages")
async def list_stages() -> dict[str, Any]:
    """List all First Money stages with labels and descriptions."""
    from cores.first_money.tracker import FirstMoneyTracker

    tracker = FirstMoneyTracker()  # temporary for constants
    return {
        "stages": [
            {
                "stage": stage.value,
                "label": tracker.STAGE_LABELS[stage],
                "description": tracker.STAGE_DESCRIPTIONS[stage],
            }
            for stage in tracker.STAGE_ORDER
        ]
    }


@router.post("/reset")
async def reset_first_money() -> dict[str, Any]:
    """Reset First Money progress (start fresh)."""
    from cores.first_money.tracker import reset_first_money_tracker

    reset_first_money_tracker()
    get_first_money_tracker()  # Creates fresh
    return {"success": True, "message": "First Money progress reset"}
