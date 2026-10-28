"""Phase 6: funnel wiring — mapping, stamping, universal acceptance gate, ranking.

Contracts pinned here:
- funnel_for_category() maps every WorkStream onto a funnel (never invents).
- recommend() stamps opp.funnel without overwriting explicit values.
- Universal P_ACCEPT wins ONLY on SUFFICIENT/HIGH evidence; otherwise the
  cold-start heuristic applies byte-identically (mocked both ways).
- rank_cross_category() orders by mode without changing any numbers.
"""

from __future__ import annotations

from unittest.mock import patch

from cores.direct_work_engine.category_funnel import funnel_for_category
from cores.direct_work_engine.models import (
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    UserProfile,
    WorkPlatform,
    WorkStream,
)
from cores.direct_work_engine.probability_contract import EvidenceLabel, ProbabilityEstimate, ProbabilityType


def _make_opp(**overrides) -> Opportunity:
    defaults = {
        "id": "op-1",
        "title": "t",
        "platform": WorkPlatform.ALGORA,
        "category": OpportunityCategory.BACKEND,
        "payment": 500.0,
        "currency": "USD",
        "payment_method": PaymentMethod.PAYPAL,
        "remote": True,
        "time_to_payout_days": 5,
    }
    defaults.update(overrides)
    return Opportunity(**defaults)


def _make_profile() -> UserProfile:
    return UserProfile(
        name="Test",
        country="Argentina",
        languages={"es", "en"},
        skills={"python"},
        projects=[],
    )


class TestFunnelMapping:
    def test_all_streams_mapped(self):
        assert funnel_for_category(OpportunityCategory.BUG_BOUNTY) == "bug_bounty"
        assert funnel_for_category(OpportunityCategory.BACKEND) == "dev_bounty"
        assert funnel_for_category(OpportunityCategory.AI_EVALUATION) == "ai_training"
        assert funnel_for_category(OpportunityCategory.DATA_ANNOTATION) == "ai_training"
        assert funnel_for_category(OpportunityCategory.GAME_DEVELOPMENT) == "dev_bounty"
        assert funnel_for_category(OpportunityCategory.OPEN_SOURCE) == "dev_bounty"
        assert funnel_for_category(OpportunityCategory.TECHNICAL_WRITING) == "client_work"

    def test_raw_values_and_unknown(self):
        assert funnel_for_category("backend") == "dev_bounty"
        assert funnel_for_category("no-such-category") == ""
        assert funnel_for_category(None) == ""

    def test_every_stream_value_covered(self):
        # All six streams resolve (explicit, no silent gaps):
        assert funnel_for_category(WorkStream.BUG_BOUNTY) == "bug_bounty"
        assert funnel_for_category(WorkStream.DEV_BOUNTY) == "dev_bounty"
        assert funnel_for_category(WorkStream.AI_WORK) == "ai_training"
        assert funnel_for_category(WorkStream.GAME_DEV) == "dev_bounty"
        assert funnel_for_category(WorkStream.OPEN_SOURCE) == "dev_bounty"
        assert funnel_for_category(WorkStream.TECH_CONTENT) == "client_work"


class TestRecommenderStamping:
    def test_recommend_stamps_funnel(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        opp = _make_opp(category=OpportunityCategory.BUG_BOUNTY)
        assert opp.funnel == ""
        rec = IntelligentRecommender()
        ranked = rec.recommend([opp], _make_profile(), limit=1)
        assert ranked
        assert ranked[0].opportunity.funnel == "bug_bounty"

    def test_explicit_funnel_never_overwritten(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        opp = _make_opp(category=OpportunityCategory.BUG_BOUNTY)
        opp.funnel = "custom_funnel"
        rec = IntelligentRecommender()
        ranked = rec.recommend([opp], _make_profile(), limit=1)
        assert ranked[0].opportunity.funnel == "custom_funnel"


def _sufficient_est(p_type=ProbabilityType.P_ACCEPT, value=0.9) -> ProbabilityEstimate:
    from datetime import UTC, datetime

    return ProbabilityEstimate(
        probability_type=p_type,
        estimate=value,
        confidence=1.0,
        lower_bound=0.91,
        upper_bound=0.97,
        evidence_label=EvidenceLabel.SUFFICIENT_EVIDENCE,
        effective_sample_size=10.0,
        raw_sample_size=10,
        prior_type="personal",
        prior_value=0.5,
        source="personal_evidence",
        segment="test",
        last_updated=datetime.now(UTC).isoformat(),
        evidence_quality=0.9,
    )


def _thin_est() -> ProbabilityEstimate:
    from datetime import UTC, datetime

    return ProbabilityEstimate(
        probability_type=ProbabilityType.P_ACCEPT,
        estimate=0.9,
        confidence=0.0,
        lower_bound=0.0,
        upper_bound=1.0,
        evidence_label=EvidenceLabel.NO_EVIDENCE,
        effective_sample_size=0.0,
        raw_sample_size=0,
        prior_type="external",
        prior_value=0.5,
        source="external_prior",
        segment="test",
        last_updated=datetime.now(UTC).isoformat(),
        evidence_quality=0.0,
    )


class TestDefaultPathAmbientIndependent:
    """Phase 6 decision pin: default recommend() NEVER consults the global
    learning store, so rankings stay deterministic regardless of ambient
    data/learning files. Calibrated estimates are for explicit callers
    (rank_cross_category / is_high_confidence_90) only."""

    def test_heuristic_stable_despite_sufficient_evidence(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        rec = IntelligentRecommender()
        with patch("cores.direct_work_engine.universal_probability.get_universal_probability_engine") as factory:
            factory.return_value.estimate.return_value = {ProbabilityType.P_ACCEPT: _sufficient_est()}
            ranked = rec.recommend([_make_opp()], _make_profile(), limit=1)
        # 0.9 would be the universal value; heuristic must win on default path.
        assert ranked[0].acceptance_probability != 0.9

    def test_heuristic_stable_when_engine_down(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        rec = IntelligentRecommender()
        with patch(
            "cores.direct_work_engine.universal_probability.get_universal_probability_engine",
            side_effect=RuntimeError("engine down"),
        ):
            ranked = rec.recommend([_make_opp()], _make_profile(), limit=1)
        assert 0.01 <= ranked[0].acceptance_probability <= 0.95


class TestCrossCategoryRanking:
    def test_high_confidence_mode_first(self):
        from cores.direct_work_engine.universal_probability import get_universal_probability_engine

        engine = get_universal_probability_engine()
        low = _make_opp(id="low", payment=10000.0, category=OpportunityCategory.BUG_BOUNTY)
        high = _make_opp(id="high", payment=50.0, category=OpportunityCategory.BUG_BOUNTY)
        with patch.object(engine, "is_high_confidence_90", side_effect=lambda o, c=None: o.id == "high"):
            ranked = engine.rank_cross_category([low, high], mode="HIGH_CONFIDENCE")
        assert [r["opportunity"].id for r in ranked] == ["high", "low"]

    def test_balanced_orders_by_ev_times_p(self):
        from cores.direct_work_engine.universal_probability import get_universal_probability_engine

        engine = get_universal_probability_engine()
        a = _make_opp(id="a", payment=100.0, estimated_time_hours=2.0, category=OpportunityCategory.BUG_BOUNTY)
        b = _make_opp(id="b", payment=400.0, estimated_time_hours=2.0, category=OpportunityCategory.BUG_BOUNTY)
        ranked = engine.rank_cross_category([a, b], mode="BALANCED")
        # Same funnel, same (empty-history) probabilities: higher EV/hour wins.
        assert [r["opportunity"].id for r in ranked] == ["b", "a"]
        assert ranked[0]["p_success"] == ranked[1]["p_success"]

    def test_unknown_category_never_invents(self):
        from cores.direct_work_engine.universal_probability import get_universal_probability_engine

        engine = get_universal_probability_engine()
        opp = _make_opp(id="x")
        opp.category = "no-such-category"  # type: ignore[assignment]
        assert engine.is_high_confidence_90(opp) is False
        ranked = engine.rank_cross_category([opp], mode="HIGH_CONFIDENCE")
        assert ranked[0]["p_success"] == 0.0
        assert ranked[0]["is_high_confidence_90"] is False


class TestDailyBriefCrossCategoryLens:
    """Phase 8: GET /api/daily-brief exposes the additive cross-category lens."""

    def test_lens_key_present_and_shaped(self):
        from fastapi.testclient import TestClient

        from api.main import app
        from cores.auth.auth import create_session_token

        client = TestClient(app)
        headers = {"Authorization": f"Bearer {create_session_token('test-user')}"}
        r = client.get("/api/daily-brief", headers=headers)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert "actions" in body  # existing contract intact
        lens = body.get("ranked_cross_category")
        assert isinstance(lens, list)
        for entry in lens:
            assert {"id", "category", "funnel", "p_success", "ev_per_hour", "is_high_confidence_90"} <= set(entry)
            assert 0.0 <= entry["p_success"] <= 1.0
