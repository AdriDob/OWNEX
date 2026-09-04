"""One Best Action Recommendation Engine - Zero-Barrier Income Engine.

Implements the ONE BEST ACTION recommendation engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cores.zero_barrier_engine.models import (
    PublicOpportunity,
    RankedOpportunity,
    UserProfile,
)
from cores.zero_barrier_engine.scoring import EVHourScorer

logger = logging.getLogger(__name__)


@dataclass
class RecommendationContext:
    """Context for recommendation generation."""

    user_profile: UserProfile
    available_hours: float
    current_lane_allocation: dict[str, float]
    time_horizon: str = "daily"  # daily, weekly, monthly
    risk_tolerance: str = "medium"


@dataclass
class RecommendationResult:
    """Result of recommendation generation."""

    best_action: RankedOpportunity | None
    next_actions: list[RankedOpportunity]
    reasoning: str
    lane_allocation: dict[str, float]
    expected_ev_hour: float
    estimated_hours: float
    confidence: float


class OneBestActionEngine:
    """Generates the ONE BEST ACTION recommendation."""

    def __init__(self, scorer: EVHourScorer | None = None):
        self.scorer = scorer or EVHourScorer()
        self.logger = logging.getLogger("ownex.zero_barrier.recommendation")

    def generate_recommendation(
        self,
        opportunities: list[PublicOpportunity],
        profile: UserProfile,
        context: RecommendationContext | None = None,
    ) -> RecommendationResult:
        """Generate the ONE BEST ACTION recommendation."""

        if not opportunities:
            return RecommendationResult(
                best_action=None,
                next_actions=[],
                reasoning="No opportunities available",
                lane_allocation={},
                expected_ev_hour=0.0,
                estimated_hours=0.0,
                confidence=0.0,
            )

        # Rank opportunities by EV/hour
        ranked = self.scorer.rank_opportunities(
            opportunities,
            top_n=10,
        )

        if not ranked:
            return RecommendationResult(
                best_action=None,
                next_actions=[],
                reasoning="No rankable opportunities",
                lane_allocation={},
                expected_ev_hour=0.0,
                estimated_hours=0.0,
                confidence=0.0,
            )

        best = ranked[0]
        ranked[1:4]  # Next 3 options

        # Create RankedOpportunity objects with proper PublicOpportunity
        best_opp = best.get("opportunity")
        if best_opp is None:
            best_opp = PublicOpportunity()
        best_action = RankedOpportunity(
            opportunity=best_opp,
            rank=best.get("rank", 0),
            ev_hour=best.get("ev_hour", 0.0),
            expected_value=best.get("expected_value", 0.0),
            acceptance_probability=best.get("probability", 0.5),
        )

        next_actions_obj = []
        for i, opp in enumerate(ranked[1:4]):
            opp_obj = opp.get("opportunity")
            if opp_obj is None:
                opp_obj = PublicOpportunity()
            next_actions_obj.append(
                RankedOpportunity(
                    opportunity=opp_obj,
                    rank=opp.get("rank", i + 1),
                    ev_hour=opp.get("ev_hour", 0.0),
                    expected_value=opp.get("expected_value", 0.0),
                    acceptance_probability=opp.get("probability", 0.5),
                )
            )

        # Calculate lane allocation
        lane_allocation = self._calculate_lane_allocation(
            ranked,
            context.available_hours if context else 8.0,
        )

        reasoning = self._generate_reasoning(ranked[0], profile)

        return RecommendationResult(
            best_action=best_action,
            next_actions=next_actions_obj,
            reasoning=reasoning,
            lane_allocation=lane_allocation,
            expected_ev_hour=ranked[0].get("ev_hour", 0.0),
            estimated_hours=ranked[0].get("estimated_hours", 0.0),
            confidence=self._calculate_confidence(ranked[0]),
        )

    def _calculate_lane_allocation(
        self,
        ranked: list[dict],
        available_hours: float,
    ) -> dict[str, float]:
        """Calculate lane allocation based on ranked opportunities."""
        cashflow = 0.0
        high_ev = 0.0
        skill_compounding = 0.0

        for opp in ranked:
            category = opp.get("category", "")
            ev_hour = opp.get("ev_hour", 0.0)

            if "evaluation" in category.lower() or "annotation" in category.lower() or "qa" in category.lower():
                cashflow += ev_hour
            elif "bounty" in category.lower() or "security" in category.lower() or "web3" in category.lower():
                high_ev += ev_hour
            else:
                skill_compounding += ev_hour

        total = cashflow + high_ev + skill_compounding
        if total == 0:
            return {"cashflow": 0.33, "high_ev": 0.33, "skill_compounding": 0.34}

        return {
            "cashflow": cashflow / total,
            "high_ev": high_ev / total,
            "skill_compounding": skill_compounding / total,
        }

    def _generate_reasoning(self, best: dict, profile) -> str:
        """Generate reasoning for the recommendation."""
        title = best.get("title", "Unknown")
        platform = best.get("platform", "unknown")
        best.get("ev_hour", 0.0)
        best.get("reward_typical", 0)

        return (
            f"Highest EV/hour opportunity: {title} on {platform}. "
            f"Expected ${best.get('ev_hour', 0):.2f}/hr with ${best.get('reward_typical', 0):.0f} typical reward. "
            f"Estimated {best.get('estimated_hours', 0)}h effort. "
            f"Category: {best.get('category', 'unknown')}."
        )

    def _calculate_confidence(self, best: dict) -> float:
        """Calculate confidence in recommendation."""
        ev_hour = best.get("ev_hour", 0)
        prob = best.get("probability", 0.5)

        # Base confidence on EV/hour and probability
        if ev_hour > 50 and prob > 0.5:
            return 0.9
        elif ev_hour > 20 and prob > 0.3:
            return 0.7
        elif ev_hour > 10:
            return 0.5
        return 0.3


def create_recommendation_engine(scorer: EVHourScorer | None = None) -> OneBestActionEngine:
    """Factory function to create recommendation engine."""
    from cores.zero_barrier_engine.scoring import EVHourScorer

    scorer = scorer or EVHourScorer()
    return OneBestActionEngine(scorer)
