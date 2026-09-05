"""EV/Hour Scoring Engine - Zero-Barrier Income Engine.

Calculates Expected Value per Human Hour for public opportunities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cores.zero_barrier_engine.models import (
    PublicOpportunity,
    UserProfile,
)

logger = logging.getLogger(__name__)


@dataclass
class ScoringWeights:
    """Weights for EV/hour calculation factors."""

    barrier_weight: float = 0.25
    reward_weight: float = 0.35
    probability_weight: float = 0.20
    speed_weight: float = 0.10
    skill_match_weight: float = 0.10

    def __post_init__(self):
        total = (
            self.barrier_weight
            + self.reward_weight
            + self.probability_weight
            + self.speed_weight
            + self.skill_match_weight
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


DEFAULT_WEIGHTS = ScoringWeights()


@dataclass
class EVHourInputs:
    """Inputs for EV/hour calculation."""

    reward_typical: float
    acceptance_probability: float
    duplicate_risk: float
    disqualification_risk: float
    estimated_hours: float
    time_to_payment_days: int
    zero_barrier_score: float
    skill_match: float
    automation_level: str = "A0"
    payment_reliability: float = 0.5
    capital_velocity_factor: float = 1.0


class EVHourScorer:
    """Calculates Expected Value per Human Hour for opportunities."""

    def __init__(self, weights: ScoringWeights | None = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self.logger = logging.getLogger("ownex.zero_barrier.scoring")

    def calculate_ev_hour(self, opportunity: PublicOpportunity, profile: UserProfile | None = None) -> float:
        """Calculate EV/hour for an opportunity given user profile."""
        inputs = self._extract_inputs(opportunity)
        skill_match = self._calculate_skill_match(opportunity)

        ev_hour = self._calculate_ev_hour(inputs, skill_match)
        return ev_hour

    def _extract_inputs(self, opp: PublicOpportunity) -> dict:
        """Extract scoring inputs from opportunity."""
        return {
            "reward_typical": opp.reward_typical,
            "acceptance_probability": opp.acceptance_probability,
            "duplicate_risk": opp.duplicate_risk,
            "disqualification_risk": opp.disqualification_risk,
            "estimated_hours": max(opp.estimated_hours, 0.5),
            "time_to_payment_days": opp.time_to_first_payment_days,
            "zero_barrier_score": opp.zero_barrier_score,
            "payment_reliability": opp.payment_reliability,
            "capital_velocity_factor": 1.0,
        }

    def _calculate_skill_match(self, opportunity: PublicOpportunity) -> float:
        """Calculate skill match between opportunity and user profile."""
        # This would be enhanced with actual profile data
        return 0.5  # placeholder

    def _calculate_ev_hour(self, inputs: dict, skill_match: float) -> float:
        """Calculate EV/hour from inputs."""
        reward = inputs["reward_typical"]
        prob = inputs["acceptance_probability"] * (1 - inputs["duplicate_risk"]) * (1 - inputs["disqualification_risk"])
        hours = max(inputs["estimated_hours"], 0.5)

        # Base EV
        ev = reward * prob

        # Adjust for barrier (higher score = lower barrier = higher EV)
        barrier_factor = 1.0 + (inputs["zero_barrier_score"] / 100.0) * 0.5

        # Adjust for payment reliability
        reliability_factor = inputs["payment_reliability"]

        # Adjust for capital velocity
        velocity_factor = inputs.get("capital_velocity_factor", 1.0)

        # EV per hour
        ev_hour = (ev / hours) * barrier_factor * reliability_factor * velocity_factor

        return max(0.0, ev_hour)

    def score_opportunity(
        self,
        opportunity: PublicOpportunity,
        profile: UserProfile | None = None,
    ) -> dict:
        """Score an opportunity and return detailed breakdown."""

        inputs = self._extract_inputs(opportunity)
        skill_match = self._calculate_skill_match(opportunity)

        # Calculate base EV/hour
        reward = inputs["reward_typical"]
        prob = inputs["acceptance_probability"] * (1 - inputs["duplicate_risk"]) * (1 - inputs["disqualification_risk"])
        hours = max(inputs["estimated_hours"], 0.5)

        base_ev = reward * prob
        base_ev_hour = base_ev / hours if hours > 0 else 0.0

        # Apply modifiers
        barrier_factor = 1.0 + (opportunity.zero_barrier_score / 100.0) * 0.5
        reliability_factor = opportunity.payment_reliability

        ev_hour = base_ev_hour * barrier_factor * reliability_factor

        # Skill match bonus (0.8 to 1.2 based on match)
        skill_bonus = 0.8 + (skill_match * 0.4)

        final_ev_hour = ev_hour * skill_bonus

        return {
            "ev_hour": max(0.0, final_ev_hour),
            "base_ev_hour": base_ev_hour,
            "barrier_factor": barrier_factor,
            "reliability_factor": reliability_factor,
            "probability_success": prob,
            "expected_payout": reward * prob,
            "estimated_hours": hours,
            "breakdown": {
                "reward_typical": inputs["reward_typical"],
                "acceptance_probability": inputs["acceptance_probability"],
                "duplicate_risk": inputs["duplicate_risk"],
                "disqualification_risk": inputs["disqualification_risk"],
                "estimated_hours": hours,
                "zero_barrier_score": 0.0,
                "payment_reliability": inputs["payment_reliability"],
            },
        }

    def rank_opportunities(
        self,
        opportunities: list[PublicOpportunity],
        profile: UserProfile | None = None,
        top_n: int = 10,
    ) -> list[dict]:
        """Rank opportunities by EV/hour."""

        ranked = []
        for opp in opportunities:
            score = self.score_opportunity(opp, None)
            ranked.append(
                {
                    "opportunity_id": opp.id,
                    "title": opp.title,
                    "platform": opp.platform,
                    "category": opp.category,
                    "ev_hour": score["ev_hour"],
                    "expected_value": score["expected_value"],
                    "probability": score["probability_success"],
                    "estimated_hours": score["estimated_hours"],
                    "reward_typical": opp.reward_typical,
                }
            )

        # Sort by EV/hour descending
        ranked.sort(key=lambda x: x["ev_hour"], reverse=True)

        return ranked[:top_n]


def create_ev_hour_scorer(weights: dict | None = None) -> EVHourScorer:
    """Factory function to create EVHourScorer with custom weights."""
    if weights:
        custom_weights = ScoringWeights(**weights)
        return EVHourScorer(custom_weights)
    return EVHourScorer()
