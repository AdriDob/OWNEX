"""Tests para el Application Assistant (plan asistido de postulaciones)."""

from __future__ import annotations

import pytest

from core.application_assistant import (
    STATUS_ACCEPTED,
    ApplicationAssistant,
    get_application_assistant,
)


@pytest.fixture()
def assistant(tmp_path):
    return ApplicationAssistant(store_path=tmp_path / "applications.json")


class TestPlan:
    def test_plan_has_five_platforms_in_priority_order(self, assistant: ApplicationAssistant) -> None:
        plan = assistant.get_plan()
        keys = [p["key"] for p in plan["platforms"]]
        assert keys == ["outlier", "mercor", "alignerr", "mindrift", "fiverr"]

    def test_steps_have_required_keys(self, assistant: ApplicationAssistant) -> None:
        plan = assistant.get_plan()
        for platform in plan["platforms"]:
            assert platform["steps"], platform["key"]
            for step in platform["steps"]:
                assert {"id", "title", "detail", "done"} <= set(step)

    def test_fresh_plan_starts_pending_and_zero_progress(self, assistant: ApplicationAssistant) -> None:
        plan = assistant.get_plan()
        first = plan["platforms"][0]
        assert first["status"] == "pending"
        assert first["completed_steps"] == 0
        assert all(not step["done"] for step in first["steps"])

    def test_suggested_answers_is_dict(self, assistant: ApplicationAssistant) -> None:
        assert isinstance(assistant.get_plan()["suggested_answers"], dict)


class TestCompleteStep:
    def test_complete_step_persists_across_instances(self, tmp_path) -> None:
        store = tmp_path / "applications.json"
        a1 = ApplicationAssistant(store_path=store)
        a1.complete_step("outlier", "create_account")

        a2 = ApplicationAssistant(store_path=store)
        plan = a2.get_plan()
        outlier = plan["platforms"][0]
        done_ids = {s["id"] for s in outlier["steps"] if s["done"]}
        assert done_ids == {"create_account"}
        assert outlier["completed_steps"] == 1

    def test_unknown_platform_raises(self, assistant: ApplicationAssistant) -> None:
        with pytest.raises(KeyError):
            assistant.complete_step("nope", "create_account")

    def test_unknown_step_raises(self, assistant: ApplicationAssistant) -> None:
        with pytest.raises(KeyError):
            assistant.complete_step("outlier", "nope")


class TestStatus:
    def test_set_status_persists(self, tmp_path) -> None:
        store = tmp_path / "applications.json"
        a1 = ApplicationAssistant(store_path=store)
        a1.set_status("mercor", STATUS_ACCEPTED)

        a2 = ApplicationAssistant(store_path=store)
        mercor = a2.get_plan()["platforms"][1]
        assert mercor["status"] == STATUS_ACCEPTED

    def test_invalid_status_raises(self, assistant: ApplicationAssistant) -> None:
        with pytest.raises(ValueError):
            assistant.set_status("mercor", "millionaire")

    def test_invalid_platform_raises(self, assistant: ApplicationAssistant) -> None:
        with pytest.raises(KeyError):
            assistant.set_status("nope", "applied")


class TestOverview:
    def test_next_action_points_to_first_pending_of_top_platform(self, assistant: ApplicationAssistant) -> None:
        overview = assistant.overview()
        action = overview["next_action"]
        assert action is not None
        assert action["platform"] == "outlier"
        assert action["step"] == "Crear cuenta en outlier.ai"

    def test_next_action_skips_accepted_platform(self, tmp_path) -> None:
        assistant = ApplicationAssistant(store_path=tmp_path / "a.json")
        assistant.set_status("outlier", STATUS_ACCEPTED)
        action = assistant.overview()["next_action"]
        assert action is not None
        assert action["platform"] == "mercor"

    def test_progress_pct_counts_done_steps(self, tmp_path) -> None:
        assistant = ApplicationAssistant(store_path=tmp_path / "a.json")
        total = sum(p["total_steps"] for p in assistant.get_plan()["platforms"])
        assistant.complete_step("outlier", "create_account")
        overview = assistant.overview()
        assert overview["progress_pct"] == round(1 / total * 100)


class TestSingleton:
    def test_get_application_assistant_returns_same_instance(self) -> None:
        assert get_application_assistant() is get_application_assistant()


class TestApiEndpoints:
    def test_plan_endpoint_via_testclient(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.control import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.get("/api/applications/plan")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["platforms"]) == 5

    def test_status_endpoint_validation(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.control import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        assert client.post("/api/applications/nope/status", json={"status": "applied"}).status_code == 404
        assert client.post("/api/applications/outlier/status", json={"status": "bad"}).status_code == 400
