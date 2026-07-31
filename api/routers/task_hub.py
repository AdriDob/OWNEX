"""Task Hub API — Unified task management across all platforms."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.task_hub.models import TaskStatus
from core.task_hub.sync import get_task_sync

logger = logging.getLogger("ownex.api.task_hub")

router = APIRouter(prefix="/api/task-hub", tags=["task-hub"])


class SyncRequest(BaseModel):
    platform: str | None = None  # If None, sync all platforms


class UpdateStatusRequest(BaseModel):
    task_id: str
    new_status: str  # TaskStatus value


@router.post("/sync")
async def sync_tasks(request: SyncRequest):
    """Sync tasks from one or all platforms."""
    try:
        sync = get_task_sync()

        if request.platform:
            result = await sync.sync_platform(request.platform)
            return {
                "success": True,
                "platform": request.platform,
                "connection": result.to_dict(),
            }
        else:
            results = await sync.sync_all()
            return {
                "success": True,
                "platforms": {k: v.to_dict() for k, v in results.items()},
            }
    except Exception as e:
        logger.error(f"Failed to sync tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/tasks")
def get_tasks(status: str | None = None):
    """Get all tasks, optionally filtered by status."""
    try:
        sync = get_task_sync()
        task_status = TaskStatus(status) if status else None
        tasks = sync.get_all_tasks(task_status)
        return {
            "success": True,
            "tasks": [t.to_dict() for t in tasks],
            "total": len(tasks),
        }
    except Exception as e:
        logger.error(f"Failed to get tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get a specific task by ID."""
    try:
        sync = get_task_sync()
        task = sync.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "success": True,
            "task": task.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/tasks/update-status")
def update_task_status(request: UpdateStatusRequest):
    """Update task status (accept, reject, complete, etc.)."""
    try:
        sync = get_task_sync()
        new_status = TaskStatus(request.new_status)
        success = sync.update_task_status(request.task_id, new_status)

        if not success:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "success": True,
            "task_id": request.task_id,
            "new_status": request.new_status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/connections")
def get_connections():
    """Get all platform connection statuses."""
    try:
        sync = get_task_sync()
        connections = sync.get_connections()
        return {
            "success": True,
            "connections": {k: v.to_dict() for k, v in connections.items()},
        }
    except Exception as e:
        logger.error(f"Failed to get connections: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/dashboard")
def get_dashboard():
    """Get unified dashboard summary."""
    try:
        sync = get_task_sync()
        all_tasks = sync.get_all_tasks()

        # Calculate stats
        total = len(all_tasks)
        pending = len([t for t in all_tasks if t.status == TaskStatus.PENDING])
        in_progress = len([t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS])
        submitted = len([t for t in all_tasks if t.status == TaskStatus.SUBMITTED])
        approved = len([t for t in all_tasks if t.status == TaskStatus.APPROVED])

        # Calculate total potential reward
        total_reward = sum(t.reward for t in all_tasks if t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS])

        # Group by platform
        by_platform: dict[str, int] = {}
        for task in all_tasks:
            by_platform[task.platform] = by_platform.get(task.platform, 0) + 1

        return {
            "success": True,
            "summary": {
                "total_tasks": total,
                "pending": pending,
                "in_progress": in_progress,
                "submitted": submitted,
                "approved": approved,
                "total_potential_reward": total_reward,
            },
            "by_platform": by_platform,
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None
