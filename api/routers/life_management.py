"""
API Router for Life Management System
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from cores.life_management import (
    AdviceCategory,
    DailyMood,
    DailyRoutine,
    Goal,
    GoalCategory,
    GoalStatus,
    Habit,
    HabitEntry,
    HabitFrequency,
    HabitStatus,
    LifeManagementSystem,
    MoodLevel,
    PCUsageSession,
    Task,
    TaskCategory,
    TaskPriority,
    TaskStatus,
    get_life_management_system,
)

router = APIRouter(prefix="/life-management", tags=["life-management"])


# ============ TASK MANAGEMENT ============


@router.post("/tasks")
async def create_task(payload: dict[str, Any]):
    """Create a new task."""
    system = get_life_management_system()

    try:
        task = system.create_task(
            title=payload.get("title"),
            description=payload.get("description", ""),
            category=TaskCategory(payload.get("category")),
            priority=TaskPriority(payload.get("priority")),
            due_date=datetime.fromisoformat(payload["due_date"]) if payload.get("due_date") else None,
            estimated_minutes=payload.get("estimated_minutes", 30),
            tags=payload.get("tags", []),
            recurring=payload.get("recurring", False),
            recurring_frequency=payload.get("recurring_frequency"),
            linked_goal_id=payload.get("linked_goal_id"),
            linked_habit_id=payload.get("linked_habit_id"),
        )

        return {
            "success": True,
            "task": task.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def get_tasks(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    date: str | None = None,
):
    """Get tasks with optional filters."""
    system = get_life_management_system()

    tasks = list(system.tasks.values())

    if category:
        tasks = [t for t in tasks if t.category.value == category]
    if priority:
        tasks = [t for t in tasks if t.priority.value == priority]
    if status:
        tasks = [t for t in tasks if t.status.value == status]
    if date:
        filter_date = datetime.strptime(date, "%Y-%m-%d")
        tasks = [t for t in tasks if t.due_date and t.due_date.strftime("%Y-%m-%d") == date]

    return {
        "success": True,
        "tasks": [task.__dict__ for task in tasks],
        "total": len(tasks),
    }


@router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: str, payload: dict[str, Any]):
    """Update task status."""
    system = get_life_management_system()

    try:
        success = system.update_task_status(task_id, TaskStatus(payload["status"]))

        if not success:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "success": True,
            "message": "Task status updated",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ GOAL MANAGEMENT ============


@router.post("/goals")
async def create_goal(payload: dict[str, Any]):
    """Create a new goal."""
    system = get_life_management_system()

    try:
        goal = system.create_goal(
            title=payload.get("title"),
            description=payload.get("description", ""),
            category=GoalCategory(payload.get("category")),
            target_date=datetime.fromisoformat(payload["target_date"]),
            milestones=payload.get("milestones", []),
            daily_focus=payload.get("daily_focus", False),
            vision_board=payload.get("vision_board", False),
            journaling=payload.get("journaling", False),
        )

        return {
            "success": True,
            "goal": goal.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goals")
async def get_goals(category: str | None = None, status: str | None = None):
    """Get goals with optional filters."""
    system = get_life_management_system()

    goals = list(system.goals.values())

    if category:
        goals = [g for g in goals if g.category.value == category]
    if status:
        goals = [g for g in goals if g.status.value == status]

    return {
        "success": True,
        "goals": [goal.__dict__ for goal in goals],
        "total": len(goals),
    }


@router.put("/goals/{goal_id}/progress")
async def update_goal_progress(goal_id: str, payload: dict[str, Any]):
    """Update goal progress."""
    system = get_life_management_system()

    try:
        success = system.update_goal_progress(goal_id, payload["progress"])

        if not success:
            raise HTTPException(status_code=404, detail="Goal not found")

        return {
            "success": True,
            "message": "Goal progress updated",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ HABIT TRACKING ============


@router.post("/habits")
async def create_habit(payload: dict[str, Any]):
    """Create a new habit."""
    system = get_life_management_system()

    try:
        habit = system.create_habit(
            title=payload.get("title"),
            description=payload.get("description", ""),
            frequency=HabitFrequency(payload.get("frequency")),
            target_time=payload.get("target_time"),
            linked_goal_id=payload.get("linked_goal_id"),
            difficulty=payload.get("difficulty", "medium"),
        )

        return {
            "success": True,
            "habit": habit.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/habits")
async def get_habits(status: str | None = None):
    """Get habits with optional filter."""
    system = get_life_management_system()

    habits = list(system.habits.values())

    if status:
        habits = [h for h in habits if h.status.value == status]

    return {
        "success": True,
        "habits": [habit.__dict__ for habit in habits],
        "total": len(habits),
    }


@router.post("/habits/{habit_id}/entry")
async def log_habit_entry(habit_id: str, payload: dict[str, Any]):
    """Log habit entry for today."""
    system = get_life_management_system()

    try:
        entry = system.log_habit_entry(
            habit_id=habit_id,
            completed=payload.get("completed", False),
            mood_before=MoodLevel(payload["mood_before"]) if payload.get("mood_before") else None,
            mood_after=MoodLevel(payload["mood_after"]) if payload.get("mood_after") else None,
            notes=payload.get("notes", ""),
        )

        return {
            "success": True,
            "entry": entry.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/habits/{habit_id}/streak")
async def get_habit_streak(habit_id: str):
    """Get habit streak."""
    system = get_life_management_system()

    streak = system.get_habit_streak(habit_id)

    return {
        "success": True,
        "streak": streak,
    }


# ============ DAILY MOOD TRACKING ============


@router.post("/mood")
async def log_daily_mood(payload: dict[str, Any]):
    """Log daily mood."""
    system = get_life_management_system()

    try:
        daily_mood = system.log_daily_mood(
            mood_morning=MoodLevel(payload["mood_morning"]) if payload.get("mood_morning") else None,
            mood_afternoon=MoodLevel(payload["mood_afternoon"]) if payload.get("mood_afternoon") else None,
            mood_evening=MoodLevel(payload["mood_evening"]) if payload.get("mood_evening") else None,
            mood_night=MoodLevel(payload["mood_night"]) if payload.get("mood_night") else None,
            energy_level=payload.get("energy_level", 5),
            stress_level=payload.get("stress_level", 5),
            sleep_quality=payload.get("sleep_quality", 5),
            notes=payload.get("notes", ""),
            gratitude=payload.get("gratitude", []),
            challenges=payload.get("challenges", []),
            achievements=payload.get("achievements", []),
        )

        return {
            "success": True,
            "daily_mood": daily_mood.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mood/trends")
async def get_mood_trends(days: int = 7):
    """Get mood trends for the last N days."""
    system = get_life_management_system()

    trends = system.get_mood_trends(days)

    return {
        "success": True,
        "trends": trends,
    }


# ============ PERSONALIZED ADVICE ============


@router.post("/advice")
async def generate_advice(payload: dict[str, Any]):
    """Generate personalized advice."""
    system = get_life_management_system()

    try:
        advice = system.generate_advice(
            category=AdviceCategory(payload["category"]),
            context=payload.get("context"),
        )

        return {
            "success": True,
            "advice": advice.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advice/today")
async def get_advice_for_today():
    """Get personalized advice for today."""
    system = get_life_management_system()

    advice = system.get_advice_for_today()

    return {
        "success": True,
        "advice": [advice.__dict__ for advice in advice],
    }


# ============ PC USAGE TRACKING ============


@router.post("/pc/session/start")
async def start_pc_session(payload: dict[str, Any]):
    """Start PC usage session."""
    system = get_life_management_system()

    try:
        session = system.start_pc_session(category=payload.get("category", "work"))

        return {
            "success": True,
            "session": session.__dict__,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pc/session/{session_id}/end")
async def end_pc_session(session_id: str, payload: dict[str, Any]):
    """End PC usage session."""
    system = get_life_management_system()

    try:
        success = system.end_pc_session(
            session_id=session_id,
            productivity_score=payload.get("productivity_score", 5),
            task_completed=payload.get("task_completed", False),
            distractions=payload.get("distractions", []),
        )

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "success": True,
            "message": "Session ended",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pc/usage/{date}")
async def get_daily_pc_usage(date: str):
    """Get daily PC usage statistics."""
    system = get_life_management_system()

    try:
        usage = system.get_daily_pc_usage(datetime.strptime(date, "%Y-%m-%d"))

        return {
            "success": True,
            "usage": usage,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ DAILY SUMMARY ============


@router.get("/summary")
async def get_daily_summary():
    """Get daily summary of all life management metrics."""
    system = get_life_management_system()

    try:
        summary = system.get_daily_summary()

        return {
            "success": True,
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/merlin-insight")
async def get_merlin_insight():
    """Get MERLIN insight on personal life."""
    system = get_life_management_system()

    try:
        insight = system.get_merlin_insight()

        return {
            "success": True,
            "insight": insight,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
