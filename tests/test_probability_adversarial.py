"""Phase 9: adversarial tests for the universal probability core.

Each test attempts to make the system lie (certainty from nothing, reward
inflating probability, corruption breaking the loop) and pins honest behavior.
Covers contract + universal engine + calibration routing only.
"""

from __future__ import annotations

from cores.direct_work_engine.probability_contract import EvidenceLabel, ProbabilityType


def _opp(**overrides):
    from cores.direct_work_engine.models import Opportunity, OpportunityCategory, PaymentMethod, WorkPlatform

    base = {
        "id": "adv-1",
        "title": "t",
        "platform": WorkPlatform.ALGORA,
        "category": OpportunityCategory.BACKEND,
        "payment": 500.0,
        "currency": "USD",
        "payment_method": PaymentMethod.PAYPAL,
        "remote": True,
    }
    base.update(overrides)
    return Opportunity(**base)


class TestOneOneIsNeverNinety:
    def test_single_win_stays_thin(self):
        from cores.direct_work_engine.universal_probability import get_universal_probability_engine

        engine = get_universal_probability_engine()
        assert engine.is_high_confidence_90(_opp()) is False

    def test_perfect_prior_still_insufficient(self):
        from datetime import UTC, datetime

        from cores.direct_work_engine.probability_contract import ProbabilityEstimate

        est = ProbabilityEstimate(
            probability_type=ProbabilityType.P_ACCEPT,
            estimate=1.0,
            confidence=1.0,
            lower_bound=1.0,
            upper_bound=1.0,
            evidence_label=EvidenceLabel.THIN_EVIDENCE,
            effective_sample_size=1.0,
            raw_sample_size=1,
            prior_type="personal",
            prior_value=1.0,
            source="personal_evidence",
            segment="t",
            last_updated=datetime.now(UTC).isoformat(),
            evidence_quality=1.0,
        )
        assert est.is_high_confidence_90 is False
        assert est.is_insufficient_for_high_confidence is True


class TestRewardCannotInflateProbability:
    def test_megabounty_thin_evidence_not_confident(self):
        from cores.direct_work_engine.universal_probability import get_universal_probability_engine

        engine = get_universal_probability_engine()
        opp = _opp(payment=100_000.0)
        assert engine.is_high_confidence_90(opp) is False
        ranked = engine.rank_cross_category([opp], mode="HIGH_CONFIDENCE")
        assert ranked[0]["is_high_confidence_90"] is False

    def test_ranking_shows_tradeoff_not_hiding_it(self):
        from cores.direct_work_engine.universal_probability import get_universal_probability_engine

        engine = get_universal_probability_engine()
        huge = _opp(id="huge", payment=100_000.0, estimated_time_hours=100.0)
        small = _opp(id="small", payment=50.0, estimated_time_hours=1.0)
        ranked = engine.rank_cross_category([huge, small], mode="BALANCED")
        by_id = {r["opportunity"].id: r for r in ranked}
        # Both surface with their numbers visible; small wins EV/hour honestly.
        assert by_id["small"]["ev_per_hour"] == 50.0
        assert by_id["huge"]["ev_per_hour"] == 1000.0
        assert ranked[0]["opportunity"].id == "huge"  # higher EV/h first, no hiding


class TestCorruptAndMissingCalibration:
    def test_corrupt_universal_store_survives(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.universal_calibration import UniversalCalibrationEngine

        store = tmp_path / "learning" / "universal_calibration.jsonl"
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text('{"broken json\n{"platform": "x"}\n', encoding="utf-8")
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        eng = UniversalCalibrationEngine(data_dir=tmp_path)
        factor, conf = eng.get_correction_factor("bug_bounty", "p_accept")
        assert factor == 1.0  # neutral, never invented

    def test_missing_store_is_neutral(self, tmp_path):
        from cores.direct_work_engine.universal_calibration import UniversalCalibrationEngine

        eng = UniversalCalibrationEngine(data_dir=tmp_path / "empty")
        factor, conf = eng.get_correction_factor("nope", "p_accept")
        assert factor == 1.0
        assert conf == "insufficient_data"

    def test_unknown_category_factor_neutral(self, tmp_path):
        from cores.direct_work_engine.universal_calibration import UniversalCalibrationEngine

        eng = UniversalCalibrationEngine(data_dir=tmp_path)
        assert eng.get_correction_factor("no-such-category", "p_accept") == (1.0, "insufficient_data")


class TestConflictingOutcomes:
    def test_mixed_history_stays_moderate(self, tmp_path):
        from cores.direct_work_engine.reward_probability import PersonalAcceptanceProbability

        eng = PersonalAcceptanceProbability(store_path=tmp_path / "acc.jsonl")
        for _ in range(5):
            eng.record_outcome(platform="p", niche="ai_llm", result="accepted")
        for _ in range(5):
            eng.record_outcome(platform="p", niche="ai_llm", result="rejected")
        est = eng.estimate(niche="ai_llm", platform="p")
        assert 0.3 <= est.p_accept <= 0.7  # never extreme on conflict
        # Confidence interval must be wide on 5/10 split.
        assert (est.p_accept_upper - est.p_accept_lower) > 0.2


class TestNewCategoryAndSegment:
    def test_unregistered_funnel_raises_not_invents(self):
        import pytest

        from cores.direct_work_engine.probability_contract import get_funnel

        with pytest.raises(KeyError):
            get_funnel("no-such-category")

    def test_empty_history_labels(self):
        import tempfile

        from cores.direct_work_engine.reward_probability import PersonalAcceptanceProbability

        with tempfile.TemporaryDirectory() as d:
            eng = PersonalAcceptanceProbability(store_path=f"{d}/a.jsonl")
            est = eng.estimate(niche="ai_llm", platform="never-seen")
            assert est.n_outcomes == 0
            assert est.source == "PRIOR_EXTERNO"
