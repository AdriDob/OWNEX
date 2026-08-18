"""Native desktop shell tests — offscreen Qt.

Covers:
- ApiClient: device login wrapper parsing, Bearer auth, 401 re-login retry,
  connectivity degrade, device file persistence.
- MissionControlData: remote dashboard (api source) and local fallback
  (local source) with real DB counts.
- Native views: refresh() populates KPIs/table/source labels.
- MainWindow: navigation triggers view.refresh().
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest

from desktop.native.services.api_client import ApiClient
from desktop.native.services.base import ServiceError
from desktop.native.services.mission import MissionControlData

# ── QApplication (session-scoped) ─────────────────────────────────────


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


# ── Fake httpx transport ──────────────────────────────────────────────


class _Resp:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _BinaryResp:
    def __init__(self, status_code: int, content: bytes = b""):
        self.status_code = status_code
        self.content = content


class _FakeTransport:
    """Sequential fake for httpx.get/post (module-level in api_client)."""

    def __init__(self):
        self.get_responses: dict[str, object] = {}
        self.post_responses: dict[str, object] = {}
        self.get_calls: list[tuple[str, dict | None]] = []
        self.post_calls: list[str] = []

    def _next(self, responses: dict[str, object], url: str) -> object:
        resp = responses.get(url)
        if isinstance(resp, list):
            return resp.pop(0) if resp else None
        return resp

    def get(self, url, params=None, headers=None, timeout=None):
        self.get_calls.append((url, headers))
        return self._next(self.get_responses, url)

    def post(self, url, params=None, json=None, headers=None, timeout=None):
        self.post_calls.append(url)
        return self._next(self.post_responses, url)


# ── ApiClient ─────────────────────────────────────────────────────────


def test_api_client_login_parses_wrapper(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.post_responses["http://127.0.0.1:8000/api/auth/login"] = _Resp(
        200, {"version": "1", "schema": "1", "data": {"token": "tok123", "refresh_token": "r123"}}
    )
    monkeypatch.setattr("desktop.native.services.api_client.httpx.post", fake.post)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.login() is True
    assert client._token == "tok123"  # noqa: SLF001
    assert client._refresh_token == "r123"  # noqa: SLF001
    dev_file = tmp_path / "desktop_device.json"
    assert dev_file.exists()
    assert "desktop-" in dev_file.read_text(encoding="utf-8")


def test_api_client_connected_false_on_error(monkeypatch, tmp_path):
    def _boom(*args, **kwargs):
        raise ConnectionError("refused")

    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", _boom)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.connected() is False


def test_api_client_get_relogs_on_401(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.post_responses["http://127.0.0.1:8000/api/auth/login"] = _Resp(200, {"data": {"token": "tok2"}})
    fake.get_responses["http://127.0.0.1:8000/api/targets"] = [
        _Resp(401),
        _Resp(200, {"items": [{"id": 1, "name": "a.com"}], "total": 1}),
    ]
    monkeypatch.setattr("desktop.native.services.api_client.httpx.post", fake.post)
    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", fake.get)
    client = ApiClient(data_dir=Path(tmp_path))
    data = client.get("/api/targets", {"limit": 5})
    assert data == {"items": [{"id": 1, "name": "a.com"}], "total": 1}
    assert len(fake.get_calls) == 2
    second_headers = fake.get_calls[1][1] or {}
    assert second_headers.get("Authorization") == "Bearer tok2"


def test_api_client_get_never_raises_on_error(monkeypatch, tmp_path):
    def _boom(*args, **kwargs):
        raise ConnectionError("refused")

    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", _boom)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.get("/api/targets") is None


def test_api_client_fetch_targets_items(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.get_responses["http://127.0.0.1:8000/api/targets"] = _Resp(
        200, {"items": [{"id": 3, "name": "x.com"}], "total": 1}
    )
    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", fake.get)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.fetch_targets() == [{"id": 3, "name": "x.com"}]


def test_api_client_post_creates_report(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.post_responses["http://127.0.0.1:8000/api/reports"] = _Resp(201, {"id": 5})
    monkeypatch.setattr("desktop.native.services.api_client.httpx.post", fake.post)
    client = ApiClient(data_dir=Path(tmp_path))
    result = client.post("/api/reports", {"finding_ids": [1, 2]})
    assert result == {"id": 5}
    assert fake.post_calls == ["http://127.0.0.1:8000/api/reports"]


def test_api_client_post_relogs_on_401(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.post_responses["http://127.0.0.1:8000/api/auth/login"] = _Resp(200, {"data": {"token": "tok2"}})
    fake.post_responses["http://127.0.0.1:8000/api/hunt/start"] = [_Resp(401), _Resp(200, {"started": True})]
    monkeypatch.setattr("desktop.native.services.api_client.httpx.post", fake.post)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.start_hunt() == {"started": True}
    assert len(fake.post_calls) == 3  # hunt start + relogin + retry


def test_api_client_post_never_raises_on_error(monkeypatch, tmp_path):
    def _boom(*args, **kwargs):
        raise ConnectionError("refused")

    monkeypatch.setattr("desktop.native.services.api_client.httpx.post", _boom)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.post("/api/hunt/start") is None


def test_api_client_download_writes_file(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.get_responses["http://127.0.0.1:8000/api/findings/7/export-markdown"] = _BinaryResp(200, b"# Finding report\n")
    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", fake.get)
    client = ApiClient(data_dir=Path(tmp_path))
    dest = client.export_finding(7, fmt="markdown")
    assert dest is not None and dest.exists()
    assert dest.read_bytes() == b"# Finding report\n"
    assert dest.parent == Path(tmp_path) / "exports"


def test_api_client_export_report_writes_file(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.get_responses["http://127.0.0.1:8000/api/reports/5/export?format=markdown"] = _BinaryResp(
        200, b"# Final report\n"
    )
    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", fake.get)
    client = ApiClient(data_dir=Path(tmp_path))
    dest = client.export_report(5, fmt="markdown")
    assert dest is not None and dest.exists()
    assert dest.name == "report_5.markdown"
    assert dest.read_bytes() == b"# Final report\n"


def test_api_client_fetch_reports_items(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.get_responses["http://127.0.0.1:8000/api/reports"] = _Resp(
        200, {"items": [{"id": 1, "title": "R"}], "total": 1}
    )
    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", fake.get)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.fetch_reports() == [{"id": 1, "title": "R"}]


def test_api_client_fetch_operations_timeline_events(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.get_responses["http://127.0.0.1:8000/api/operations/timeline"] = _Resp(
        200, {"events": [{"type": "finding"}], "total": 1}
    )
    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", fake.get)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.fetch_operations_timeline() == [{"type": "finding"}]


def test_api_client_fetch_intelligence_state(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.get_responses["http://127.0.0.1:8000/api/intelligence/state"] = _Resp(200, {"snapshots": 3, "findings": 7})
    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", fake.get)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.fetch_intelligence_state() == {"snapshots": 3, "findings": 7}


def test_api_client_fetch_pipeline_stages(monkeypatch, tmp_path):
    fake = _FakeTransport()
    fake.get_responses["http://127.0.0.1:8000/api/pipeline/stages"] = _Resp(200, {"stages": [{"id": "recon"}]})
    monkeypatch.setattr("desktop.native.services.api_client.httpx.get", fake.get)
    client = ApiClient(data_dir=Path(tmp_path))
    assert client.fetch_pipeline_stages() == [{"id": "recon"}]


# ── MissionControlData ────────────────────────────────────────────────


class _FakeApi:
    def __init__(self, connected: bool = True):
        self._connected = connected

    def connected(self) -> bool:
        return self._connected

    def fetch_targets(self, limit: int = 20) -> list[dict]:
        return [
            {"id": 1, "name": "api-target", "domain": "api.example.com", "active": True, "endpoint_count": 5},
            {"id": 2, "name": "inactive", "domain": "old.example.com", "active": False},
        ]

    def fetch_findings(self, limit: int = 50) -> list[dict]:
        return [{"id": 9, "title": "IDOR", "severity": "high", "status": "confirmed", "target_id": 1}]

    def fetch_activity(self, hours: int = 24, limit: int = 40) -> list[dict]:
        return [{"type": "scan", "severity": "info", "title": "target scanned", "timestamp": "2026-08-17T00:00:00Z"}]

    def fetch_direct_work_status(self) -> dict | None:
        return {"running": True}

    def fetch_reports(self, limit: int = 20) -> list[dict] | None:
        return [
            {
                "id": 3,
                "title": "Report one",
                "platform": "hackerone",
                "created_at": "2026-08-17T10:00:00Z",
                "status": "draft",
            }
        ]

    def fetch_report(self, report_id: int) -> dict | None:
        return {"id": report_id, "title": "Report one", "platform": "hackerone", "status": "draft", "content": "# Body"}

    def create_report(self, finding_ids: list[int]) -> dict | None:
        return {"id": 3, "status": "draft"}

    def export_report(self, report_id: int, fmt: str = "markdown") -> Path | None:
        return Path("/tmp/opencode/report_3.md")

    def fetch_finding(self, finding_id: int) -> dict | None:
        return {"id": finding_id, "title": "IDOR", "severity": "high", "status": "confirmed", "target_id": 1}

    def export_finding(self, finding_id: int, fmt: str = "markdown") -> Path | None:
        return Path("/tmp/opencode/finding_9.md")

    def generate_report_from_finding(self, finding_id: int) -> dict | None:
        return {"id": 3, "status": "draft"}

    def fetch_operations_timeline(self, limit: int = 50, hours: int = 72) -> list[dict] | None:
        return [{"time": "10:00", "event": "scan finished", "status": "ok"}]

    def fetch_operations_metrics(self) -> dict | None:
        return {"total_tasks": 12, "completed": 8}

    def fetch_intelligence_state(self) -> dict | None:
        return {"snapshot": {"targets": 2}, "updated_at": "2026-08-17T10:00:00Z"}

    def fetch_system_status(self) -> dict | None:
        return {"status": "running", "score": 92}

    def fetch_health(self) -> dict | None:
        return {"status": "ok", "version": "7.0.0"}

    def fetch_pipeline_stages(self) -> list[dict] | None:
        return [{"stage": "recon", "status": "completed"}]

    def fetch_scan_runs(self, limit: int = 20) -> list[dict] | None:
        return [{"id": 1, "target_id": 1, "status": "completed"}]

    def fetch_hunt_status(self) -> dict | None:
        return {"status": "running"}

    def start_hunt(self) -> dict | None:
        return {"status": "running"}

    def stop_hunt(self) -> dict | None:
        return {"status": "stopped"}


def test_dashboard_remote_source():
    mission = MissionControlData(api=_FakeApi(connected=True))  # type: ignore[arg-type]
    data = mission.get_dashboard()
    assert data["source"] == "api"
    assert data["counts"]["targets"] == 2
    assert data["counts"]["findings"] == 1
    assert data["counts"]["opps"] == "running"
    assert data["counts"]["activity"] == 1
    assert data["targets"][0]["name"] == "api-target"
    assert data["targets"][0]["endpoint_count"] == 5
    assert data["targets"][1]["active"] is False
    assert data["findings"][0]["severity"] == "high"
    assert data["activity"][0]["event_type"] == "scan"


def test_dashboard_local_source_and_counts():
    from database import db, models

    session = db.SessionLocal()
    try:
        t = models.Target(name="local-target", domain="local.example.com", active=True)
        session.add(t)
        session.commit()
        session.refresh(t)
        session.add(models.Finding(target_id=t.id, title="Local finding", severity="low"))
        session.commit()
    finally:
        session.close()

    mission = MissionControlData(api=_FakeApi(connected=False))  # type: ignore[arg-type]
    data = mission.get_dashboard()
    assert data["source"] == "local"
    assert data["counts"]["targets"] >= 1
    assert data["counts"]["findings"] >= 1
    assert data["counts"]["opps"] == "n/a"
    assert isinstance(data["targets"], list)
    assert isinstance(data["findings"], list)


def test_get_targets_remote_mapping():
    mission = MissionControlData(api=_FakeApi(connected=True))  # type: ignore[arg-type]
    targets = mission.get_targets()
    assert len(targets) == 2
    assert targets[0]["endpoint_count"] == 5
    assert targets[0]["roi_score"] == 0.0


def test_get_findings_remote_with_filter():
    mission = MissionControlData(api=_FakeApi(connected=True))  # type: ignore[arg-type]
    confirmed = mission.get_findings(status_filter="confirmed")
    assert len(confirmed) == 1
    assert mission.get_findings(status_filter="open") == []


def test_get_activity_remote_mapping():
    mission = MissionControlData(api=_FakeApi(connected=True))  # type: ignore[arg-type]
    events = mission.get_activity()
    assert events[0]["event_type"] == "scan"
    assert events[0]["timestamp"] == "2026-08-17T00:00:00Z"


# ── Mission domain bridges (reports / operations / system) ─────────────


def test_mission_get_reports_remote():
    mission = MissionControlData(api=_FakeApi(connected=True))  # type: ignore[arg-type]
    reports = mission.get_reports()
    assert reports[0]["id"] == 3
    assert reports[0]["platform"] == "hackerone"
    assert reports[0]["created_at"] == "2026-08-17T10:00:00Z"


def test_mission_get_reports_local():
    from database import db, models

    session = db.SessionLocal()
    try:
        t = models.Target(name="rep-target", domain="rep.example.com", active=True)
        session.add(t)
        session.commit()
        session.refresh(t)
        session.add(models.Report(target=t.name, status="draft", content="# Body"))
        session.commit()
    finally:
        session.close()

    mission = MissionControlData(api=_FakeApi(connected=False))  # type: ignore[arg-type]
    reports = mission.get_reports()
    assert any(r["status"] == "draft" for r in reports)


def test_mission_report_detail_and_export_remote():
    mission = MissionControlData(api=_FakeApi(connected=True))  # type: ignore[arg-type]
    detail = mission.get_report(3)
    assert detail is not None
    assert detail["content"] == "# Body"
    path = mission.export_report(3)
    assert path is not None
    assert path.name == "report_3.md"


def test_mission_report_mutations_raise_offline():
    mission = MissionControlData(api=_FakeApi(connected=False))  # type: ignore[arg-type]
    with pytest.raises(ServiceError):
        mission.create_report([1])
    with pytest.raises(ServiceError):
        mission.export_report(1)
    with pytest.raises(ServiceError):
        mission.submit_report(1, "hackerone")


def test_mission_operations_and_intelligence_remote():
    mission = MissionControlData(api=_FakeApi(connected=True))  # type: ignore[arg-type]
    timeline = mission.get_operations_timeline()
    assert timeline is not None
    assert timeline[0]["event"] == "scan finished"
    metrics = mission.get_operations_metrics()
    assert metrics["total_tasks"] == 12
    state = mission.get_intelligence_state()
    assert state["snapshot"]["targets"] == 2
    assert mission.get_operations_timeline() != []


def test_mission_operations_and_intelligence_offline_honest():
    mission = MissionControlData(api=_FakeApi(connected=False))  # type: ignore[arg-type]
    assert mission.get_operations_timeline() == []
    assert mission.get_operations_metrics() == {}
    assert mission.get_intelligence_state() == {}
    assert mission.get_system_status() == {"status": "offline"}


def test_mission_system_pipeline_scans_hunt_remote():
    mission = MissionControlData(api=_FakeApi(connected=True))  # type: ignore[arg-type]
    status = mission.get_system_status()
    assert status["score"] == 92
    health = mission.get_health()
    assert health["version"] == "7.0.0"
    stages = mission.get_pipeline_stages()
    assert stages is not None
    assert stages[0]["stage"] == "recon"
    runs = mission.get_scan_runs()
    assert runs is not None
    assert runs[0]["status"] == "completed"
    hunt = mission.get_hunt_status()
    assert hunt is not None
    assert hunt["status"] == "running"
    started = mission.start_hunt()
    assert started is not None
    assert started["status"] == "running"
    stopped = mission.stop_hunt()
    assert stopped is not None
    assert stopped["status"] == "stopped"


# ── Native views ──────────────────────────────────────────────────────


class _FakeMission:
    def __init__(self, dashboard: dict | None = None):
        self._dashboard = dashboard or {
            "source": "api",
            "counts": {"targets": 2, "findings": 3, "opps": "running", "activity": 5},
            "targets": [
                {"id": 1, "name": "a.com", "domain": "a.com", "active": True},
                {"id": 2, "name": "b.com", "domain": "b.com", "active": False},
            ],
        }

    def get_dashboard(self) -> dict:
        return self._dashboard

    def get_targets(self) -> list[dict]:
        return self._dashboard.get("targets", [])


def test_mission_view_refresh_populates(qapp):
    from desktop.native.ui.views.mission import MissionControlView

    view = MissionControlView(mission=_FakeMission())  # type: ignore[arg-type]
    view.refresh()
    assert view._targets_kpi.text() == "Targets: 2"  # noqa: SLF001
    assert view._findings_kpi.text() == "Findings: 3"  # noqa: SLF001
    assert view._opps_kpi.text() == "Ops: running"  # noqa: SLF001
    assert view._activity_kpi.text() == "Activity: 5"  # noqa: SLF001
    assert view._source_label.text() == "Source: api"  # noqa: SLF001
    assert view._table.rowCount() == 2  # noqa: SLF001
    assert view._table.item(0, 1).text() == "a.com"  # noqa: SLF001
    assert view._table.item(1, 3).text() == "Inactive"  # noqa: SLF001


def test_findings_view_refresh_populates(qapp):
    from desktop.native.ui.views.findings import FindingsView

    class _M:
        def get_findings(self):
            return [
                {"id": 1, "title": "IDOR", "severity": "high", "status": "confirmed", "target_id": 7},
                {"id": 2, "title": "SSRF", "severity": "medium", "status": "open", "target_id": 7},
            ]

    view = FindingsView()
    view._mission = _M()  # type: ignore[assignment]  # noqa: SLF001
    view.refresh()
    assert view._table.rowCount() == 2  # noqa: SLF001
    assert view._table.item(0, 1).text() == "IDOR"  # noqa: SLF001
    assert view._table.item(1, 2).text() == "medium"  # noqa: SLF001


def test_system_view_refresh_populates(qapp):
    from desktop.native.ui.views.system import SystemView

    view = SystemView()
    view._mission = _FakeMission()  # type: ignore[assignment]  # noqa: SLF001
    view.refresh()
    assert view._targets_kpi.text() == "Targets: 2"  # noqa: SLF001
    assert view._ops_kpi.text() == "Ops: running"  # noqa: SLF001
    assert view._svc_labels["Backend API"].text() == "Backend API: online"  # noqa: SLF001
    assert view._svc_labels["Direct Work"].text() == "Direct Work: running"  # noqa: SLF001


def test_system_view_local_statuses(qapp):
    from desktop.native.ui.views.system import SystemView

    view = SystemView()
    view._mission = _FakeMission({"source": "local", "counts": {"targets": 1, "findings": 0, "opps": "n/a"}})  # type: ignore[assignment]  # noqa: SLF001
    view.refresh()
    assert view._svc_labels["Backend API"].text() == "Backend API: offline"  # noqa: SLF001
    assert view._svc_labels["Scheduler"].text() == "Scheduler: n/a"  # noqa: SLF001


def test_surface_view_refresh_populates(qapp):
    from desktop.native.ui.views.surface import SurfaceView

    view = SurfaceView()
    view._mission = _FakeMission()  # type: ignore[assignment]  # noqa: SLF001
    view.refresh()
    assert view._table.rowCount() == 2  # noqa: SLF001
    assert view._table.item(0, 2).text() == "a.com"  # noqa: SLF001
    assert view._table.item(0, 3).text() == "0"  # noqa: SLF001


def test_terminal_view_defaults(qapp):
    from desktop.native.ui.views.terminal import TerminalView

    view = TerminalView()
    assert view._conn_status.text() == "Disconnected"  # noqa: SLF001
    assert view._connect_btn.text() == "Start Terminal"  # noqa: SLF001
    assert view._send_btn.isEnabled() is False  # noqa: SLF001
    assert view._term.isReadOnly() is True  # noqa: SLF001
    assert view._input is not None  # noqa: SLF001
    assert not hasattr(view, "_cmd_selector")


def test_terminal_view_clear_and_append(qapp):
    from desktop.native.ui.views.terminal import TerminalView

    view = TerminalView()
    view._on_text("\x1b[31mred\x1b[0m\n")  # noqa: SLF001
    assert view._term.toPlainText() == "red\n"  # noqa: SLF001
    view._on_clear()
    assert view._term.toPlainText() == ""  # noqa: SLF001


def test_terminal_view_send_requires_connection(qapp):
    from desktop.native.ui.views.terminal import TerminalView

    view = TerminalView()
    view._input.setText("ls -la")  # noqa: SLF001
    view._on_send()
    assert view._term.toPlainText() == ""  # noqa: SLF001
    assert view._input.text() == "ls -la"  # noqa: SLF001


# ── MainWindow navigation ─────────────────────────────────────────────


def test_nav_triggers_view_refresh(qapp, monkeypatch):
    from PySide6.QtWidgets import QWidget

    from desktop.native.ui.main_window import MainWindow

    calls: list[str] = []

    class _FakeView(QWidget):
        def refresh(self):
            calls.append("refresh")

    monkeypatch.setattr("desktop.native.ui.main_window.load_view", lambda section: _FakeView())
    win = MainWindow()
    assert len(calls) >= 1  # initial navigation
    win._on_nav_clicked("findings")  # noqa: SLF001
    assert len(calls) == 2
    win.close()


def test_mainwindow_auto_refresh_timer(qapp, monkeypatch):
    from PySide6.QtWidgets import QWidget

    from desktop.native.ui.main_window import MainWindow

    monkeypatch.setattr("desktop.native.ui.main_window.load_view", lambda section: QWidget())
    win = MainWindow()
    assert win._auto_refresh is not None  # noqa: SLF001
    assert win._auto_refresh.isActive()
    assert win._auto_refresh.interval() == 10000
    win.close()


def test_mainwindow_auto_refresh_refreshes_active_view(qapp, monkeypatch):
    from PySide6.QtWidgets import QWidget

    from desktop.native.ui.main_window import MainWindow

    calls: list[str] = []

    class _FakeView(QWidget):
        def refresh(self):
            calls.append("refresh")

    monkeypatch.setattr("desktop.native.ui.main_window.load_view", lambda section: _FakeView())
    win = MainWindow()
    win._refresh_active_view()  # noqa: SLF001
    assert calls, "auto-refresh must refresh the active view"
    win.close()


# ── Backend bootstrap (in-process sidecar) ────────────────────────────


def test_local_engines_initialize_db_schema(monkeypatch):
    """Desktop-only processes must provision the DB schema exactly once.

    Regression for the `Ops: error` root cause: MissionControlData never ran
    init_db() (only the server boot does), so local queries on a fresh
    database failed with 'no such table' and the dashboard degraded to error.
    """
    calls: list[str] = []

    def _fake_init_db() -> None:
        calls.append("init")

    monkeypatch.setattr("database.db.init_db", _fake_init_db)
    mission = MissionControlData(api=_FakeApi(connected=False))  # type: ignore[arg-type]
    mission.get_targets()  # first local query triggers schema init
    mission.get_findings()  # subsequent local queries must not re-init
    assert calls == ["init"], "schema must be initialized exactly once per instance"


def test_mission_local_data_persists_across_instances():
    """Desktop-local data must survive app reopen (fresh MissionControlData)."""
    from api.services.data_service import create_target

    create_target(name="reopen-target", domain="reopen.example.com")

    first = MissionControlData(api=_FakeApi(connected=False))  # type: ignore[arg-type]
    assert any(t["name"] == "reopen-target" for t in first.get_targets())

    reopened = MissionControlData(api=_FakeApi(connected=False))  # type: ignore[arg-type]
    assert any(t["name"] == "reopen-target" for t in reopened.get_targets())


def test_mission_view_empty_state_row(qapp):
    from desktop.native.ui.views.mission import MissionControlView

    mission = _FakeMission(
        {
            "source": "local",
            "counts": {"targets": 0, "findings": 0, "opps": "n/a", "activity": 0},
            "targets": [],
        }
    )
    view = MissionControlView(mission=mission)  # type: ignore[arg-type]
    view.refresh()
    assert view._table.rowCount() == 1  # noqa: SLF001
    assert "No targets configured yet" in view._table.item(0, 0).text()  # noqa: SLF001


def test_findings_view_empty_state_row(qapp):
    from desktop.native.ui.views.findings import FindingsView

    class _M:
        def get_findings(self):
            return []

    view = FindingsView()
    view._mission = _M()  # type: ignore[assignment]  # noqa: SLF001
    view.refresh()
    assert view._table.rowCount() == 1  # noqa: SLF001
    assert "No findings yet" in view._table.item(0, 0).text()  # noqa: SLF001


def test_surface_view_empty_state_and_add_target(qapp, monkeypatch):
    from desktop.native.ui.views.surface import SurfaceView

    class _M:
        def get_targets(self):
            return []

    created: list[tuple[str, str | None]] = []

    def _fake_create(name: str, domain: str | None):
        created.append((name, domain))
        return {"id": 1, "name": name, "domain": domain, "duplicate": False}

    monkeypatch.setattr("api.services.data_service.create_target", _fake_create)
    inputs = iter([("new-target.example.com", True), ("example.com", True)])
    monkeypatch.setattr("desktop.native.ui.views.surface.QInputDialog.getText", lambda *a: next(inputs))
    view = SurfaceView()
    view._mission = _M()  # type: ignore[assignment]  # noqa: SLF001
    view.refresh()
    assert view._table.rowCount() == 1  # noqa: SLF001
    assert "No targets configured yet" in view._table.item(0, 0).text()  # noqa: SLF001
    view._add_target()  # noqa: SLF001
    assert created == [("new-target.example.com", "example.com")]


def test_surface_view_add_target_duplicate_notice(qapp, monkeypatch):
    from desktop.native.ui.views.surface import SurfaceView

    class _M:
        def get_targets(self):
            return []

    monkeypatch.setattr(
        "api.services.data_service.create_target",
        lambda name, domain=None: {"id": 7, "name": name, "domain": domain, "duplicate": True},
    )
    monkeypatch.setattr("desktop.native.ui.views.surface.QInputDialog.getText", lambda *a: ("dup.example.com", True))
    notices: list[str] = []
    monkeypatch.setattr(
        "desktop.native.ui.views.surface.QMessageBox.information", lambda *a, **k: notices.append(str(a[2]))
    )
    view = SurfaceView()
    view._mission = _M()  # type: ignore[assignment]  # noqa: SLF001
    view._add_target()  # noqa: SLF001
    assert notices and "already exists" in notices[0]


def test_backend_alive_false_when_unreachable():
    from desktop.native.services import backend

    assert backend.backend_alive("http://127.0.0.1:1") is False


def test_backend_alive_true_with_server():
    import http.server
    import socket
    import threading

    from desktop.native.services import backend

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        def log_message(self, format, *args):  # noqa: ARG002
            pass

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        assert backend.backend_alive(f"http://127.0.0.1:{port}") is True
    finally:
        server.shutdown()


def test_ensure_backend_running_skips_when_alive(monkeypatch):
    from desktop.native.services import backend

    monkeypatch.setattr(backend, "backend_alive", lambda base_url="": True)
    monkeypatch.setattr(backend, "_start_server_thread", lambda: pytest.fail("must not start a thread"))
    assert backend.ensure_backend_running() is True


def test_ensure_backend_running_starts_thread(monkeypatch):
    import threading

    from desktop.native.services import backend

    monkeypatch.setattr(backend, "backend_alive", lambda base_url="": False)
    started: list[str] = []

    def _fake_start():
        thread = threading.Thread(target=lambda: started.append("serve"), daemon=True)
        thread.start()
        return thread

    monkeypatch.setattr(backend, "_start_server_thread", _fake_start)
    monkeypatch.setattr(backend, "_wait_alive", lambda base_url, timeout: False)
    assert backend.ensure_backend_running() is False
    assert started == ["serve"]
