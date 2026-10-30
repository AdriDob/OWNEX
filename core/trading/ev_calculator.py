"""Unified EV/Hour Calculator — Single source of truth for Expected Value per Human Hour.

Calculates EV/hour across all 3 income engines:
- Bug Bounty (cores.direct_work_engine)
- Dev Bounty (core.trading.engines.content_factory)
- Content Factory (MoneyPrinterTurbo)

Uses unified formulas with honest probability handling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from core.trading.contracts import (
    MarketData,
    Strategy,
)

logger = logging.getLogger("ownex.ev_calculator")


@dataclass
class EVHourInputs:
    """Inputs for EV/hour calculation."""

    reward_typical: Decimal
    acceptance_probability: Decimal
    duplicate_risk: Decimal
    disqualification_risk: Decimal
    estimated_hours: Decimal
    time_to_payment_days: int
    zero_barrier_score: Decimal
    skill_match: Decimal
    automation_level: str = "A0"
    payment_reliability: Decimal = Decimal("0.5")
    capital_velocity_factor: Decimal = Decimal("1.0")


@dataclass
class EVHourResult:
    """EV/hour calculation result."""

    ev_hour: Decimal
    expected_value: Decimal
    probability_success: Decimal
    expected_payout: Decimal
    estimated_hours: Decimal
    human_hours: Decimal
    machine_hours: Decimal
    automation_level: str
    time_to_payment_days: int
    capital_velocity_factor: Decimal
    risk_adjusted: Decimal
    breakdown: dict[str, Decimal] = field(default_factory=dict)


class UnifiedEVCalculator:
    """Unified EV/hour calculator for all income engines."""

    # Weights for EV/hour calculation factors
    WEIGHTS = {
        "barrier": Decimal("0.25"),
        "reward": Decimal("0.35"),
        "probability": Decimal("0.20"),
        "speed": Decimal("0.10"),
        "skill_match": Decimal("0.10"),
    }

    def __init__(self):
        self.logger = logging.getLogger("ownex.ev_calculator")

    def calculate_ev_hour(
        self,
        strategy: Strategy,
        market_data: MarketData,
        profile: dict | None = None,
    ) -> EVHourResult:
        """Calculate EV/hour for a strategy given user profile."""
        inputs = self._extract_inputs(strategy, market_data)
        skill_match = self._calculate_skill_match(strategy, profile)

        # Calculate detailed breakdown
        reward = inputs["reward_typical"]
        prob = inputs["acceptance_probability"] * (1 - inputs["duplicate_risk"]) * (1 - inputs["disqualification_risk"])
        hours = max(inputs["estimated_hours"], Decimal("0.5"))

        base_ev = reward * prob
        base_ev_hour = base_ev / hours if hours > 0 else Decimal("0")

        # Apply modifiers
        barrier_factor = Decimal("1.0") + (inputs["zero_barrier_score"] / Decimal("100")) * Decimal("0.5")
        reliability_factor = inputs["payment_reliability"]
        velocity_factor = inputs.get("capital_velocity_factor", Decimal("1.0"))
        skill_bonus = Decimal("0.8") + (Decimal(str(skill_match)) * Decimal("0.4"))

        final_ev_hour = base_ev_hour * barrier_factor * reliability_factor * velocity_factor
        final_ev_hour = final_ev_hour * skill_bonus

        return EVHourResult(
            ev_hour=max(Decimal("0"), final_ev_hour),
            expected_value=base_ev,
            probability_success=prob,
            expected_payout=reward * prob,
            estimated_hours=hours,
            human_hours=hours * (Decimal("1") - inputs.get("automation_level_value", Decimal("0"))),
            machine_hours=hours * inputs.get("automation_level_value", Decimal("0")),
            automation_level=inputs["automation_level"],
            time_to_payment_days=inputs["time_to_payment_days"],
            capital_velocity_factor=velocity_factor,
            risk_adjusted=final_ev_hour * reliability_factor,
            breakdown={
                "reward_typical": inputs["reward_typical"],
                "acceptance_probability": inputs["acceptance_probability"],
                "duplicate_risk": inputs["duplicate_risk"],
                "disqualification_risk": inputs["disqualification_risk"],
                "estimated_hours": hours,
                "zero_barrier_score": inputs["zero_barrier_score"],
                "payment_reliability": inputs["payment_reliability"],
                "barrier_factor": barrier_factor,
                "reliability_factor": reliability_factor,
                "velocity_factor": velocity_factor,
                "skill_bonus": skill_bonus,
            },
        )

    def _extract_inputs(self, strategy: Strategy, market_data: MarketData) -> dict:
        """Extract scoring inputs from strategy and market data."""
        return {
            "reward_typical": strategy.parameters.get("reward_typical", Decimal("0")),
            "acceptance_probability": strategy.parameters.get("acceptance_probability", Decimal("0.5")),
            "duplicate_risk": strategy.parameters.get("duplicate_risk", Decimal("0.3")),
            "disqualification_risk": strategy.parameters.get("disqualification_risk", Decimal("0.2")),
            "estimated_hours": max(Decimal(str(strategy.parameters.get("estimated_hours", "1"))), Decimal("0.5")),
            "time_to_payment_days": strategy.parameters.get("time_to_payment_days", 30),
            "zero_barrier_score": strategy.parameters.get("zero_barrier_score", Decimal("50")),
            "payment_reliability": strategy.parameters.get("payment_reliability", Decimal("0.5")),
            "capital_velocity_factor": Decimal("1.0"),
            "automation_level": strategy.parameters.get("automation_level", "A0"),
            "automation_level_value": Decimal(str(strategy.parameters.get("automation_level_value", "0"))),
        }

    def _calculate_skill_match(self, strategy: Strategy, profile: dict | None) -> float:
        """Calculate skill match between strategy and user profile."""
        # Placeholder - would be enhanced with actual profile data
        return 0.5

    def _calculate_ev_hour(self, inputs: dict, skill_match: float) -> Decimal:
        """Calculate EV/hour from inputs."""
        reward = inputs["reward_typical"]
        prob = (
            inputs["acceptance_probability"]
            * (Decimal("1") - inputs["duplicate_risk"])
            * (Decimal("1") - inputs["disqualification_risk"])
        )
        hours = max(inputs["estimated_hours"], Decimal("0.5"))

        base_ev = reward * prob

        barrier_factor = Decimal("1.0") + (inputs["zero_barrier_score"] / Decimal("100")) * Decimal("0.5")
        reliability_factor = inputs["payment_reliability"]
        velocity_factor = inputs.get("capital_velocity_factor", Decimal("1.0"))

        ev_hour = (base_ev / hours) * barrier_factor * reliability_factor * velocity_factor
        return max(Decimal("0"), ev_hour)


# ══════════════════════════════════════════════════════════════════════════════════════════════════════
# UNIFIED EV CALCULATOR FOR 3 ENGINES
# ════════════════════════════════════════════════════════════════════════════════════════════════════════


class UnifiedEVOrchestrator:
    """Unified EV orchestrator across all 3 income engines."""

    def __init__(self):
        self.calculator = UnifiedEVCalculator()
        self.logger = logging.getLogger("ownex.unified_ev")

    def calculate_all_engines(
        self,
        bug_bounty_strategies: list,
        dev_bounty_strategies: list,
        content_factory_strategies: list,
        market_data: MarketData,
        profile: dict | None = None,
    ) -> dict:
        """Calculate EV/hour for all strategies across all 3 engines."""

        all_results = []

        # Bug Bounty strategies
        for strategy in bug_bounty_strategies:
            result = self._calculate_engine_ev("bug_bounty", strategy, market_data, profile)
            if result:
                all_results.append(result)

        # Dev Bounty strategies
        for strategy in dev_bounty_strategies:
            result = self._calculate_engine_ev("dev_bounty", strategy, market_data, profile)
            if result:
                all_results.append(result)

        # Content Factory strategies
        for strategy in content_factory_strategies:
            result = self._calculate_engine_ev("content_factory", strategy, market_data, profile)
            if result:
                all_results.append(result)

        # Sort by EV/hour descending
        all_results.sort(key=lambda x: x["ev_hour"], reverse=True)

        return {
            "all_ranked": all_results,
            "by_engine": {
                "bug_bounty": [r for r in all_results if r["engine"] == "bug_bounty"],
                "dev_bounty": [r for r in all_results if r["engine"] == "dev_bounty"],
                "content_factory": [r for r in all_results if r["engine"] == "content_factory"],
            },
            "best_overall": all_results[0] if all_results else None,
        }

    def _calculate_engine_ev(self, engine: str, strategy, market_data, profile) -> dict | None:
        """Calculate EV for a single strategy in a specific engine."""
        try:
            # This would use the appropriate engine adapter
            # For now, return a mock calculation
            return {
                "strategy_id": strategy.get("strategy_id", "unknown"),
                "engine": engine,
                "ev_hour": Decimal("0"),
                "expected_value": Decimal("0"),
                "probability_success": Decimal("0.5"),
                "estimated_hours": Decimal("1"),
                "zero_barrier_score": Decimal("50"),
            }
        except Exception as e:
            logger.error(f"EV calculation failed for {engine}: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════

_unified_ev_calculator: UnifiedEVOrchestrator | None = None


def get_unified_ev_calculator() -> UnifiedEVOrchestrator:
    """Get the global unified EV calculator singleton."""
    global _unified_ev_calculator
    if _unified_ev_calculator is None:
        _unified_ev_calculator = UnifiedEVOrchestrator()
    return _unified_ev_calculator
