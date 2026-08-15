"""Outlook API — calendar agenda, Microsoft To Do, task sync and integration status.

Endpoints:
    GET  /api/outlook/status       — connection + config status
    GET  /api/outlook/agenda       — upcoming calendar events + unread count
    GET  /api/outlook/todo         — Microsoft To Do lists + tasks
    POST /api/outlook/sync         — push local tasks (due_date) to calendar + To Do
    GET  /api/outlook/tasks        — local tasks with their calendar/To Do sync state
"""

from __future__ import annotations

from fastapi import APIRouter

from cores.gateway.schemas import error, ok
from database import db, models

router = APIRouter(prefix="/api/outlook", tags=["outlook"])


@router.get("/status")
async def outlook_status():
    """Return Outlook integration status (configured/connected/user)."""
    try:
        from cores.integrations.outlook.connector import get_outlook_connector
        from cores.integrations.outlook.sync import is_outlook_configured

        configured = is_outlook_configured()
        connector = get_outlook_connector()
        connected = connector.is_connected()
        user = ""
        if configured and connected:
            health = await connector.health()
            user = health.get("user", "")
        return ok(
            {
                "configured": configured,
                "connected": connected,
                "user": user,
            }
        )
    except Exception as exc:
        return error(str(exc), version="1.0")


@router.get("/agenda")
async def outlook_agenda(days_ahead: int = 14, max_results: int = 50):
    """Fetch the Outlook agenda: upcoming events + unread email count."""
    try:
        from cores.integrations.outlook.sync import pull_calendar_agenda

        agenda = await pull_calendar_agenda(days_ahead=days_ahead, max_results=max_results)
        if not agenda.get("configured"):
            return error("Outlook integration is not configured", version="1.0")
        return ok(agenda)
    except Exception as exc:
        return error(str(exc), version="1.0")


@router.get("/todo")
async def outlook_todo():
    """Fetch Microsoft To Do lists + tasks."""
    try:
        from cores.integrations.outlook.sync import pull_todo_lists

        todo = await pull_todo_lists()
        if not todo.get("configured"):
            return error("Outlook integration is not configured", version="1.0")
        return ok(todo)
    except Exception as exc:
        return error(str(exc), version="1.0")


@router.post("/sync")
async def outlook_sync():
    """Push all local tasks with due_date into Outlook calendar + Microsoft To Do."""
    try:
        from cores.integrations.outlook.sync import sync_tasks_to_calendar, sync_tasks_to_todo

        calendar_summary = await sync_tasks_to_calendar()
        todo_summary = await sync_tasks_to_todo()
        if calendar_summary.get("skipped") == -1 and todo_summary.get("todo_skipped") == -1:
            return error("Outlook integration is not configured", version="1.0")
        return ok({"summary": calendar_summary, "todo": todo_summary})
    except Exception as exc:
        return error(str(exc), version="1.0")


@router.get("/tasks")
async def outlook_tasks(limit: int = 100):
    """List local tasks with their calendar sync state."""
    try:
        session = db.SessionLocal()
        try:
            tasks = (
                session.query(models.Task)
                .filter(models.Task.due_date.isnot(None))
                .order_by(models.Task.due_date.asc())
                .limit(limit)
                .all()
            )
            return ok(
                {
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "status": t.status,
                            "priority": t.priority,
                            "due_date": t.due_date.isoformat() if t.due_date else "",
                            "calendar_event_id": t.calendar_event_id,
                            "synced_to_calendar": t.synced_to_calendar == "true",
                            "todo_task_id": t.todo_task_id,
                            "synced_to_todo": t.synced_to_todo == "true",
                            "last_synced_at": t.last_synced_at.isoformat() if t.last_synced_at else "",
                        }
                        for t in tasks
                    ]
                }
            )
        finally:
            session.close()
    except Exception as exc:
        return error(str(exc), version="1.0")
