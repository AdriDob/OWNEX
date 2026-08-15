"""OutlookCalendarSync — two-way sync between local tasks and Microsoft 365.

Push direction (tasks -> Outlook):
    Every task with a ``due_date`` and status not in ("completed", "cancelled")
    is materialized as a calendar event AND a Microsoft To Do task. Tasks
    already synced are updated in place (subject/body/start/end) and completed
    tasks are deleted from both surfaces.

Pull direction (Outlook -> tasks):
    The agenda is fetched (email, calendar, contacts, To Do lists) for the
    Mission Control surface; tasks whose event/todo was deleted in Outlook
    are marked unsynced.

Graceful degradation:
    If Outlook credentials are not configured, every entry point returns an
    explicit "not configured" state — nothing fails hard.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from database import db, models

logger = logging.getLogger("orion.integrations.outlook.sync")

DEFAULT_EVENT_DURATION_MINUTES = 60
DEFAULT_DAYS_AHEAD = 14
TODO_LIST_NAME = "OWNEX"

_OUTLOOK_CHANNELS = ("email", "outlook")


def is_outlook_configured() -> bool:
    """True when Outlook credentials are available (env or IdentityVault)."""
    try:
        from cores.integrations.outlook.connector import get_outlook_connector

        connector = get_outlook_connector()
        return bool(
            connector._client_id or connector._client_secret or connector._tenant_id or _vault_has_outlook_credentials()
        )
    except Exception:
        return False


def _vault_has_outlook_credentials() -> bool:
    try:
        from cores.identity_vault import get_identity_vault

        vault = get_identity_vault()
        return bool(vault.get("outlook_client_id", "") and vault.get("outlook_client_secret", ""))
    except Exception:
        return False


def _event_window(due: datetime, duration_minutes: int = DEFAULT_EVENT_DURATION_MINUTES) -> tuple[str, str]:
    """Build the start/end ISO strings for an event from a due date.

    The event is scheduled to *end* at the due moment — the working window
    is the ``duration_minutes`` right before it.
    """
    end = due
    start = end - timedelta(minutes=duration_minutes)
    return start.isoformat(), end.isoformat()


def _get_connector():
    from cores.integrations.outlook.connector import get_outlook_connector

    return get_outlook_connector()


async def sync_tasks_to_calendar() -> dict:
    """Push all local tasks with due_date into the Outlook calendar.

    Returns a summary dict with counts of created/updated/deleted/skipped.
    """
    summary = {"created": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}
    connector = _get_connector()

    if not is_outlook_configured():
        summary["skipped"] = -1
        logger.info("[OUTLOOK-SYNC] Not configured — skipping push")
        return summary

    if not connector.is_connected() and not await connector.connect():
        summary["skipped"] = -1
        logger.warning("[OUTLOOK-SYNC] Connection failed — skipping push")
        return summary

    session = db.SessionLocal()
    try:
        tasks = session.query(models.Task).filter(models.Task.due_date.isnot(None)).all()
    finally:
        session.close()

    for task in tasks:
        try:
            if task.status in ("completed", "cancelled"):
                if task.calendar_event_id and task.synced_to_calendar == "true":
                    await connector.delete_calendar_event(task.calendar_event_id)
                    _mark_unsynced(task.id)
                    summary["deleted"] += 1
                continue

            start_iso, end_iso = _event_window(task.due_date)
            body = task.description or ""
            title = f"[{task.priority or 'medium'}] {task.title}"

            if task.calendar_event_id and task.synced_to_calendar == "true":
                event = await connector.update_calendar_event(
                    task.calendar_event_id,
                    subject=title,
                    start_time=start_iso,
                    end_time=end_iso,
                    body=body,
                )
                if event:
                    summary["updated"] += 1
            else:
                event = await connector.create_calendar_event(
                    subject=title,
                    start_time=start_iso,
                    end_time=end_iso,
                    body=body,
                )
                if event:
                    _mark_synced(task.id, event.id)
                    summary["created"] += 1
                else:
                    summary["errors"] += 1
        except Exception as exc:
            logger.warning("[OUTLOOK-SYNC] Task %s failed: %s", task.id, exc)
            summary["errors"] += 1

    logger.info("[OUTLOOK-SYNC] Push done: %s", summary)
    return summary


async def sync_tasks_to_todo() -> dict:
    """Push all local tasks with due_date into Microsoft To Do.

    Tasks land in a dedicated "OWNEX" list (created on first run). Returns
    a summary dict with counts of created/updated/deleted/skipped/errors.
    """
    summary = {"todo_created": 0, "todo_updated": 0, "todo_deleted": 0, "todo_skipped": 0, "todo_errors": 0}
    connector = _get_connector()

    if not is_outlook_configured():
        summary["todo_skipped"] = -1
        logger.info("[OUTLOOK-SYNC] Not configured — skipping To Do push")
        return summary

    if not connector.is_connected() and not await connector.connect():
        summary["todo_skipped"] = -1
        logger.warning("[OUTLOOK-SYNC] Connection failed — skipping To Do push")
        return summary

    todo_list = await connector.get_or_create_todo_list(TODO_LIST_NAME)
    if todo_list is None:
        summary["todo_errors"] += 1
        logger.warning("[OUTLOOK-SYNC] Could not obtain To Do list '%s'", TODO_LIST_NAME)
        return summary

    session = db.SessionLocal()
    try:
        tasks = session.query(models.Task).filter(models.Task.due_date.isnot(None)).all()
    finally:
        session.close()

    for task in tasks:
        try:
            if task.status in ("completed", "cancelled"):
                if task.todo_task_id and task.synced_to_todo == "true":
                    await connector.delete_todo_task(todo_list.id, task.todo_task_id)
                    _mark_todo_unsynced(task.id)
                    summary["todo_deleted"] += 1
                continue

            due_iso = task.due_date.isoformat() if task.due_date else ""
            importance = "high" if task.priority == "critical" else "normal"

            if task.todo_task_id and task.synced_to_todo == "true":
                todo = await connector.update_todo_task(
                    todo_list.id,
                    task.todo_task_id,
                    title=task.title,
                    due_date=due_iso,
                    importance=importance,
                )
                if todo:
                    summary["todo_updated"] += 1
                else:
                    summary["todo_errors"] += 1
            else:
                todo = await connector.create_todo_task(
                    todo_list.id,
                    title=task.title,
                    due_date=due_iso,
                    importance=importance,
                    body=task.description or "",
                )
                if todo:
                    _mark_todo_synced(task.id, todo.id)
                    summary["todo_created"] += 1
                else:
                    summary["todo_errors"] += 1
        except Exception as exc:
            logger.warning("[OUTLOOK-SYNC] Task %s To Do failed: %s", task.id, exc)
            summary["todo_errors"] += 1

    logger.info("[OUTLOOK-SYNC] To Do push done: %s", summary)
    return summary


async def pull_todo_lists() -> dict:
    """Fetch Microsoft To Do lists + tasks (OWNEX list) for display."""
    connector = _get_connector()
    if not is_outlook_configured():
        return {"configured": False, "lists": [], "tasks": []}

    if not connector.is_connected() and not await connector.connect():
        return {"configured": True, "connected": False, "lists": [], "tasks": []}

    todo_lists = await connector.list_todo_lists()
    tasks: list[dict] = []
    for lst in todo_lists:
        items = await connector.list_todo_tasks(lst.id, max_results=50)
        for item in items:
            tasks.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "status": item.status,
                    "importance": item.importance,
                    "due_date": item.due_date,
                    "list_id": lst.id,
                    "list_name": lst.display_name,
                }
            )
    return {
        "configured": True,
        "connected": True,
        "lists": [{"id": lst.id, "display_name": lst.display_name, "is_owner": lst.is_owner} for lst in todo_lists],
        "tasks": tasks,
    }


async def pull_calendar_agenda(days_ahead: int = DEFAULT_DAYS_AHEAD, max_results: int = 50) -> dict:
    """Fetch the Outlook agenda (events + unread email count) for display."""
    connector = _get_connector()
    if not is_outlook_configured():
        return {"configured": False, "events": [], "unread": 0}

    if not connector.is_connected() and not await connector.connect():
        return {"configured": True, "connected": False, "events": [], "unread": 0}

    events = await connector.list_calendar_events(max_results=max_results, days_ahead=days_ahead)
    emails = await connector.list_emails(max_results=10, unread_only=True)
    return {
        "configured": True,
        "connected": True,
        "events": [
            {
                "id": e.id,
                "subject": e.subject,
                "start": e.start_time,
                "end": e.end_time,
                "location": e.location,
                "organizer": e.organizer,
                "is_online": e.is_online,
                "body_preview": e.body_preview,
            }
            for e in events
        ],
        "unread": len(emails),
    }


def _mark_synced(task_id: int, event_id: str) -> None:
    session = db.SessionLocal()
    try:
        task = session.query(models.Task).filter(models.Task.id == task_id).first()
        if task:
            task.calendar_event_id = event_id
            task.synced_to_calendar = "true"
            task.last_synced_at = datetime.now(UTC)
            session.commit()
    finally:
        session.close()


def _mark_unsynced(task_id: int) -> None:
    session = db.SessionLocal()
    try:
        task = session.query(models.Task).filter(models.Task.id == task_id).first()
        if task:
            task.calendar_event_id = None
            task.synced_to_calendar = "false"
            session.commit()
    finally:
        session.close()


def _mark_todo_synced(task_id: int, todo_task_id: str) -> None:
    session = db.SessionLocal()
    try:
        task = session.query(models.Task).filter(models.Task.id == task_id).first()
        if task:
            task.todo_task_id = todo_task_id
            task.synced_to_todo = "true"
            task.last_synced_at = datetime.now(UTC)
            session.commit()
    finally:
        session.close()


def _mark_todo_unsynced(task_id: int) -> None:
    session = db.SessionLocal()
    try:
        task = session.query(models.Task).filter(models.Task.id == task_id).first()
        if task:
            task.todo_task_id = None
            task.synced_to_todo = "false"
            session.commit()
    finally:
        session.close()


async def run_calendar_sync(*args: object, **kwargs: object) -> dict:
    """Scheduler entry point — pushes tasks (calendar + To Do) and pulls snapshots."""
    summary = await sync_tasks_to_calendar()
    todo_summary = await sync_tasks_to_todo()
    agenda = await pull_calendar_agenda()
    todo = await pull_todo_lists()
    return {
        "push": summary,
        "todo_push": todo_summary,
        "agenda_configured": agenda.get("configured", False),
        "events": len(agenda.get("events", [])),
        "todo_lists": len(todo.get("lists", [])),
        "todo_tasks": len(todo.get("tasks", [])),
    }
