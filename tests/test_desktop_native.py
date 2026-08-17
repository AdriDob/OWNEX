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

    def post(self, url, json=None, headers=None, timeout=None):
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
