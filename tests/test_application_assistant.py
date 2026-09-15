"""Tests para el Application Assistant (plan asistido de postulaciones)."""

from __future__ import annotations

import pytest

from cores.application_assistant import (
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


class TestPlatformStatus:
    def test_fresh_platform_is_not_connected_with_unknown_facets(self, tmp_path) -> None:
        assistant = ApplicationAssistant(store_path=tmp_path / "a.json")
        st = assistant.get_platform_status("outlier")
        assert st["global_state"] == "NOT_CONNECTED"
        assert st["facets"]["account"] == "pending"
        assert st["facets"]["email"] == "unknown"
        assert st["facets"]["first_payment"] == "unknown"
        assert st["next_action"] is not None
        assert "missing" in st and "account" in st["missing"]

    def test_completed_steps_move_facets_and_global_state(self, tmp_path) -> None:
        assistant = ApplicationAssistant(store_path=tmp_path / "a.json")
        assistant.complete_step("alignerr", "create_account")
        assistant.complete_step("alignerr", "domain_assessment")
        assistant.complete_step("alignerr", "payment_setup")
        st = assistant.get_platform_status("alignerr", allow_interview_paths=True)
        assert st["facets"]["account"] == "done"
        assert st["facets"]["skills"] == "done"
        assert st["facets"]["payment"] == "done"
        assert st["global_state"] in ("READY", "OPERATIONAL")
        assert "account" not in st["missing"]

    def test_accepted_without_payment_evidence_never_claims_first_payment(self, tmp_path) -> None:
        from cores.application_assistant import STATUS_ACCEPTED

        assistant = ApplicationAssistant(store_path=tmp_path / "a.json")
        assistant.set_status("outlier", STATUS_ACCEPTED)
        st = assistant.get_platform_status("outlier")
        assert st["facets"]["first_payment"] == "unknown"

    def test_unknown_platform_raises(self, tmp_path) -> None:
        import pytest

        assistant = ApplicationAssistant(store_path=tmp_path / "a.json")
        with pytest.raises(KeyError):
            assistant.get_platform_status("nope")


class TestPhaseStatusEndpoint:
    def test_phase_status_endpoint_shape(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.control import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.get("/api/applications/outlier/phase-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["platform"] == "outlier"
        assert body["global_state"] == "NOT_CONNECTED"
        assert body["facets"]["first_payment"] == "unknown"
        assert "missing" in body and "what_unlocks" in body

    def test_phase_status_unknown_platform_404(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.control import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        assert client.get("/api/applications/nope/phase-status").status_code == 404


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


class TestZeroBarrierGating:
    """L4: default hides CV/interview steps; opt-in reveals them."""

    def test_default_plan_hides_gated_steps(self, assistant: ApplicationAssistant) -> None:
        plan = assistant.get_plan()
        assert plan["zero_barrier"] is True
        ids = {s["id"] for p in plan["platforms"] for s in p["steps"]}
        assert "resume_linkedin" not in ids
        assert "ai_interview" not in ids
        # assessments stay (registration-or-assessment is allowed)
        assert "coding_assessment" in ids

    def test_opt_in_reveals_all_steps(self, assistant: ApplicationAssistant) -> None:
        plan = assistant.get_plan(allow_interview_paths=True)
        assert plan["zero_barrier"] is False
        ids = {s["id"] for p in plan["platforms"] for s in p["steps"]}
        assert "resume_linkedin" in ids
        assert "ai_interview" in ids

    def test_gated_count_reported(self, assistant: ApplicationAssistant) -> None:
        plan = assistant.get_plan()
        gated = sum(p.get("gated_steps", 0) for p in plan["platforms"])
        assert gated == 4  # outlier CV + mercor CV + mercor interview + alignerr CV

    def test_onboarding_filters_consistently(self, assistant: ApplicationAssistant) -> None:
        ob = assistant.get_onboarding("mercor")
        ids = {c["id"] for c in ob["checklist"]}
        assert "ai_interview" not in ids
        assert "create_account" not in ids  # CV-gated
        assert "technical_screening" in ids  # assessment stays
        ob_full = assistant.get_onboarding("mercor", allow_interview_paths=True)
        full_ids = {c["id"] for c in ob_full["checklist"]}
        assert "ai_interview" in full_ids
        assert "create_account" in full_ids

    def test_complete_gated_step_still_valid(self, tmp_path) -> None:
        a = ApplicationAssistant(store_path=tmp_path / "a.json")
        res = a.complete_step("mercor", "ai_interview")
        assert res["success"] is True
