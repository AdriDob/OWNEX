"""MAX_INCOME + Expected Human Value + filtros ZE/ZB-strict (spec §16 items 6-12)."""

from __future__ import annotations

from typing import Any

from cores.direct_work_engine.economics import (
    UNKNOWN_AVAILABILITY,
    TaskAvailability,
    compute_expected_human_value,
)
from cores.direct_work_engine.models import (
    EmploymentType,
    EntryMechanism,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    UserProfile,
    WorkPlatform,
)
from cores.direct_work_engine.recommendation import (
    MAX_INCOME_RECOMMENDER_CONFIG,
    IntelligentRecommender,
)


def _opp(**overrides: Any) -> Opportunity:
    params: dict[str, Any] = {
        "id": "t",
        "title": "T",
        "platform": WorkPlatform.OPIRE,
        "category": OpportunityCategory.DEV_BOUNTY,
        "employment_type": EmploymentType.BOUNTY,
    }
    params.update(overrides)
    return Opportunity(**params)


def _profile() -> UserProfile:
    return UserProfile(name="test")


class TestExpectedHumanValue:
    def test_hourly_stream_computes_per_human_hour(self) -> None:
        res = compute_expected_human_value(
            hourly_rate=25.0,
            human_hours=3.0,
            acceptance_probability=1.0,
            task_availability=TaskAvailability.of(1.0),
            payment_reliability=1.0,
            time_to_first_payment_days=7.0,
        )
        assert res.ev_per_human_hour_usd == 25.0
        assert res.cash_speed_days == 7.0
        assert res.availability_state == "known"

    def test_bounty_beats_by_ev_not_rate(self) -> None:
        """Spec item 8: hourly rate alone no rankea — $25/h×3h compite con $70."""
        stream = compute_expected_human_value(
            hourly_rate=25.0,
            human_hours=3.0,
            acceptance_probability=1.0,
            task_availability=TaskAvailability.of(1.0),
        )
        bounty = compute_expected_human_value(
            payment=70.0,
            human_hours=1.5,
            acceptance_probability=1.0,
            task_availability=TaskAvailability.of(1.0),
        )
        assert stream.ev_per_human_hour_usd is not None
        assert bounty.ev_per_human_hour_usd is not None
        assert stream.ev_per_human_hour_usd == 25.0
        assert bounty.ev_per_human_hour_usd > stream.ev_per_human_hour_usd

    def test_unknown_availability_never_becomes_probability(self) -> None:
        """Spec item 12: UNKNOWN nunca se convierte en probabilidad inventada."""
        res = compute_expected_human_value(
            payment=100.0,
            human_hours=2.0,
            acceptance_probability=1.0,
            task_availability=UNKNOWN_AVAILABILITY,
        )
        assert res.availability_state == "unknown"
        assert any("availability" in w for w in res.warnings)
        # EV parcial SIN el factor availability multiplicando.
        assert res.factors.get("task_availability") is None

    def test_unknown_hours_returns_none_not_invented(self) -> None:
        res = compute_expected_human_value(
            payment=100.0,
            human_hours=None,
            acceptance_probability=0.9,
        )
        assert res.ev_per_human_hour_usd is None
        assert any("human_hours" in w for w in res.warnings)

    def test_payout_delay_lowers_cash_speed(self) -> None:
        """Spec item 7: payout lento reduce cash-speed."""
        fast = compute_expected_human_value(
            payment=80.0, human_hours=1.0, acceptance_probability=1.0, time_to_first_payment_days=7.0
        )
        slow = compute_expected_human_value(
            payment=80.0, human_hours=1.0, acceptance_probability=1.0, time_to_first_payment_days=45.0
        )
        assert fast.cash_speed_days == 7.0
        assert slow.cash_speed_days == 45.0

    def test_qualification_time_reduces_roi(self) -> None:
        """Spec item 10: qualification time afecta ROI — horas humanas totales."""
        with_screening = compute_expected_human_value(
            payment=120.0,
            human_hours=4.0,
            acceptance_probability=1.0,
            task_availability=TaskAvailability.of(1.0),
        )  # incluye 1h assessment
        without_screening = compute_expected_human_value(
            payment=120.0,
            human_hours=2.0,
            acceptance_probability=1.0,
            task_availability=TaskAvailability.of(1.0),
        )
        assert with_screening.ev_per_human_hour_usd is not None
        assert without_screening.ev_per_human_hour_usd is not None
        assert without_screening.ev_per_human_hour_usd > with_screening.ev_per_human_hour_usd


class TestMaxIncomeMode:
    def test_config_sums_to_one(self) -> None:
        assert MAX_INCOME_RECOMMENDER_CONFIG.validate() is True

    def test_mode_does_not_leak(self) -> None:
        rec = IntelligentRecommender()
        base = rec.config.weight_expected_value
        opps = [_opp(id="a", payment=100), _opp(id="b", payment=50)]
        rec.recommend(opps, _profile(), mode="max_income")
        rec.recommend(opps, _profile())
        assert rec.config.weight_expected_value == base

    def test_zero_experience_only_keeps_assessment_drops_required(self) -> None:
        """Spec item 10: excluye REQUIRED pero NO assessment/training/onboarding."""
        rec = IntelligentRecommender()
        assessed = _opp(
            id="assessed",
            platform=WorkPlatform.OUTLIER,
            category=OpportunityCategory.AI_EVALUATION,
            entry_mechanism=EntryMechanism.ASSESSMENT,
            technical_test_required=True,
            registration_required=True,
            experience_required=ExperienceLevel.NONE,
        )
        senior = _opp(id="senior", experience_required=ExperienceLevel.SENIOR)
        kept = rec.recommend([assessed, senior], _profile(), zero_experience_only=True, limit=10)
        ids = {r.opportunity.id for r in kept}
        assert ids == {"assessed"}

    def test_zero_barrier_strict_excludes_assessment(self) -> None:
        """Spec item 11: modo estricto SÍ excluye assessment."""
        rec = IntelligentRecommender()
        assessed = _opp(id="assessed", entry_mechanism=EntryMechanism.ASSESSMENT, technical_test_required=True)
        direct = _opp(id="direct")
        kept = rec.recommend([assessed, direct], _profile(), zero_barrier_strict=True, limit=10)
        ids = {r.opportunity.id for r in kept}
        assert ids == {"direct"}


class TestEarningScores:
    def test_curated_profile_known_category(self) -> None:
        from cores.direct_work_engine.economics import EarningScores

        s = EarningScores.for_category("ai_evaluation")
        assert s.source == "curated"
        assert s.immediate == 60 and s.long_term == 80

    def test_unknown_category_neutral_never_invented(self) -> None:
        from cores.direct_work_engine.economics import EarningScores

        s = EarningScores.for_category("alien_category")
        assert (s.immediate, s.long_term) == (50, 50)
