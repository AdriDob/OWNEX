"""L7+L9 backend: mission hub — overview, target, award, workspace toggles."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CATEYE_CSRF_DISABLED", "1")
    from cores.levels import reset_progression_engine

    reset_progression_engine()
    import api.main as main

    return TestClient(main.app, raise_server_exceptions=False)


class TestOverview:
    def test_overview_shape(self, client):
        r = client.get("/mission-hub/overview")
        assert r.status_code == 200
        data = r.json()
        assert data["mission"]["target_usd"] == 5000.0
        assert data["levels"]["level"] == 1
        assert len(data["workspaces"]) == 10
        roles = {w["id"]: w["role"] for w in data["workspaces"]}
        assert roles["trading"] == "capital_only"
        assert roles["backup_income"] == "last_resort"
        assert roles["bug_bounty"] == "primary"
        assert isinstance(data["next_action"], str)

    def test_overview_target_override(self, client):
        r = client.get("/mission-hub/overview?target_usd=10000")
        assert r.status_code == 200
        assert r.json()["mission"]["target_usd"] == 10000.0


class TestTarget:
    def test_set_and_persist_target(self, client):
        assert client.post("/mission-hub/target", json={"target_usd": 8000}).status_code == 200
        r = client.get("/mission-hub/overview")
        assert r.json()["mission"]["target_usd"] == 8000.0

    def test_invalid_target_rejected(self, client):
        assert client.post("/mission-hub/target", json={"target_usd": -5}).status_code == 422
        assert client.post("/mission-hub/target", json={"target_usd": 0}).status_code == 422


class TestAward:
    def test_award_known_event(self, client):
        r = client.post("/mission-hub/award", json={"event": "task_completed", "ref_id": "t-1"})
        assert r.status_code == 200
        assert r.json()["xp"] == 10
        levels = client.get("/mission-hub/overview").json()["levels"]
        assert levels["total_xp"] == 10

    def test_award_unknown_event_400_never_invents(self, client):
        r = client.post("/mission-hub/award", json={"event": "clicked_button"})
        assert r.status_code == 400


class TestWorkspaceToggle:
    def test_deactivate_and_reactivate(self, client):
        assert client.post("/mission-hub/workspaces/content_factory/deactivate").status_code == 200
        ws = {w["id"]: w for w in client.get("/mission-hub/overview").json()["workspaces"]}
        assert ws["content_factory"]["active"] is False
        assert client.post("/mission-hub/workspaces/content_factory/activate").status_code == 200
        ws = {w["id"]: w for w in client.get("/mission-hub/overview").json()["workspaces"]}
        assert ws["content_factory"]["active"] is True

    def test_unknown_workspace_404(self, client):
        assert client.post("/mission-hub/workspaces/nope/activate").status_code == 404
        assert client.post("/mission-hub/workspaces/nope/deactivate").status_code == 404
