"""BarrierProfile tests — explicación factor-por-factor (Fase B)."""

from __future__ import annotations

from typing import Any

from cores.direct_work_engine.models import (
    Opportunity,
    OpportunityCategory,
    WorkPlatform,
)
from cores.direct_work_engine.scoring import barrier_profile


def _opp(**overrides: Any) -> Opportunity:
    base: dict[str, Any] = dict(
        id="b1",
        title="Task",
        platform=WorkPlatform.OPIRE,
        category=OpportunityCategory.DEV_BOUNTY,
        payment=250.0,
        remote=True,
        international_payment=True,
    )
    base.update(overrides)
    return Opportunity(**base)


class TestBarrierProfile:
    def test_clean_opportunity_is_zero_barrier_candidate(self) -> None:
        profile = barrier_profile(_opp())
        assert profile["is_zero_barrier_candidate"] is True
        assert profile["blocking"] == []
        assert profile["explanation"].startswith("Zero Barrier")

    def test_interview_surfaces_as_blocking_with_explanation(self) -> None:
        profile = barrier_profile(_opp(interview_required=True))
        assert "entrevista" in profile["blocking"]
        assert profile["is_zero_barrier_candidate"] is False
        assert "entrevista" in profile["explanation"]

    def test_geo_restriction_blocks(self) -> None:
        profile = barrier_profile(_opp(international_payment=False))
        assert profile["geo_restricted"] is True
        assert profile["is_zero_barrier_candidate"] is False

    def test_multiple_barriers_listed(self) -> None:
        profile = barrier_profile(_opp(interview_required=True, portfolio_required=True))
        assert set(profile["blocking"]) == {"entrevista", "portfolio"}
        assert "entrevista" in profile["explanation"]
        assert "portfolio" in profile["explanation"]

    def test_never_color_only_score_explains_itself(self) -> None:
        """Spec §7: la explicación existe independientemente del score."""
        profile = barrier_profile(_opp())
        assert len(profile["factors"]) >= 5
        assert isinstance(profile["explanation"], str) and profile["explanation"]
