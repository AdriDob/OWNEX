"""Tests for the Outlook calendar sync service (tasks -> calendar)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from database import db, models

db.init_db()


class _FakeEvent:
    def __init__(self, event_id: str) -> None:
        self.id = event_id
        self.subject = "fake"
        self.start_time = ""
        self.end_time = ""
        self.location = ""
        self.organizer = ""
        self.is_online = False
        self.body_preview = ""


class _FakeTodoList:
    def __init__(self, list_id: str, display_name: str = "OWNEX") -> None:
        self.id = list_id
        self.display_name = display_name
        self.is_owner = True


class _FakeTodoTask:
    def __init__(self, task_id: str, title: str = "", due_date: str = "", status: str = "notStarted") -> None:
        self.id = task_id
        self.title = title
        self.status = status
        self.importance = "normal"
        self.due_date = due_date
        self.body_preview = ""


class _FakeConnector:
    """In-memory stand-in for OutlookConnector — records calls, returns fakes."""

    def __init__(self) -> None:
        self.connected = False
        self.created: list[dict] = []
        self.updated: list[dict] = []
        self.deleted: list[str] = []
        self._events: dict[str, _FakeEvent] = {}
        self._todo_lists: dict[str, _FakeTodoList] = {}
        self._todo_tasks: dict[str, list[_FakeTodoTask]] = {}
        self.todo_created: list[dict] = []
        self.todo_updated: list[dict] = []
        self.todo_deleted: list[str] = []

    def is_connected(self) -> bool:
        return self.connected

    async def connect(self) -> bool:
        self.connected = True
        return True

    async def create_calendar_event(self, subject: str, start_time: str, end_time: str, body: str = "") -> _FakeEvent:
        event = _FakeEvent(f"evt-{len(self.created)}")
        event.subject = subject
        event.start_time = start_time
        event.end_time = end_time
        event.body_preview = body
        self.created.append({"subject": subject, "start": start_time, "end": end_time})
        self._events[event.id] = event
        return event

    async def update_calendar_event(
        self,
        event_id: str,
        subject: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        body: str | None = None,
    ) -> _FakeEvent | None:
        event = self._events.get(event_id)
        if event is None:
            return None
        if subject is not None:
            event.subject = subject
        if start_time is not None:
            event.start_time = start_time
        if end_time is not None:
            event.end_time = end_time
        self.updated.append({"id": event_id, "subject": subject})
        return event

    async def delete_calendar_event(self, event_id: str) -> bool:
        self.deleted.append(event_id)
        self._events.pop(event_id, None)
        return True

    async def list_calendar_events(self, max_results: int = 20, days_ahead: int = 14) -> list[_FakeEvent]:
        return list(self._events.values())[:max_results]

    async def list_emails(self, max_results: int = 10, unread_only: bool = False) -> list:
        return []

    async def get_or_create_todo_list(self, display_name: str = "OWNEX") -> _FakeTodoList | None:
        for lst in self._todo_lists.values():
            if lst.display_name.strip().lower() == display_name.strip().lower():
                return lst
        lst = _FakeTodoList(f"list-{len(self._todo_lists)}", display_name)
        self._todo_lists[lst.id] = lst
        self._todo_tasks[lst.id] = []
        return lst

    async def list_todo_lists(self, max_results: int = 50) -> list[_FakeTodoList]:
        return list(self._todo_lists.values())[:max_results]

    async def list_todo_tasks(self, list_id: str, max_results: int = 50) -> list[_FakeTodoTask]:
        return self._todo_tasks.get(list_id, [])[:max_results]

    async def create_todo_task(
        self,
        list_id: str,
        title: str,
        due_date: str = "",
        importance: str = "normal",
        body: str = "",
    ) -> _FakeTodoTask | None:
        tasks = self._todo_tasks.setdefault(list_id, [])
        todo = _FakeTodoTask(f"todo-{len(self.todo_created)}", title, due_date)
        tasks.append(todo)
        self.todo_created.append({"list": list_id, "title": title, "due_date": due_date})
        return todo

    async def update_todo_task(
        self,
        list_id: str,
        task_id: str,
        title: str | None = None,
        due_date: str | None = None,
        status: str | None = None,
        importance: str | None = None,
    ) -> _FakeTodoTask | None:
        for tasks in self._todo_tasks.get(list_id, []):
            if tasks.id == task_id:
                if title is not None:
                    tasks.title = title
                if due_date is not None:
                    tasks.due_date = due_date
                if status is not None:
                    tasks.status = status
                self.todo_updated.append({"id": task_id, "title": title})
                return tasks
        return None

    async def delete_todo_task(self, list_id: str, task_id: str) -> bool:
        self.todo_deleted.append(task_id)
        tasks = self._todo_tasks.get(list_id, [])
        self._todo_tasks[list_id] = [t for t in tasks if t.id != task_id]
        return True


def _make_task(
    due: datetime,
    status: str = "pending",
    synced: bool = False,
    event_id: str | None = None,
    todo_synced: bool = False,
    todo_id: str | None = None,
) -> int:
    task = models.Task(
        title="Task",
        description="Desc",
        status=status,
        priority="high",
        due_date=due,
        synced_to_calendar="true" if synced else "false",
        calendar_event_id=event_id,
        synced_to_todo="true" if todo_synced else "false",
        todo_task_id=todo_id,
    )
    session = db.SessionLocal()
    try:
        session.add(task)
        session.commit()
        return task.id
    finally:
        session.close()


def _cleanup(task_ids: list[int]) -> None:
    session = db.SessionLocal()
    try:
        for tid in task_ids:
            session.query(models.Task).filter(models.Task.id == tid).delete()
        session.commit()
    finally:
        session.close()


def _cleanup_all_due_tasks() -> None:
    session = db.SessionLocal()
    try:
        session.query(models.Task).filter(models.Task.due_date.isnot(None)).delete()
        session.commit()
    finally:
        session.close()


def test_sync_creates_events_for_pending_tasks(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        _cleanup_all_due_tasks()
        due = datetime.now(UTC) + timedelta(hours=5)
        task = _make_task(due)

        fake = _FakeConnector()
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: True)

        summary = await sync_mod.sync_tasks_to_calendar()
        try:
            assert summary["created"] == 1
            assert len(fake.created) == 1
            session = db.SessionLocal()
            try:
                row = session.query(models.Task).filter(models.Task.id == task).first()
                assert row.synced_to_calendar == "true"
                assert row.calendar_event_id is not None
            finally:
                session.close()
        finally:
            _cleanup([task])

    asyncio.run(_run())


def test_sync_updates_existing_events(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        _cleanup_all_due_tasks()
        due = datetime.now(UTC) + timedelta(days=1)
        task = _make_task(due, synced=True, event_id="evt-existing")

        fake = _FakeConnector()
        fake.connected = True
        fake._events["evt-existing"] = _FakeEvent("evt-existing")
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: True)

        summary = await sync_mod.sync_tasks_to_calendar()
        try:
            assert summary["updated"] == 1
            assert summary["created"] == 0
            assert len(fake.updated) == 1
        finally:
            _cleanup([task])

    asyncio.run(_run())


def test_sync_deletes_events_for_completed_tasks(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        _cleanup_all_due_tasks()
        due = datetime.now(UTC) + timedelta(hours=3)
        task = _make_task(due, status="completed", synced=True, event_id="evt-done")

        fake = _FakeConnector()
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: True)

        summary = await sync_mod.sync_tasks_to_calendar()
        try:
            assert summary["deleted"] == 1
            assert fake.deleted == ["evt-done"]
            session = db.SessionLocal()
            try:
                row = session.query(models.Task).filter(models.Task.id == task).first()
                assert row.synced_to_calendar == "false"
                assert row.calendar_event_id is None
            finally:
                session.close()
        finally:
            _cleanup([task])

    asyncio.run(_run())


def test_sync_skips_when_not_configured(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        fake = _FakeConnector()
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: False)

        summary = await sync_mod.sync_tasks_to_calendar()
        assert summary["skipped"] == -1
        assert fake.created == []

    asyncio.run(_run())


def test_pull_agenda_returns_events(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        fake = _FakeConnector()
        fake.connected = True
        fake._events["evt-1"] = _FakeEvent("evt-1")
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: True)

        agenda = await sync_mod.pull_calendar_agenda()
        assert agenda["configured"] is True
        assert agenda["connected"] is True
        assert len(agenda["events"]) == 1

    asyncio.run(_run())


def test_pull_agenda_not_configured(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: _FakeConnector())
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: False)

        agenda = await sync_mod.pull_calendar_agenda()
        assert agenda["configured"] is False

    asyncio.run(_run())


def test_event_window_ends_at_due() -> None:
    from cores.integrations.outlook.sync import _event_window

    due = datetime(2026, 8, 20, 14, 0, tzinfo=UTC)
    start, end = _event_window(due, duration_minutes=60)
    assert end == "2026-08-20T14:00:00+00:00"
    assert start == "2026-08-20T13:00:00+00:00"


def test_todo_sync_creates_tasks_in_ownex_list(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        _cleanup_all_due_tasks()
        due = datetime.now(UTC) + timedelta(hours=5)
        task = _make_task(due)

        fake = _FakeConnector()
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: True)

        summary = await sync_mod.sync_tasks_to_todo()
        try:
            assert summary["todo_created"] == 1
            assert len(fake.todo_created) == 1
            assert fake.todo_created[0]["list"] == "list-0"
            session = db.SessionLocal()
            try:
                row = session.query(models.Task).filter(models.Task.id == task).first()
                assert row.synced_to_todo == "true"
                assert row.todo_task_id is not None
            finally:
                session.close()
        finally:
            _cleanup([task])

    asyncio.run(_run())


def test_todo_sync_updates_existing_tasks(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        _cleanup_all_due_tasks()
        due = datetime.now(UTC) + timedelta(days=1)
        task = _make_task(due, todo_synced=True, todo_id="todo-existing")

        fake = _FakeConnector()
        fake.connected = True
        lst = _FakeTodoList("list-main")
        fake._todo_lists[lst.id] = lst
        fake._todo_tasks[lst.id] = [_FakeTodoTask("todo-existing", "Task")]
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: True)

        summary = await sync_mod.sync_tasks_to_todo()
        try:
            assert summary["todo_updated"] == 1
            assert summary["todo_created"] == 0
            assert len(fake.todo_updated) == 1
        finally:
            _cleanup([task])

    asyncio.run(_run())


def test_todo_sync_deletes_tasks_for_completed(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        _cleanup_all_due_tasks()
        due = datetime.now(UTC) + timedelta(hours=3)
        task = _make_task(due, status="completed", todo_synced=True, todo_id="todo-done")

        fake = _FakeConnector()
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: True)

        summary = await sync_mod.sync_tasks_to_todo()
        try:
            assert summary["todo_deleted"] == 1
            assert fake.todo_deleted == ["todo-done"]
            session = db.SessionLocal()
            try:
                row = session.query(models.Task).filter(models.Task.id == task).first()
                assert row.synced_to_todo == "false"
                assert row.todo_task_id is None
            finally:
                session.close()
        finally:
            _cleanup([task])

    asyncio.run(_run())


def test_todo_sync_skips_when_not_configured(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        fake = _FakeConnector()
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: False)

        summary = await sync_mod.sync_tasks_to_todo()
        assert summary["todo_skipped"] == -1
        assert fake.todo_created == []

    asyncio.run(_run())


def test_pull_todo_lists_returns_lists_and_tasks(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        fake = _FakeConnector()
        fake.connected = True
        lst = _FakeTodoList("list-1", "OWNEX")
        fake._todo_lists[lst.id] = lst
        fake._todo_tasks[lst.id] = [_FakeTodoTask("t1", "Hacer X", "2026-08-20T10:00:00")]
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: True)

        data = await sync_mod.pull_todo_lists()
        assert data["configured"] is True
        assert len(data["lists"]) == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["title"] == "Hacer X"

    asyncio.run(_run())


def test_pull_todo_not_configured(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: _FakeConnector())
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: False)

        data = await sync_mod.pull_todo_lists()
        assert data["configured"] is False

    asyncio.run(_run())


def test_run_calendar_sync_includes_todo(monkeypatch) -> None:
    from cores.integrations.outlook import sync as sync_mod

    async def _run() -> None:
        _cleanup_all_due_tasks()
        fake = _FakeConnector()
        monkeypatch.setattr(sync_mod, "_get_connector", lambda: fake)
        monkeypatch.setattr(sync_mod, "is_outlook_configured", lambda: True)

        result = await sync_mod.run_calendar_sync()
        assert "todo_push" in result
        assert "todo_lists" in result
        assert "todo_tasks" in result

    asyncio.run(_run())
