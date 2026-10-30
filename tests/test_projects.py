"""Project OS tests — states, priority, dedup, persist, seeds, endpoints."""

from __future__ import annotations

import pytest

from cores.projects.models import (
    AutomationLevel,
    ProjectState,
    ProjectTask,
    TaskState,
    health_score,
    priority_score,
)
from cores.projects.registry import ProjectStore, finance_for, maintenance_due, next_actions


@pytest.fixture()
def store(tmp_path):
    return ProjectStore(path=tmp_path / "projects.json")


class TestStates:
    def test_ladder_mapping(self) -> None:
        t = ProjectTask(id="x", project_id="p", phase="f", title="t", state=TaskState.READY)
        assert t.to_ladder_rung() == "A1_prepare"
        t.state = TaskState.WAITING
        assert t.to_ladder_rung() == "A3_human_approval"
        t.state = TaskState.BLOCKED
        assert t.to_ladder_rung() == "A5_external_block"

    def test_all_project_states_valid(self) -> None:
        assert len(list(ProjectState)) == 13

    def test_all_task_states_valid(self) -> None:
        assert len(list(TaskState)) == 9


class TestPriority:
    def test_blocked_sinks(self) -> None:
        t = ProjectTask(id="x", project_id="p", phase="f", title="t", financial_impact_usd=9999)
        assert priority_score(t, blocked=True) == 0.0

    def test_money_beats_cosmetic(self) -> None:
        money = ProjectTask(
            id="a", project_id="p", phase="f", title="paid work", financial_impact_usd=500, urgency=8, effort_min=60
        )
        cosmetic = ProjectTask(
            id="b", project_id="p", phase="f", title="pretty button", financial_impact_usd=0, urgency=2, effort_min=30
        )
        assert priority_score(money) > priority_score(cosmetic)

    def test_automation_boosts(self) -> None:
        auto = ProjectTask(id="a", project_id="p", phase="f", title="a", automation=AutomationLevel.AUTOMATICA)
        manual = ProjectTask(id="b", project_id="p", phase="f", title="b", automation=AutomationLevel.MANUAL)
        assert priority_score(auto) > priority_score(manual)


class TestHealth:
    def test_paused_is_dormant(self, store: ProjectStore) -> None:
        p = store.get("ownex")
        assert p is not None
        p.state = ProjectState.PAUSADO
        assert health_score(p)["level"] == "DORMANT"

    def test_blocked_is_critical(self, store: ProjectStore) -> None:
        p = store.get("droppinglabel")
        assert p is not None
        assert health_score(p, blocked=2)["level"] == "CRITICAL"


class TestStore:
    def test_seeds_five_projects(self, store: ProjectStore) -> None:
        ids = {p.id for p in store.list()}
        assert {"ownex", "droppinglabel", "mercado_libre", "adriel_webs", "rastro"} <= ids

    def test_dedup_rejects(self, store: ProjectStore) -> None:
        t = ProjectTask(id="dup1", project_id="ownex", phase="operacion", title="Daily digest 08:00")
        assert store.add_task("ownex", t) is False

    def test_add_and_transition(self, store: ProjectStore) -> None:
        t = ProjectTask(id="new1", project_id="ownex", phase="operacion", title="Tarea nueva única xyz")
        assert store.add_task("ownex", t) is True
        assert store.set_task_state("ownex", "new1", TaskState.DONE, evidence="ok") is True
        got = store.get("ownex")
        assert got is not None
        assert got.tasks["new1"].state == TaskState.DONE

    def test_persist_reload(self, tmp_path) -> None:
        s1 = ProjectStore(path=tmp_path / "p.json")
        assert s1.set_project_state("rastro", ProjectState.CRECIMIENTO) is True
        s2 = ProjectStore(path=tmp_path / "p.json")
        reloaded = s2.get("rastro")
        assert reloaded is not None
        assert reloaded.state == ProjectState.CRECIMIENTO

    def test_next_actions_top3(self, store: ProjectStore) -> None:
        acts = next_actions(store, limit=3)
        assert len(acts) <= 3
        assert all("score" in a and "ladder_rung" in a for a in acts)

    def test_finance_honest_empty(self, store: ProjectStore) -> None:
        fin = finance_for("droppinglabel")
        assert fin["project"] == "droppinglabel"
        assert fin["net_usd"] == 0.0  # no PAID → honest zero, never invented

    def test_maintenance_lists_recurring(self, store: ProjectStore) -> None:
        items = maintenance_due(store)
        assert any(i["recurring"] == "daily" for i in items)


class TestEndpoints:
    def test_portfolio_and_detail(self) -> None:
        from fastapi.testclient import TestClient

        from api.main import app

        c = TestClient(app)
        r = c.post("/api/auth/login", json={"device_id": "test-projects"})
        tok = r.json()["data"]["token"]
        c.headers.update({"Authorization": f"Bearer {tok}"})
        g = c.get("/api/system/pc-health")
        csrf = g.cookies.get("csrf-token")
        if csrf:
            c.headers.update({"X-CSRF-Token": csrf})
        assert c.get("/api/projects").status_code == 200
        assert c.get("/api/projects/next-actions?limit=3").status_code == 200
        assert c.get("/api/projects/maintenance").status_code == 200
        d = c.get("/api/projects/ownex").status_code
        assert d == 200
        assert c.get("/api/projects/nope").status_code == 404
        # invalid transitions fail closed
        assert c.post("/api/projects/ownex/state", json={"state": "nope"}).status_code == 422
