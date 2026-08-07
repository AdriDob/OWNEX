"""API Router para Life & Personal Assistant."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("api.life")

router = APIRouter(prefix="/api/life", tags=["life"])


# ── Tasks ────────────────────────────────────────────────────────


@router.get("/tasks")
async def get_tasks(status: str = "", category: str = "", priority: str = "") -> dict[str, Any]:
    """Get tasks with optional filters."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        tasks = assistant.get_tasks(status=status, category=category, priority=priority)
        return {"tasks": [t.__dict__ for t in tasks], "total": len(tasks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/tasks/today")
async def get_today_tasks() -> dict[str, Any]:
    """Get today's tasks."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        tasks = assistant.get_today_tasks()
        return {"tasks": [t.__dict__ for t in tasks], "total": len(tasks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/tasks")
async def add_task(task: dict[str, Any]) -> dict[str, Any]:
    """Add a new task."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        new_task = assistant.add_task(**task)
        return {"task": new_task.__dict__}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str) -> dict[str, Any]:
    """Complete a task."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        task = assistant.complete_task(task_id)
        if task:
            return {"task": task.__dict__}
        raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> dict[str, Any]:
    """Delete a task."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        deleted = assistant.delete_task(task_id)
        return {"deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Goals ────────────────────────────────────────────────────────


@router.get("/goals")
async def get_goals(status: str = "") -> dict[str, Any]:
    """Get goals with optional status filter."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        goals = assistant.get_goals(status=status)
        return {"goals": [g.__dict__ for g in goals], "total": len(goals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/goals")
async def add_goal(goal: dict[str, Any]) -> dict[str, Any]:
    """Add a new goal."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        new_goal = assistant.add_goal(**goal)
        return {"goal": new_goal.__dict__}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/goals/{goal_id}/progress")
async def update_goal_progress(goal_id: str, value: float) -> dict[str, Any]:
    """Update goal progress."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        goal = assistant.update_goal_progress(goal_id, value)
        if goal:
            return {"goal": goal.__dict__}
        raise HTTPException(status_code=404, detail="Goal not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Habits ───────────────────────────────────────────────────────


@router.get("/habits")
async def get_habits() -> dict[str, Any]:
    """Get all habits."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        habits = assistant.get_habits()
        return {"habits": [h.__dict__ for h in habits], "total": len(habits)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/habits/today")
async def get_today_habits() -> dict[str, Any]:
    """Get today's habits with completion status."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        habits = assistant.get_today_habits()
        return {"habits": habits, "total": len(habits)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/habits")
async def add_habit(habit: dict[str, Any]) -> dict[str, Any]:
    """Add a new habit."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        new_habit = assistant.add_habit(**habit)
        return {"habit": new_habit.__dict__}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/habits/{habit_id}/complete")
async def complete_habit(habit_id: str, date: str = "") -> dict[str, Any]:
    """Mark a habit as completed."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        habit = assistant.complete_habit(habit_id, date)
        if habit:
            return {"habit": habit.__dict__}
        raise HTTPException(status_code=404, detail="Habit not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Health ───────────────────────────────────────────────────────


@router.get("/health")
async def get_health(days: int = 7) -> dict[str, Any]:
    """Get health entries for the last N days."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        entries = assistant.get_health(days)
        return {"health": [e.__dict__ for e in entries], "days": days}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/health")
async def log_health(entry: dict[str, Any]) -> dict[str, Any]:
    """Log health data for today."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        new_entry = assistant.log_health(**entry)
        return {"entry": new_entry.__dict__}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Learning ─────────────────────────────────────────────────────


@router.get("/learning")
async def get_learning(topic: str = "") -> dict[str, Any]:
    """Get learning entries."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        entries = assistant.get_learning(topic=topic)
        return {"learning": [e.__dict__ for e in entries], "total": len(entries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/learning")
async def add_learning(entry: dict[str, Any]) -> dict[str, Any]:
    """Add a learning entry."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        new_entry = assistant.add_learning(**entry)
        return {"entry": new_entry.__dict__}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Notes ────────────────────────────────────────────────────────


@router.get("/notes")
async def get_notes(category: str = "") -> dict[str, Any]:
    """Get personal notes."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        notes = assistant.get_notes(category=category)
        return {"notes": [n.__dict__ for n in notes], "total": len(notes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/notes")
async def add_note(note: dict[str, Any]) -> dict[str, Any]:
    """Add a personal note."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        new_note = assistant.add_note(**note)
        return {"note": new_note.__dict__}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Daily Summary ────────────────────────────────────────────────


@router.get("/summary")
async def get_daily_summary() -> dict[str, Any]:
    """Get comprehensive daily summary."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        return assistant.get_daily_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Weekly Plan ──────────────────────────────────────────────────


@router.get("/weekly-plan")
async def get_weekly_plan() -> dict[str, Any]:
    """Get the weekly plan."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        return assistant.get_weekly_plan()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── AI Assistant ─────────────────────────────────────────────────


@router.post("/ask")
async def ask_assistant(request: dict[str, Any]) -> dict[str, Any]:
    """Ask the AI assistant a question."""
    try:
        from core.life_assistant import get_life_assistant

        assistant = get_life_assistant()
        response = await assistant.ask(
            question=request.get("question", ""),
            context=request.get("context"),
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
