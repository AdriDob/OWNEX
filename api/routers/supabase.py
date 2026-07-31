"""
API Router for Supabase Sync
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.supabase.sync_manager import get_supabase_sync_manager

router = APIRouter(prefix="/supabase", tags=["supabase"])


class SyncTaskRequest(BaseModel):
    user_id: str
    task_data: dict[str, Any]


class SyncGoalRequest(BaseModel):
    user_id: str
    goal_data: dict[str, Any]


class SyncHabitRequest(BaseModel):
    user_id: str
    habit_data: dict[str, Any]


class SyncDailyMoodRequest(BaseModel):
    user_id: str
    mood_data: dict[str, Any]


@router.post("/sync/task")
async def sync_task(payload: SyncTaskRequest):
    """Sincronizar tarea con Supabase."""
    try:
        sync_manager = get_supabase_sync_manager()

        if not sync_manager:
            raise HTTPException(status_code=503, detail="Supabase not configured")

        success = sync_manager.sync_task(payload.user_id, payload.task_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to sync task")

        return {"success": True, "message": "Task synced successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/sync/goal")
async def sync_goal(payload: SyncGoalRequest):
    """Sincronizar meta con Supabase."""
    try:
        sync_manager = get_supabase_sync_manager()

        if not sync_manager:
            raise HTTPException(status_code=503, detail="Supabase not configured")

        success = sync_manager.sync_goal(payload.user_id, payload.goal_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to sync goal")

        return {"success": True, "message": "Goal synced successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/sync/habit")
async def sync_habit(payload: SyncHabitRequest):
    """Sincronizar hábito con Supabase."""
    try:
        sync_manager = get_supabase_sync_manager()

        if not sync_manager:
            raise HTTPException(status_code=503, detail="Supabase not configured")

        success = sync_manager.sync_habit(payload.user_id, payload.habit_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to sync habit")

        return {"success": True, "message": "Habit synced successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/sync/daily_mood")
async def sync_daily_mood(payload: SyncDailyMoodRequest):
    """Sincronizar estado de ánimo con Supabase."""
    try:
        sync_manager = get_supabase_sync_manager()

        if not sync_manager:
            raise HTTPException(status_code=503, detail="Supabase not configured")

        success = sync_manager.sync_daily_mood(payload.user_id, payload.mood_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to sync daily mood")

        return {"success": True, "message": "Daily mood synced successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/tasks/{user_id}")
async def get_user_tasks(user_id: str):
    """Obtener tareas del usuario desde Supabase."""
    try:
        sync_manager = get_supabase_sync_manager()

        if not sync_manager:
            raise HTTPException(status_code=503, detail="Supabase not configured")

        tasks = sync_manager.get_user_tasks(user_id)

        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/goals/{user_id}")
async def get_user_goals(user_id: str):
    """Obtener metas del usuario desde Supabase."""
    try:
        sync_manager = get_supabase_sync_manager()

        if not sync_manager:
            raise HTTPException(status_code=503, detail="Supabase not configured")

        goals = sync_manager.get_user_goals(user_id)

        return {"success": True, "goals": goals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/habits/{user_id}")
async def get_user_habits(user_id: str):
    """Obtener hábitos del usuario desde Supabase."""
    try:
        sync_manager = get_supabase_sync_manager()

        if not sync_manager:
            raise HTTPException(status_code=503, detail="Supabase not configured")

        habits = sync_manager.get_user_habits(user_id)

        return {"success": True, "habits": habits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/daily_moods/{user_id}")
async def get_user_daily_moods(user_id: str, limit: int = 7):
    """Obtener estados de ánimo del usuario desde Supabase."""
    try:
        sync_manager = get_supabase_sync_manager()

        if not sync_manager:
            raise HTTPException(status_code=503, detail="Supabase not configured")

        moods = sync_manager.get_user_daily_moods(user_id, limit)

        return {"success": True, "moods": moods}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
