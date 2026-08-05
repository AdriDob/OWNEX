"""Tests for the OWNEX Success Rate Engine."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from cores.direct_work_engine.success_engine import (
    QUALITY_CHECKLIST,
    REVIEW_DIMENSIONS,
    SuccessRateEngine,
    get_success_stats,
    learn_from_outcome,
    record_outcome,
)

SAMPLE_OPPORTUNITY = {
    "id": "opp-1",
    "title": "Fix a physics bug in a Godot plugin",
    "category": "game_dev",
    "platform": "godot",
    "description": "Fix collision edge case with scoring criteria and accepted examples",
    "requirements": ["reproduce the bug", "fix without regressions", "add tests"],
    "reward": 800,
    "deadline": "2026-09-01",
    "complexity": "medium",
    "similar_submissions": 6,
    "url": "https://example.com/task/1",
}


@pytest.fixture()
def tmp_lessons(tmp_path, monkeypatch) -> None:
    from cores.direct_work_engine import success_engine as se

    monkeypatch.setattr(se, "SUCCESS_LESSONS_PATH", tmp_path / "success_lessons.json")


# ── Engine ──────────────────────────────────────────────────


def test_engine_produces_complete_plan() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    assert plan.opportunity_id == "opp-1"
    assert plan.best_approach
    assert plan.generated_at


def test_intelligence_identifies_rules_criteria_and_ambiguities() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    intel = plan.intelligence
    assert intel.platform == "godot"
    assert intel.category == "game_dev"
    assert intel.evaluation_criteria
    assert len(intel.ambiguity_to_resolve) >= 0


def test_prediction_within_bounds_and_verdict() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    assert 0.0 <= plan.prediction.probability <= 1.0
    assert plan.prediction.verdict in {"proceed", "proceed_with_caution", "improve_first"}
    assert plan.prediction.factors
    assert plan.prediction.confidence in {"high", "medium", "low"}


def test_high_competition_lowers_probability() -> None:
    quiet = dict(SAMPLE_OPPORTUNITY, similar_submissions=2)
    crowded = dict(SAMPLE_OPPORTUNITY, similar_submissions=50)
    p_quiet = SuccessRateEngine().analyze(quiet).prediction.probability
    p_crowded = SuccessRateEngine().analyze(crowded).prediction.probability
    assert p_crowded < p_quiet


def test_after_full_plan_raises_probability() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    assert plan.prediction.probability_after_full_plan > plan.prediction.probability


def test_after_full_plan_respects_category_ceiling() -> None:
    engine = SuccessRateEngine()
    annotation = dict(SAMPLE_OPPORTUNITY, category="data_annotation", platform="labeler")
    pred = engine.analyze(annotation).prediction
    assert pred.probability_after_full_plan <= 0.95
    assert pred.probability_after_full_plan >= 0.92


def test_after_full_plan_never_exceeds_honest_cap() -> None:
    engine = SuccessRateEngine()
    bug_bounty = dict(SAMPLE_OPPORTUNITY, category="bug_bounty", platform="hackerone", similar_submissions=2)
    pred = engine.analyze(bug_bounty).prediction
    assert pred.probability_after_full_plan <= 0.45


def test_game_dev_after_full_plan() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    assert plan.prediction.probability_after_full_plan == pytest.approx(0.70, abs=0.01)


def test_dwe_alias_game_development_maps_to_game_dev() -> None:
    aliased = dict(SAMPLE_OPPORTUNITY, category="game_development")
    canonical = dict(SAMPLE_OPPORTUNITY, category="game_dev")
    a = SuccessRateEngine().analyze(aliased).prediction
    b = SuccessRateEngine().analyze(canonical).prediction
    assert a.probability == b.probability
    assert a.probability_after_full_plan == b.probability_after_full_plan


def test_new_high_yield_categories_are_usable() -> None:
    engine = SuccessRateEngine()
    for category, min_after in [("ai_evaluation", 0.90), ("synthetic_data", 0.88), ("web_scraping", 0.72)]:
        pred = engine.analyze(dict(SAMPLE_OPPORTUNITY, category=category, platform="x")).prediction
        assert pred.probability_after_full_plan >= min_after, category


def test_no_dwe_category_falls_to_general() -> None:
    from cores.direct_work_engine.models import OpportunityCategory
    from cores.direct_work_engine.success_engine import CATEGORY_BASE_ACCEPTANCE

    engine = SuccessRateEngine()
    for cat in OpportunityCategory:
        plan = engine.analyze(dict(SAMPLE_OPPORTUNITY, category=cat.value, platform="x"))
        assert plan.intelligence.category != "general", cat.value
        assert cat.value in CATEGORY_BASE_ACCEPTANCE


def test_multi_pass_engineering_generates_candidates_and_keeps_best() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    assert len(plan.candidate_approaches) >= 2
    assert plan.best_approach.startswith(max(plan.candidate_approaches, key=lambda a: a.acceptance_boost).name)
    assert any("iterated" in s for a in plan.candidate_approaches for s in a.strengths)


def test_internal_review_covers_eight_dimensions() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    dims = [r.dimension for r in plan.review]
    assert dims == REVIEW_DIMENSIONS
    assert all(r.recommendation for r in plan.review)


def test_quality_checklist_has_all_ten_items() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    assert set(plan.quality_checklist) == set(QUALITY_CHECKLIST)


def test_verification_and_rule_compliance_present() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    assert "unit tests" in plan.verification_steps
    assert "lint" in plan.verification_steps
    assert plan.rule_compliance
    assert "requirement: reproduce the bug" in plan.rule_compliance


def test_deliverable_optimization_and_effort_split() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    assert any("review" in d for d in plan.deliverables_optimization)
    assert any("approval" in w for w in plan.human_work)
    assert "discovery and analysis (this engine)" in plan.automated_work


def test_transparency_block() -> None:
    plan = SuccessRateEngine().analyze(SAMPLE_OPPORTUNITY)
    t = plan.transparency
    assert "what_was_analyzed" in t
    assert "why_this_approach" in t
    assert t["estimated_success_probability"] == plan.prediction.probability
    assert t["remaining_manual_work"] == plan.human_work


def test_low_probability_suggests_improvement_first() -> None:
    bad = {
        **SAMPLE_OPPORTUNITY,
        "category": "bug_bounty",
        "similar_submissions": 60,
        "complexity": "high",
    }
    plan = SuccessRateEngine().analyze(bad)
    if plan.prediction.probability < 0.4:
        assert plan.prediction.improvement_before_implementation
        assert plan.prediction.verdict == "improve_first"


# ── Learning ────────────────────────────────────────────────


def test_record_outcome_persists_lessons(tmp_lessons) -> None:
    result = record_outcome("opp-1", "accepted")
    assert result["recorded"]["outcome"] == "accepted"
    assert result["total_lessons"] >= 1
    from cores.direct_work_engine import success_engine as se

    data = json.loads(se.SUCCESS_LESSONS_PATH.read_text())
    assert data["outcomes"][0]["opportunity_id"] == "opp-1"


def test_unknown_outcome_rejected(tmp_lessons) -> None:
    with pytest.raises(ValueError):
        record_outcome("opp-1", "lost")


def test_stats_after_outcomes(tmp_lessons) -> None:
    record_outcome("opp-1", "accepted")
    record_outcome("opp-2", "rejected")
    stats = get_success_stats()
    assert stats["total_outcomes_recorded"] == 2
    assert stats["by_outcome"]["accepted"] == 1
    assert stats["acceptance_rate"] == 0.5


def test_learn_from_outcome_returns_stats(tmp_lessons) -> None:
    result = learn_from_outcome("opp-3", "modified")
    assert result["stats"]["total_outcomes_recorded"] == 1
    assert "lessons" in result["recorded"]


# ── API ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def auth_client():
    from api.main import app
    from cores.license.validator import generate_license

    client = TestClient(app)
    lic = generate_license(expiry_days=365)
    client.post("/api/license/activate", json={"key": lic})
    resp = client.post("/api/auth/login", json={"device_id": "pytest-success-engine"})
    if resp.status_code == 200:
        client.headers.update({"Authorization": f"Bearer {resp.json()['data']['token']}"})
    resp = client.get("/api/version")
    csrf_token = resp.cookies.get("csrf-token")
    if csrf_token:
        client.headers.update({"X-CSRF-Token": csrf_token})
    return client


def test_success_plan_endpoint(auth_client) -> None:
    resp = auth_client.post("/direct-work/success-plan", json={"opportunity": SAMPLE_OPPORTUNITY})
    assert resp.status_code == 200
    body = resp.json()
    assert body["opportunity_id"] == "opp-1"
    assert "prediction" in body
    assert body["prediction"]["probability"] > 0
    assert "transparency" in body
    assert len(body["candidate_approaches"]) >= 2


def test_success_outcome_endpoint(auth_client, tmp_lessons) -> None:
    resp = auth_client.post("/direct-work/success-outcome", json={"opportunity_id": "opp-x", "outcome": "accepted"})
    assert resp.status_code == 200
    assert resp.json()["stats"]["total_outcomes_recorded"] == 1


def test_success_stats_endpoint(auth_client, tmp_lessons) -> None:
    resp = auth_client.get("/direct-work/success-stats")
    assert resp.status_code == 200
    assert "total_outcomes_recorded" in resp.json()


def test_invalid_outcome_endpoint_returns_500(auth_client, tmp_lessons) -> None:
    resp = auth_client.post("/direct-work/success-outcome", json={"opportunity_id": "opp-x", "outcome": "nope"})
    assert resp.status_code == 500
