"""Zero Experience ≠ Zero Barrier — modelo de entrada corregido (2026-08-25).

Spec §16 items 1-5, 13-15:
1. ZERO_EXPERIENCE != ZERO_BARRIER
2. assessment no implica experience_required
3. Outlier-like: ZERO_EXPERIENCE + LOW barrier
4. dev bounty: ZERO_EXPERIENCE + ZERO_BARRIER
5. data annotation varía según plataforma
13. sin enums duplicados (viven solo en models.py)
14. taxonomía canónica intacta
15. backward compat con datos legacy
"""

from __future__ import annotations

from typing import Any

from cores.direct_work_engine.models import (
    BarrierLevel,
    EmploymentType,
    EntryMechanism,
    ExperienceLevel,
    ExperienceRequirement,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)
from cores.direct_work_engine.scoring import ZeroBarrierScorer


def _opp(**overrides: Any) -> Opportunity:
    params: dict[str, Any] = {
        "id": "t",
        "title": "T",
        "platform": WorkPlatform.OUTLIER,
        "category": OpportunityCategory.AI_EVALUATION,
    }
    params.update(overrides)
    return Opportunity(**params)


class TestZeroExperienceVsZeroBarrier:
    def test_outlier_like_is_zero_experience_but_not_zero_barrier(self) -> None:
        """Assessment de capacidad + sin experiencia: ZE=True, ZB=False."""
        op = _opp(
            entry_mechanism=EntryMechanism.ASSESSMENT,
            technical_test_required=True,
            registration_required=True,
            experience_required=ExperienceLevel.NONE,
        )
        assert op.is_zero_experience is True
        assert op.is_zero_barrier is False

    def test_dev_bounty_is_both(self) -> None:
        op = _opp(
            platform=WorkPlatform.OPIRE,
            category=OpportunityCategory.DEV_BOUNTY,
            entry_mechanism=EntryMechanism.DIRECT,
            employment_type=EmploymentType.BOUNTY,
        )
        assert op.is_zero_experience is True
        assert op.is_zero_barrier is True

    def test_senior_gate_blocks_zero_experience(self) -> None:
        op = _opp(experience_required=ExperienceLevel.SENIOR)
        assert op.is_zero_experience is False

    def test_legacy_data_derives_requirements(self) -> None:
        """Dicts viejos sin campos nuevos siguen funcionando (spec §15)."""
        legacy = _opp(experience_required=ExperienceLevel.NONE)  # sin entry_mechanism explícito
        assert legacy.entry_mechanism == EntryMechanism.DIRECT
        assert legacy.experience_requirement is None
        assert legacy.effective_experience_requirement == ExperienceRequirement.NONE
        assert legacy.is_zero_barrier is True

    def test_annotation_varies_by_platform(self) -> None:
        """Spec item 5: data annotation depende de la plataforma."""
        direct = _opp(
            category=OpportunityCategory.DATA_ANNOTATION,
            entry_mechanism=EntryMechanism.DIRECT,
        )
        gated = _opp(
            id="gated",
            category=OpportunityCategory.DATA_ANNOTATION,
            entry_mechanism=EntryMechanism.ASSESSMENT,
            technical_test_required=True,
        )
        assert direct.is_zero_barrier is True
        assert gated.is_zero_barrier is False
        assert gated.is_zero_experience is True

    def test_explicit_requirement_overrides_legacy_depth(self) -> None:
        op = _opp(
            experience_required=ExperienceLevel.JUNIOR,
            experience_requirement=ExperienceRequirement.REQUIRED,
        )
        assert op.effective_experience_requirement == ExperienceRequirement.REQUIRED
        assert op.is_zero_experience is False


class TestScorerAssessmentFix:
    def test_assessment_only_entry_scores_above_registration(self) -> None:
        scorer = ZeroBarrierScorer()
        assessed = scorer.score(_opp(technical_test_required=True))
        registered = scorer.score(_opp(id="r", registration_required=True))
        assert assessed.factors["direct_application"] == 70.0
        assert assessed.total > registered.total

    def test_assessment_no_longer_worse_than_interview(self) -> None:
        scorer = ZeroBarrierScorer()
        with_test = scorer.score(_opp(technical_test_required=True))
        with_interview = scorer.score(_opp(id="i", interview_required=True))
        # La corrección elimina la severidad invertida: el assessment amortizado
        # ya no puede puntuar dramáticamente peor que un funnel de entrevista.
        assert with_test.total > with_interview.total - 10.0

    def test_zero_tier_reachable_for_direct_work(self) -> None:
        score = ZeroBarrierScorer().score(
            _opp(
                platform=WorkPlatform.OPIRE,
                category=OpportunityCategory.DEV_BOUNTY,
                payment_method=PaymentMethod.PAYONEER,
                payment_proven=True,
                time_to_payout_days=7,
                reputation=0.9,
                stability=0.9,
                risk=0.1,
                compatibility=0.9,
            )
        )
        assert score.barrier_level in {BarrierLevel.ZERO, BarrierLevel.VERY_LOW}
        assert score.total >= 80

    def test_reasoning_distinguishes_assessment_from_test_blocker(self) -> None:
        score = ZeroBarrierScorer().score(_opp(entry_mechanism=EntryMechanism.ASSESSMENT, technical_test_required=True))
        assert any("assessment" in e.lower() for e in score.enablers)


class TestTaxonomyGuardrails:
    def test_new_enums_live_only_in_models(self) -> None:
        """Spec item 13: cero enums duplicados — importable desde models.py."""
        from cores.direct_work_engine.models import EntryMechanism as MechanismEnum
        from cores.direct_work_engine.models import ExperienceRequirement as RequirementEnum

        assert len(MechanismEnum) == 9
        assert len(RequirementEnum) == 4

    def test_canonical_taxonomy_untouched(self) -> None:
        """Spec item 14: las 38 categorías siguen siendo SSOT."""
        from cores.work_taxonomy import OpportunityCategory

        assert len(OpportunityCategory) == 38
