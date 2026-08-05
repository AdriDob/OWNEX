"""Tests for the Fiverr Strategic Engine and Decision Engine routers."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.decision import router as decision_router
from api.routers.fiverr import router as fiverr_router
from api.routers.result_based import router as result_router


def _app() -> TestClient:
    app = FastAPI()
    app.include_router(fiverr_router)
    app.include_router(decision_router)
    app.include_router(result_router)
    return TestClient(app)


class TestFiverrEngine:
    def test_catalog_returns_gigs_with_tiers(self) -> None:
        c = _app()
        r = c.get("/fiverr/catalog")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] >= 10
        gig = body["gigs"][0]
        assert set(gig["pricing"]) == {"starter", "standard", "premium", "band", "delivery_days"}
        assert gig["pricing"]["starter"] > 0

    def test_catalog_filters_by_category(self) -> None:
        c = _app()
        body = c.get("/fiverr/catalog?category=ai_integration").json()
        assert len(body["gigs"]) == 1
        assert body["gigs"][0]["category"] == "ai_integration"

    def test_plan_returns_pipeline_steps(self) -> None:
        c = _app()
        r = c.post("/fiverr/plan", json={"order_id": "o1", "gig_key": "python_automation", "title": "PDF script"})
        assert r.status_code == 200
        steps = [s["step"] for s in r.json()["steps"]]
        assert steps[0] == "requirement_analysis"
        assert steps[-1] == "delivery_package"
        assert len(steps) == 7

    def test_ethics_gate_flags_bad_copy(self) -> None:
        c = _app()
        ok = c.post("/fiverr/ethics-check", json={"text": "I fix bugs fast, clean code"}).json()
        assert ok["passed"] is True
        bad = c.post("/fiverr/ethics-check", json={"text": "bypass captcha guaranteed 100%"}).json()
        assert bad["passed"] is False
        assert bad["tos_violation"] is True

    def test_asset_kb_persists(self) -> None:
        c = _app()
        c.post("/fiverr/asset", json={"name": "load_test", "kind": "module", "source_order_id": "o1"})
        assets = c.get("/fiverr/assets").json()
        assert assets["total_assets"] >= 1
        assert assets["by_kind"].get("module", 0) >= 1

    def test_status_reports_gigs_and_assets(self) -> None:
        c = _app()
        body = c.get("/fiverr/status").json()
        assert body["gigs"] >= 10
        assert "sample_pricing" in body


class TestDecisionEngine:
    def test_evaluate_go_when_worth_it(self) -> None:
        c = _app()
        r = c.post(
            "/decision/evaluate",
            json={
                "task": {
                    "task_id": "t1",
                    "description": "bounty 1000",
                    "estimated_reward_usd": 1000,
                    "estimated_cost_usd": 10,
                    "estimated_duration_hours": 8,
                    "confidence": 0.2,
                }
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["verdict"] == "GO"
        assert body["worth_it"] is True

    def test_evaluate_skip_when_not_worth_it(self) -> None:
        c = _app()
        body = c.post(
            "/decision/evaluate",
            json={
                "task": {
                    "task_id": "t2",
                    "description": "waste of time",
                    "estimated_reward_usd": 5,
                    "estimated_cost_usd": 30,
                    "estimated_duration_hours": 3,
                    "confidence": 0.5,
                }
            },
        ).json()
        assert body["verdict"] == "SKIP"
        assert body["worth_it"] is False

    def test_status(self) -> None:
        c = _app()
        assert c.get("/decision/status").status_code == 200


class TestResultBasedModel:
    def test_bug_bounty_is_level_s(self) -> None:
        c = _app()
        body = c.post(
            "/result-based/classify",
            json={
                "opportunity": {
                    "employment_type": "bounty",
                    "payment": 2000,
                    "remote": True,
                    "international_payment": True,
                }
            },
        ).json()
        assert body["level"] == "S"
        assert body["recommendation"] == "compete"

    def test_ai_eval_is_level_a(self) -> None:
        c = _app()
        body = c.post(
            "/result-based/classify",
            json={"opportunity": {"employment_type": "microtask", "payment": 50}},
        ).json()
        assert body["level"] == "A"

    def test_traditional_is_level_c_skip(self) -> None:
        c = _app()
        body = c.post(
            "/result-based/classify",
            json={
                "opportunity": {"employment_type": "full_time", "interview_required": True, "portfolio_required": True}
            },
        ).json()
        assert body["level"] == "C"

    def test_first_day_guide(self) -> None:
        c = _app()
        body = c.get("/result-based/first-day").json()
        assert len(body["guide"]["steps"]) == 5
        assert body["guide"]["steps"][0]["step"] == 1
        assert "philosophy" in body["guide"]

    def test_first_day_step_progress(self) -> None:
        c = _app()
        c.post("/result-based/first-day/step", params={"step": 1}).json()
        progress = c.get("/result-based/first-day").json()["progress"]
        assert progress["pct"] > 0

    def test_levels_legend(self) -> None:
        c = _app()
        levels = c.get("/result-based/levels").json()
        for lvl in ("S", "A", "B", "C"):
            assert lvl in levels
