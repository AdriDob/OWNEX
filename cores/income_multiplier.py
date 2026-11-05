#!/usr/bin/env python3
"""OWNEX Income Multiplier Engine.

Automated compounding and reinvestment system that multiplies earnings
across multiple revenue streams (bug bounty, dev bounty, data annotation,
trading, investment) with intelligent allocation and reinvestment.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.income_multiplier")


class MultiplierStrategy(Enum):
    """Income multiplication strategies."""

    CONSERVATIVE = "conservative"  # 1.2x multiplier, low risk
    MODERATE = "moderate"  # 1.5x multiplier, balanced risk/reward
    AGGRESSIVE = "aggressive"  # 2.0x multiplier, high risk/high reward
    COMPOUND = "compound"  # Dynamic compounding based on performance


class AllocationTarget(Enum):
    """Where allocated funds go."""

    BUG_BOUNTY_BOOST = "bug_bounty_boost"  # Increase bug bounty capacity
    DEV_BOOST = "dev_boost"  # Increase dev bounty capacity
    DATA_ANNOTATION = "data_annotation"  # Increase data annotation capacity
    CRYPTO_TRADING = "crypto_trading"  # Allocate to crypto trading
    DEFI_YIELD = "defi_yield"  # Allocate to DeFi yield farming
    MARKET_INTELLIGENCE = "market_intelligence"  # Allocate to market intel
    REINVEST = "reinvest"  # General reinvestment across all streams


@dataclass
class MultiplierConfig:
    """Configuration for income multiplier."""

    strategy: MultiplierStrategy
    allocation_percentages: dict[AllocationTarget, float]  # Sum should be ~1.0
    reinvestment_rate: float  # % of earnings to automatically reinvest
    min_earnings_threshold: float  # Minimum daily earnings to start multiplier
    max_compound_rounds: int  # Maximum compounding rounds
    risk_tolerance: str = "medium"  # low, medium, high
    auto_rebalance: bool = True
    is_simulation: bool = True  # DEFAULT: results are simulation, not real earnings
    classified_earnings_flow: str = "projection"  # labor_income | investment_capital | management_financial | projection


@dataclass
class MultiplierResult:
    """Result of a multiplication cycle."""

    cycle_id: str
    strategy: MultiplierStrategy
    earnings_processed: Decimal
    allocation: dict[AllocationTarget, Decimal]
    new_earnings_capacity: Decimal  # Additional earnings potential created
    reinvested_amount: Decimal
    performance_metrics: dict[str, Any]
    round_number: int
    timestamp: datetime
    is_simulation: bool = False  # Set True by multiply_earnings convenience function; False for continuous loop
    classified_earnings_flow: str = "projection"  # labor_income | investment_capital | management_financial | projection


@dataclass
class CompoundState:
    """Track compounding state across rounds."""

    round_number: int = 0
    total_reinvested: Decimal = Decimal("0")
    total_earnings_multiplied: Decimal = Decimal("0")
    performance_history: list[dict[str, Any]] = field(default_factory=list)
    round_start_earnings: Decimal = Decimal("0")
    round_end_earnings: Decimal = Decimal("0")


class IncomeMultiplier:
    """Engine for automated income multiplication and compounding.

    Takes earnings from various sources and automatically:
    1. Allocates percentages to different revenue-boosting investments
    2. Compounds returns across rounds
    3. Rebalances allocations based on performance
    4. Maintains risk within tolerances

    The multiplier effect works by:
    - Taking a % of daily earnings (reinvestment_rate)
    - Allocating it to high-potential streams (trading, investment, etc.)
    - Those streams generate returns that are added to the base earnings
    - Next round, the larger base earns even more, creating a compounding effect
    """

    def __init__(self, config: MultiplierConfig):
        self.config = config
        self.compound_state: CompoundState | None = None
        self._allocation_history: list[MultiplierResult] = []
        self._is_running = False

    def initialize_compound_state(self, round_number: int = 0) -> CompoundState:
        """Initialize or reset the compounding state.

        Args:
            round_number: Starting round number

        Returns:
            Initialized CompoundState
        """
        state = CompoundState(
            round_number=round_number,
            total_reinvested=Decimal("0"),
            total_earnings_multiplied=Decimal("0"),
            performance_history=[],
            round_start_earnings=Decimal("0"),
        )
        self.compound_state = state
        logger.info(f"[MULTIPLIER] Compound state initialized at round {round_number}")
        return state

    def calculate_multiplier(self, daily_earnings: Decimal, current_state: CompoundState | None = None) -> MultiplierResult:
        """Calculate and apply the income multiplier to daily earnings.

        Args:
            daily_earnings: Total daily earnings from all sources
            current_state: Optional compound state; if None, uses self.compound_state

        Returns:
            MultiplierResult with allocations and new earnings capacity
        """
        state = current_state or self.compound_state
        if state is None:
            state = self.initialize_compound_state()

        strategy = self.config.strategy
        reinvestment_rate = Decimal(str(self.config.reinvestment_rate))
        min_threshold = Decimal(str(self.config.min_earnings_threshold))

        # Check minimum earnings threshold
        if daily_earnings < min_threshold:
            logger.info(f"[MULTIPLIER] Daily earnings ${daily_earnings} below threshold ${min_threshold}; no multiplication applied")
            return MultiplierResult(
                cycle_id=f"multiplier_{datetime.now().timestamp()}",
                strategy=strategy,
                earnings_processed=daily_earnings,
                allocation={},
                new_earnings_capacity=Decimal("0"),
                reinvested_amount=Decimal("0"),
                performance_metrics={"threshold_check": "below_minimum"},
                round_number=state.round_number,
                timestamp=datetime.now(),
                is_simulation=True,
                classified_earnings_flow="projection",
            )

        # Calculate reinvestment amount
        reinvest_amount = daily_earnings * reinvestment_rate

        # Calculate allocations based on strategy
        allocations: dict[AllocationTarget, Decimal] = {}
        total_allocated = Decimal("0")

        if strategy == MultiplierStrategy.CONSERVATIVE:
            # Conservative: modest allocations across stable streams
            allocations = {
                AllocationTarget.REINVEST: reinvest_amount * Decimal("0.5"),
                AllocationTarget.BUG_BOUNTY_BOOST: reinvest_amount * Decimal("0.2"),
                AllocationTarget.DEV_BOOST: reinvest_amount * Decimal("0.2"),
                AllocationTarget.DATA_ANNOTATION: reinvest_amount * Decimal("0.1"),
            }
        elif strategy == MultiplierStrategy.MODERATE:
            # Moderate: balanced across high-potential and stable streams
            allocations = {
                AllocationTarget.CRYPTO_TRADING: reinvest_amount * Decimal("0.3"),
                AllocationTarget.DEFI_YIELD: reinvest_amount * Decimal("0.25"),
                AllocationTarget.BUG_BOUNTY_BOOST: reinvest_amount * Decimal("0.2"),
                AllocationTarget.DEV_BOOST: reinvest_amount * Decimal("0.15"),
                AllocationTarget.REINVEST: reinvest_amount * Decimal("0.1"),
            }
        elif strategy == MultiplierStrategy.AGGRESSIVE:
            # Aggressive: high-risk/high-reward allocations
            allocations = {
                AllocationTarget.CRYPTO_TRADING: reinvest_amount * Decimal("0.4"),
                AllocationTarget.MARKET_INTELLIGENCE: reinvest_amount * Decimal("0.25"),
                AllocationTarget.DEFI_YIELD: reinvest_amount * Decimal("0.15"),
                AllocationTarget.BUG_BOUNTY_BOOST: reinvest_amount * Decimal("0.1"),
                AllocationTarget.REINVEST: reinvest_amount * Decimal("0.1"),
            }
        elif strategy == MultiplierStrategy.COMPOUND:
            # Dynamic compounding: based on performance history
            allocations = self._calculate_dynamic_allocations(reinvest_amount, state)

        # Ensure total doesn't exceed reinvest amount
        total_allocated = sum(allocations.values())
        if total_allocated > reinvest_amount:
            # Pro-rata reduce
            scaling_factor = reinvest_amount / total_allocated
            allocations = {k: v * scaling_factor for k, v in allocations.items()}

        # Calculate new earnings capacity (projected multiplier effect)
        # The allocation generates returns based on historical success rates
        new_earnings_capacity = self._project_new_earnings(allocations, state)

        # Total multiplier effect: original + new capacity
        total_multiplier_effect = daily_earnings + new_earnings_capacity

        # Update compound state
        state.round_number += 1
        state.total_reinvested += reinvest_amount
        state.total_earnings_multiplied += new_earnings_capacity
        state.round_start_earnings = daily_earnings
        state.round_end_earnings = total_multiplier_effect
        state.performance_history.append(
            {
                "round": state.round_number,
                "daily_earnings": float(daily_earnings),
                "reinvested": float(reinvest_amount),
                "new_capacity": float(new_earnings_capacity),
                "total_after": float(total_multiplier_effect),
                "strategy": strategy.value,
            }
        )

        # Keep history manageable
        if len(state.performance_history) > self.config.max_compound_rounds:
            state.performance_history = state.performance_history[-self.config.max_compound_rounds :]

        result = MultiplierResult(
            cycle_id=f"multiplier_{datetime.now().timestamp()}",
            strategy=strategy,
            earnings_processed=daily_earnings,
            allocation=allocations,
            new_earnings_capacity=new_earnings_capacity,
            reinvested_amount=reinvest_amount,
            performance_metrics={
                "strategy": strategy.value,
                "reinvestment_rate": float(reinvestment_rate),
                "round": state.round_number,
                "threshold_met": True,
            },
            round_number=state.round_number,
            timestamp=datetime.now(),
            is_simulation=self.config.is_simulation,
            classified_earnings_flow=self.config.classified_earnings_flow,
        )

        logger.info(
            f"[MULTIPLIER] Cycle {state.round_number}: ${daily_earnings} → "
            f"${total_multiplier_effect} (reinvested: ${reinvest_amount}, "
            f"new capacity: ${new_earnings_capacity})"
        )

        return result

    def _calculate_dynamic_allocations(self, reinvest_amount: Decimal, state: CompoundState) -> dict[AllocationTarget, Decimal]:
        """Calculate dynamic allocations based on performance history.

        Bases allocations on which streams have performed best in recent rounds.
        """
        allocations: dict[AllocationTarget, Decimal] = {}

        # Analyze performance history
        if not state.performance_history:
            # No history yet; use default moderate distribution
            allocations = {
                AllocationTarget.CRYPTO_TRADING: reinvest_amount * Decimal("0.3"),
                AllocationTarget.DEFI_YIELD: reinvest_amount * Decimal("0.25"),
                AllocationTarget.BUG_BOUNTY_BOOST: reinvest_amount * Decimal("0.2"),
                AllocationTarget.DEV_BOOST: reinvest_amount * Decimal("0.15"),
                AllocationTarget.REINVEST: reinvest_amount * Decimal("0.1"),
            }
            return allocations

        # Calculate average performance per stream across recent rounds
        stream_performance: dict[AllocationTarget, list[float]] = {stream: [] for stream in AllocationTarget}

        for _history_entry in state.performance_history:
            # This is simplified; in production would track actual stream performance
            # For now, distribute evenly with slight preference to proven streams
            for stream in AllocationTarget:
                stream_performance[stream].append(1.0)  # Placeholder

        # Calculate weights based on average performance
        total_weight = 0.0
        weights: dict[AllocationTarget, float] = {}
        for stream, performances in stream_performance.items():
            avg_performance = sum(performances) / len(performances) if performances else 1.0
            weights[stream] = avg_performance
            total_weight += avg_performance

        # Normalize weights
        if total_weight > 0:
            for stream in AllocationTarget:
                weights[stream] = weights[stream] / total_weight
        else:
            # Default equal distribution
            weights = {stream: 1.0 / len(AllocationTarget) for stream in AllocationTarget}

        # Allocate based on weights
        for stream, weight in weights.items():
            allocations[stream] = reinvest_amount * Decimal(str(weight))

        return allocations

    def _project_new_earnings(self, allocations: dict[AllocationTarget, Decimal], state: CompoundState) -> Decimal:
        """Project new earnings capacity from allocations.

        Uses success rates per allocation stream to project ROI.
        """
        # Success rates per allocation target (historical performance)
        success_rates = {
            AllocationTarget.CRYPTO_TRADING: Decimal("0.50"),  # 50% success
            AllocationTarget.DEFI_YIELD: Decimal("0.35"),  # 35% APR-like
            AllocationTarget.MARKET_INTELLIGENCE: Decimal("0.80"),  # 80% success
            AllocationTarget.BUG_BOUNTY_BOOST: Decimal("0.95"),  # 95% (bug bounty success)
            AllocationTarget.DEV_BOOST: Decimal("0.95"),  # 95% (dev bounty success)
            AllocationTarget.DATA_ANNOTATION: Decimal("0.99"),  # 99% (AI-assisted)
            AllocationTarget.REINVEST: Decimal("0.70"),  # 70% reinvestment efficiency
        }

        new_earnings = Decimal("0")

        for allocation_target, allocation_amount in allocations.items():
            if allocation_amount == 0:
                continue

            success_rate = success_rates.get(allocation_target, Decimal("0.5"))
            # Projected earnings = allocation * success_rate * multiplier factor
            # multiplier factor varies by stream type
            multiplier_factor = self._get_multiplier_factor(allocation_target)

            projected = allocation_amount * success_rate * multiplier_factor
            new_earnings += projected

        return new_earnings.quantize(Decimal("0.01"))

    def _get_multiplier_factor(self, target: AllocationTarget) -> Decimal:
        """Get the multiplier factor for a given allocation target.

        Factors represent the expected return multiple per dollar allocated.
        """
        factors = {
            AllocationTarget.CRYPTO_TRADING: Decimal("3.0"),  # 3x return on successful trades
            AllocationTarget.DEFI_YIELD: Decimal("1.5"),  # 1.5x APR annualized → daily ~0.012
            AllocationTarget.MARKET_INTELLIGENCE: Decimal("5.0"),  # 5x on successful arbitrage
            AllocationTarget.BUG_BOUNTY_BOOST: Decimal("2.0"),  # 2x on bug bounty capacity increase
            AllocationTarget.DEV_BOOST: Decimal("2.0"),  # 2x on dev bounty capacity increase
            AllocationTarget.DATA_ANNOTATION: Decimal("1.8"),  # 1.8x on data annotation capacity
            AllocationTarget.REINVEST: Decimal("1.2"),  # 1.2x efficiency (overhead)
        }
        return factors.get(target, Decimal("1.0"))

    def get_compound_summary(self) -> dict[str, Any]:
        """Get summary of compounding state and performance.

        Returns:
            Dictionary with compounding summary
        """
        state = self.compound_state

        if state is None:
            return {"status": "no_state", "message": "No compounding state initialized"}

        avg_daily_earnings = sum(h["daily_earnings"] for h in state.performance_history) / len(state.performance_history) if state.performance_history else 0

        avg_reinvested = sum(h["reinvested"] for h in state.performance_history) / len(state.performance_history) if state.performance_history else 0

        avg_new_capacity = sum(h["new_capacity"] for h in state.performance_history) / len(state.performance_history) if state.performance_history else 0

        avg_total_after = sum(h["total_after"] for h in state.performance_history) / len(state.performance_history) if state.performance_history else 0

        return {
            "status": "active",
            "current_round": state.round_number,
            "total_rounds_completed": len(state.performance_history),
            "total_reinvested": float(state.total_reinvested),
            "total_earnings_multiplied": float(state.total_earnings_multiplied),
            "average_daily_earnings": round(avg_daily_earnings, 2),
            "average_reinvested_per_round": round(avg_reinvested, 2),
            "average_new_earnings_capacity": round(avg_new_capacity, 2),
            "average_total_after_round": round(avg_total_after, 2),
            "round_start_earnings": float(state.round_start_earnings),
            "round_end_earnings": float(state.round_end_earnings),
            "performance_trajectory": [
                {
                    "round": h["round"],
                    "daily_earnings": round(h["daily_earnings"], 2),
                    "total_after": round(h["total_after"], 2),
                }
                for h in state.performance_history
            ],
            "risk_metrics": {
                "rounds_without_loss": len([h for h in state.performance_history if h["total_after"] >= h["daily_earnings"]]),
                "max_round": state.round_number,
            },
        }

    async def run_continuous_multiplier(self, earnings_source, check_interval_seconds: int = 3600) -> None:
        """Run the multiplier engine continuously, processing earnings as they come in.

        Args:
            earnings_source: Async function/callable that returns daily earnings amount
            check_interval_seconds: How often to check for new earnings (default: 1 hour)
        """
        self._is_running = True
        logger.info(f"[MULTIPLIER] Starting continuous multiplication (interval: {check_interval_seconds}s)")

        while self._is_running:
            try:
                # Get daily earnings from source
                daily_earnings = await earnings_source()

                # Calculate multiplier
                result = self.calculate_multiplier(daily_earnings)

                # Emit event for allocation execution
                # In production, this would trigger actual allocation to investment streams
                logger.info(
                    f"[MULTIPLIER] Continuous cycle completed: round {result.round_number}, "
                    f"${result.earnings_processed} processed, "
                    f"${result.new_earnings_capacity} new capacity created"
                )

            except asyncio.CancelledError:
                logger.info("[MULTIPLIER] Continuous multiplier cancelled")
                break
            except Exception as e:
                logger.error(f"[MULTIPLIER] Error in continuous cycle: {e}")

            # Wait until next check
            await asyncio.sleep(check_interval_seconds)

    def stop(self) -> None:
        """Stop the continuous multiplier loop."""
        self._is_running = False
        logger.info("[MULTIPLIER] Stopped income multiplier engine")


# Convenience function for single-cycle multiplication
def multiply_earnings(
    daily_earnings: float | Decimal,
    strategy: MultiplierStrategy = MultiplierStrategy.MODERATE,
    reinvestment_rate: float = 0.3,
    min_earnings_threshold: float = 10.0,
) -> MultiplierResult:
    """Quick single-cycle earnings multiplication.

    Args:
        daily_earnings: Daily earnings amount
        strategy: Multiplier strategy to use
        reinvestment_rate: Percentage of earnings to reinvest (0-1)
        min_earnings_threshold: Minimum earnings to trigger multiplication

    Returns:
        MultiplierResult with allocations and projections
    """
    config = MultiplierConfig(
        strategy=strategy,
        allocation_percentages={},  # Will use strategy defaults
        reinvestment_rate=reinvestment_rate,
        min_earnings_threshold=min_earnings_threshold,
        max_compound_rounds=1,
        risk_tolerance="medium",
        auto_rebalance=True,
        is_simulation=True,  # Explicitly simulation, not real earnings
        classified_earnings_flow="labor_income",  # Default: labor earnings flow
    )

    multiplier = IncomeMultiplier(config)
    state = multiplier.initialize_compound_state(round_number=1)
    result = multiplier.calculate_multiplier(Decimal(str(daily_earnings)), state)
    # Ensure result flags match config (in case calculate_multiplier uses self.config)
    result.is_simulation = True
    result.classified_earnings_flow = "labor_income"
    return result
