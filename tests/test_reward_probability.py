"""Personal reward probability + funnel + evidence gate (HIGH_UPSIDE_90D plan).

P1 PRIOR_EXTERNO is a labeled weak prior, never a personal rate.
P2 posterior updates ONLY from verified outcomes. P6 evidence gate forbids
fake confidence. P4 funnel distinguishes every stage with real counts.
"""

from __future__ import annotations

import pytest

from cores.direct_work_engine.reward_probability import (
    FUNNEL_STAGES,
    NICHE_AI_LLM,
    NICHE_API_AUTH,
    NICHE_WEB3,
    NICHE_WEB_CLASSIC,
    FunnelTracker,
    PersonalRewardProbability,
    evidence_label,
    get_external_prior,
    niche_for_category,
    prior_midpoint,
)


def _engine(tmp_path):
    return PersonalRewardProbability(tmp_path / "outcomes.jsonl")


def _funnel(tmp_path):
    return FunnelTracker(tmp_path / "funnel.jsonl")


class TestExternalPrior:
    def test_prior_is_labeled_external(self):
        p = get_external_prior(NICHE_WEB3)
        assert p.label == "PRIOR_EXTERNO"
        assert p.source == "market-average-public-programs-no-history"

    def test_prior_midpoint_is_small(self):
        # Weak prior: single-digit end-to-end probability, never a promise.
        for niche in (NICHE_AI_LLM, NICHE_WEB3, NICHE_API_AUTH, NICHE_WEB_CLASSIC):
            assert 0.0 < prior_midpoint(get_external_prior(niche)) < 0.10

    def test_niche_mapping(self):
        assert niche_for_category("llm_engineering") == NICHE_AI_LLM
        assert niche_for_category("smart_contracts") == NICHE_WEB3
        assert niche_for_category("api_development") == NICHE_API_AUTH
        assert niche_for_category("bug_bounty") == NICHE_WEB_CLASSIC
        assert niche_for_category(None) == "other"
        assert niche_for_category("something_unknown") == "other"


class TestEvidenceGate:
    def test_labels(self):
        assert evidence_label(0) == "NO_EVIDENCE"
        assert evidence_label(2) == "THIN_EVIDENCE"
        assert evidence_label(3) == "LOW"
        assert evidence_label(10) == "MEDIUM"
        assert evidence_label(50) == "HIGH"

    def test_no_outcomes_means_prior_only(self, tmp_path):
        est = _engine(tmp_path).estimate(NICHE_WEB3)
        assert est.n_outcomes == 0
        assert est.evidence_label == "NO_EVIDENCE"
        assert est.source == "PRIOR_EXTERNO"

    def test_two_wins_do_not_make_high_confidence(self, tmp_path):
        e = _engine(tmp_path)
        e.record_outcome(platform="h1", niche=NICHE_WEB3, result="accepted", reward_usd=1000)
        e.record_outcome(platform="h1", niche=NICHE_WEB3, result="accepted", reward_usd=2000)
        est = e.estimate(NICHE_WEB3)
        assert est.evidence_label == "THIN_EVIDENCE"
        assert est.confidence == "low"
        # Prior still dominates: posterior far below naive 2/2 = 1.0
        assert est.p_reward < 0.5


class TestPersonalPosterior:
    def test_invalid_result_rejected(self, tmp_path):
        with pytest.raises(ValueError):
            _engine(tmp_path).record_outcome(platform="h1", niche=NICHE_WEB3, result="maybe")

    def test_duplicate_is_not_a_win(self, tmp_path):
        e = _engine(tmp_path)
        e.record_outcome(platform="h1", niche=NICHE_WEB3, result="duplicate")
        est = e.estimate(NICHE_WEB3)
        assert est.n_wins == 0
        assert est.n_outcomes == 1

    def test_many_wins_converge_to_personal_rate(self, tmp_path):
        e = _engine(tmp_path)
        for _ in range(60):
            e.record_outcome(platform="h1", niche=NICHE_WEB3, result="accepted", reward_usd=100)
        for _ in range(60):
            e.record_outcome(platform="h1", niche=NICHE_WEB3, result="rejected")
        est = e.estimate(NICHE_WEB3)
        assert est.evidence_label == "HIGH"
        assert est.source == "personal"
        # 60/120 = 0.5 blended with weak prior -> near 0.5, not pinned to it
        assert 0.40 < est.p_reward < 0.60

    def test_segmentation_by_platform(self, tmp_path):
        e = _engine(tmp_path)
        e.record_outcome(platform="h1", niche=NICHE_WEB3, result="accepted", reward_usd=500)
        assert e.estimate(NICHE_WEB3, platform="bugcrowd").n_outcomes == 0
        assert e.estimate(NICHE_WEB3, platform="h1").n_outcomes == 1

    def test_hours_and_reward_totals(self, tmp_path):
        e = _engine(tmp_path)
        e.record_outcome(platform="h1", niche=NICHE_WEB3, result="accepted", reward_usd=500, actual_hours=4)
        est = e.estimate(NICHE_WEB3)
        assert est.total_reward_usd == 500.0
        assert est.total_hours == 4.0


class TestFunnel:
    def test_stages_are_fixed_vocabulary(self):
        assert "discovered" in FUNNEL_STAGES and "rewarded" in FUNNEL_STAGES
        assert "paid" not in FUNNEL_STAGES  # PAID lives in the revenue ledger, not the funnel

    def test_invalid_stage_rejected(self, tmp_path):
        with pytest.raises(ValueError):
            _funnel(tmp_path).record("o1", "invented")

    def test_summary_counts_and_math(self, tmp_path):
        f = _funnel(tmp_path)
        f.record("o1", "discovered", platform="hackerone", niche=NICHE_WEB3)
        f.record("o1", "submitted", hours_spent=2.5)
        f.record("o1", "rewarded", reward_usd=500)
        s = f.summary()
        assert s["stages"]["discovered"] == 1
        assert s["stages"]["submitted"] == 1
        assert s["stages"]["accepted"] == 0
        assert s["total_human_hours"] == 2.5
        assert s["total_reward_usd"] == 500.0
        assert s["reward_per_human_hour"] == 200.0

    def test_empty_funnel_is_zero_not_none(self, tmp_path):
        s = _funnel(tmp_path).summary()
        assert s["total_human_hours"] == 0.0
        assert s["reward_per_human_hour"] is None


class TestHighUpside90DMode:
    def _rec(self, **overrides):
        from cores.direct_work_engine.models import (
            Opportunity,
            OpportunityCategory,
            PaymentMethod,
            UserProfile,
            WorkPlatform,
        )
        from cores.direct_work_engine.recommendation import HIGH_UPSIDE_90D_RECOMMENDER_CONFIG

        assert HIGH_UPSIDE_90D_RECOMMENDER_CONFIG.validate()
        opp_defaults = {
            "id": "op-1",
            "title": "Audit AI agent auth",
            "platform": WorkPlatform.OPIRE,
            "category": OpportunityCategory.LLM_ENGINEERING,
            "remote": True,
            "payment": 3000.0,
            "currency": "USD",
            "payment_method": PaymentMethod.PAYPAL,
            "estimated_time_hours": 10.0,
            "evidence_gate_status": "HIGH_CONFIDENCE",
        }
        opp_defaults.update(overrides)
        opp = Opportunity(**opp_defaults)
        profile = UserProfile(name="Adriel", country="Argentina", languages={"es", "en"}, skills={"python"})
        return opp, profile

    def test_mode_ranks_without_breaking(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        opp, profile = self._rec()
        ranked = IntelligentRecommender().recommend([opp], profile, limit=1, mode="high_upside_90d")
        assert len(ranked) == 1
        assert ranked[0].rank == 1

    def test_anti_casino_lines_present(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        opp, profile = self._rec()
        ranked = IntelligentRecommender().recommend([opp], profile, limit=1, mode="high_upside_90d")
        text = "\n".join(ranked[0].recommendation_reasoning)
        assert "EV $" in text  # expected value, never headline alone
        assert "P personal" in text  # probability with evidence label
        assert "Frescura" in text
        assert "Competencia" in text

    def test_other_modes_untouched_by_boost(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        opp, profile = self._rec()
        ranked = IntelligentRecommender().recommend([opp], profile, limit=1, mode="balanced")
        text = "\n".join(ranked[0].recommendation_reasoning)
        assert "P personal" not in text
        assert "Frescura" not in text

    def test_boost_is_bounded(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        opp, profile = self._rec(payment=100000.0)
        ranked = IntelligentRecommender().recommend([opp], profile, limit=1, mode="high_upside_90d")
        base = IntelligentRecommender().recommend([self._rec(payment=100000.0)[0]], profile, limit=1, mode="max_income")
        assert ranked[0].overall_recommendation_score <= base[0].overall_recommendation_score * 1.61


class TestFunnelHooks:
    def test_bridge_submitted_records_funnel(self, tmp_path, monkeypatch):
        from types import SimpleNamespace

        from cores.direct_work_engine.reward_probability import get_funnel_tracker, reset_funnel_tracker
        from cores.revenue_tracker.execution_bridge import record_submission_outcome

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        reset_funnel_tracker()
        rec = SimpleNamespace(
            id="s1",
            opportunity_id="wb-1",
            platform="hackerone",
            status="submitted",
            metadata={"opportunity": {"reward": 500, "title": "XSS", "category": "bug_bounty"}},
            last_error="",
            opportunity_title="XSS",
            attempts=1,
        )
        record_submission_outcome(rec)
        summary = get_funnel_tracker().summary()
        assert summary["stages"]["submitted"] == 1
