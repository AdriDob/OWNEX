"""API Router for Daily Planning and Productivity."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from cores.productivity.daily_planning import (
    TaskStatus,
    get_daily_planning_system,
)

router = APIRouter(prefix="/productivity", tags=["productivity"])


@router.get("/daily-plan")
async def get_daily_plan(date: str | None = None):
    """Get daily plan for a specific date."""
    system = get_daily_planning_system()

    plan_date = datetime.strptime(date, "%Y-%m-%d") if date else None

    plan = system.get_daily_plan(plan_date)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "date": plan.date,
        "tasks": [task.__dict__ for task in plan.tasks],
        "total_estimated_minutes": plan.total_estimated_minutes,
        "total_completed_minutes": plan.total_completed_minutes,
        "progress_percentage": plan.progress_percentage,
        "breaks_scheduled": plan.breaks_scheduled,
        "breaks_taken": plan.breaks_taken,
        "focus_sessions": plan.focus_sessions,
    }


@router.post("/daily-plan/generate")
async def generate_daily_plan(date: str | None = None):
    """Generate daily plan for a specific date."""
    system = get_daily_planning_system()

    plan_date = datetime.strptime(date, "%Y-%m-%d") if date else None

    plan = system.generate_daily_plan(plan_date)

    return {
        "date": plan.date,
        "tasks": [task.__dict__ for task in plan.tasks],
        "total_estimated_minutes": plan.total_estimated_minutes,
        "progress_percentage": plan.progress_percentage,
        "breaks_scheduled": plan.breaks_scheduled,
    }


@router.put("/task/{task_id}/status")
async def update_task_status(task_id: str, payload: dict[str, Any]):
    """Update task status."""
    system = get_daily_planning_system()

    date = payload.get("date")
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    status = TaskStatus(payload.get("status", "pending"))

    success = system.update_task_status(date, task_id, status)

    if not success:
        raise HTTPException(status_code=404, detail="Task or plan not found")

    return {
        "success": True,
        "task_id": task_id,
        "status": status.value,
    }


@router.post("/break")
async def add_break(payload: dict[str, Any]):
    """Add break to daily plan."""
    system = get_daily_planning_system()

    date = payload.get("date")
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    success = system.add_break(date)

    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "success": True,
        "date": date,
    }


@router.get("/metrics")
async def get_productivity_metrics(date: str | None = None):
    """Get productivity metrics for a specific date."""
    system = get_daily_planning_system()

    metric_date = datetime.strptime(date, "%Y-%m-%d") if date else None

    metrics = system.get_productivity_metrics(metric_date)

    return metrics.__dict__


@router.get("/weekly-summary")
async def get_weekly_summary():
    """Get weekly productivity summary."""
    system = get_daily_planning_system()
    summary = system.get_weekly_summary()
    return summary


@router.post("/sync-obsidian")
async def sync_with_obsidian(payload: dict[str, Any]):
    """Sync daily plan with Obsidian."""
    system = get_daily_planning_system()

    date = payload.get("date")
    sync_date = datetime.strptime(date, "%Y-%m-%d") if date else None

    success = system.sync_with_obsidian(sync_date)

    if not success:
        raise HTTPException(status_code=400, detail="Obsidian sync failed or not enabled")

    return {
        "success": True,
        "message": "Plan synced with Obsidian",
    }
