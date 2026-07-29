"""Strategy Engine — decides what to work on RIGHT NOW.

Not planning. DECIDING.
Strategy evaluates opportunities and produces a priority-ranked queue.
Each strategy scores independently; the weighted sum produces final priority.
"""
from __future__ import annotations

import contextlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.engine.base import Engine
from core.engine.classification import Opportunity

logger = logging.getLogger("ownex.strategy")


# ── Core types ─────────────────────────────────────────────────────


@dataclass
class PrioritizedOpportunity:
    """An opportunity with a strategy decision attached."""

    opportunity: Opportunity
    priority: float           # 0.0 to 1.0
    reason: str               # why this priority?
    estimated_ev: float       # expected value after strategy
    estimated_time: float     # estimated hours
    due_by: datetime | None = None
    strategy_applied: str = ""


@dataclass
class WorkContext:
    """Current work context for strategy decisions."""

    opportunities: list[Opportunity]
    available_time_hours: float = 8.0
    current_cycle: str | None = None
    energy_level: str = "normal"           # "low", "normal", "high"
    financial_goal_month: float = 10000.0
    financial_goal_week: float = 2500.0
    earned_this_month: float = 0.0
    earned_this_week: float = 0.0
    last_strategy: str = "balanced"
    user_preferences: dict[str, float] = field(default_factory=dict)

    def get_cycle_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for o in self.opportunities:
            counts[o.cycle] = counts.get(o.cycle, 0) + 1
        return counts

    def get_cycle_ev(self) -> dict[str, float]:
        evs: dict[str, float] = {}
        for o in self.opportunities:
            ev = o.estimated_reward_max * o.confidence
            evs[o.cycle] = evs.get(o.cycle, 0) + ev
        return evs


# ── Strategy interface ─────────────────────────────────────────────


class Strategy(ABC):
    """A strategy decides what to work on.

    Each strategy has a weight. The overall score is weighted sum.
    """

    name: str = ""
    weight: float = 1.0

    @abstractmethod
    def score(self, opportunity: Opportunity, context: WorkContext) -> float:
        """Score 0.0 to 1.0. Higher = more priority."""
        ...


# ── Concrete strategies ───────────────────────────────────────────


class MaxEVStrategy(Strategy):
    """Prioritize opportunities with highest expected value."""

    name = "max_ev"
    weight = 1.0

    def score(self, opportunity: Opportunity, context: WorkContext) -> float:
        ev = opportunity.estimated_reward_max * opportunity.confidence
        max_ev = max(
            (o.estimated_reward_max * o.confidence for o in context.opportunities),
            default=1.0,
        )
        if max_ev == 0:
            return 0.0
        return min(ev / max_ev, 1.0)


class BestEffortRatioStrategy(Strategy):
    """Prioritize best $/hour ratio."""

    name = "best_effort_ratio"
    weight = 0.8

    def score(self, opportunity: Opportunity, context: WorkContext) -> float:
        ev = opportunity.estimated_reward_max * opportunity.confidence
        hours = max(opportunity.estimated_effort_hours, 0.5)
        ratio = ev / hours
        max_ratio = max(
            (
                o.estimated_reward_max * o.confidence / max(o.estimated_effort_hours, 0.5)
                for o in context.opportunities
            ),
            default=1.0,
        )
        if max_ratio == 0:
            return 0.0
        return min(ratio / max_ratio, 1.0)


class LowCompetitionStrategy(Strategy):
    """Prioritize opportunities with least competition."""

    name = "low_competition"
    weight = 0.6

    def score(self, opportunity: Opportunity, context: WorkContext) -> float:
        # No direct competition data on Opportunity yet — default 0.5
        return 0.5


class TimeSensitiveStrategy(Strategy):
    """Prioritize opportunities with approaching deadlines."""

    name = "time_sensitive"
    weight = 0.7

    def score(self, opportunity: Opportunity, context: WorkContext) -> float:
        if not opportunity.raw_data.get("due_by"):
            return 0.0
        try:
            due = datetime.fromisoformat(opportunity.raw_data["due_by"])
            hours_left = (due - datetime.now(timezone.utc)).total_seconds() / 3600
            if hours_left <= 0:
                return 0.0
            if hours_left < 24:
                return 1.0
            return max(0.0, 1.0 - hours_left / (7 * 24))
        except (ValueError, TypeError):
            return 0.0


class QuickWinStrategy(Strategy):
    """Prioritize opportunities that can be done quickly (< 2h)."""

    name = "quick_win"
    weight = 0.4

    def score(self, opportunity: Opportunity, context: WorkContext) -> float:
        hours = opportunity.estimated_effort_hours
        if hours <= 0:
            return 0.0
        if hours <= 1:
            return 1.0
        if hours <= 2:
            return 0.7
        return max(0.0, 1.0 - hours / 8)


class AvailabilityStrategy(Strategy):
    """Filter by current time availability."""

    name = "availability"
    weight = 0.5

    def score(self, opportunity: Opportunity, context: WorkContext) -> float:
        available_hours = context.available_time_hours
        if available_hours <= 0:
            return 0.0
        if opportunity.estimated_effort_hours <= available_hours:
            return 1.0
        return available_hours / opportunity.estimated_effort_hours if opportunity.estimated_effort_hours > 0 else 0.0


class CycleBalanceStrategy(Strategy):
    """Ensure we're not doing only one type of work."""

    name = "cycle_balance"
    weight = 0.3

    def score(self, opportunity: Opportunity, context: WorkContext) -> float:
        cycle_counts = context.get_cycle_counts()
        total = sum(cycle_counts.values())
        if total == 0:
            return 0.5
        current = cycle_counts.get(opportunity.cycle, 0)
        return 1.0 - (current / total)


# ── Strategy Engine ────────────────────────────────────────────────


class StrategyEngine(Engine):
    """Decides what to work on RIGHT NOW.

    Not planning — DECIDING.
    Runs every time the queue needs prioritization.
    """

    name = "strategy_engine"

    def __init__(self, event_bus: Any | None = None) -> None:
        super().__init__()
        self.strategies: list[Strategy] = [
            MaxEVStrategy(),
            BestEffortRatioStrategy(),
            LowCompetitionStrategy(),
            TimeSensitiveStrategy(),
            QuickWinStrategy(),
            AvailabilityStrategy(),
            CycleBalanceStrategy(),
        ]
        self.event_bus = event_bus

    def add_strategy(self, strategy: Strategy) -> None:
        self.strategies.append(strategy)

    def set_weights(self, weights: dict[str, float]) -> None:
        """Override strategy weights dynamically."""
        for s in self.strategies:
            if s.name in weights:
                s.weight = weights[s.name]

    def get_statistics(self) -> dict[str, Any]:
        return {
            "strategies": [s.name for s in self.strategies],
            "weights": {s.name: s.weight for s in self.strategies},
        }

    async def decide(
        self,
        opportunities: list[Opportunity],
        context: WorkContext | None = None,
    ) -> list[PrioritizedOpportunity]:
        """Score all opportunities and return prioritized list."""
        if context is None:
            context = WorkContext(opportunities=opportunities)
        else:
            context.opportunities = opportunities

        scored: list[PrioritizedOpportunity] = []
        for opp in opportunities:
            total_score = 0.0
            total_weight = 0.0
            reasons: list[str] = []

            for strategy in self.strategies:
                try:
                    score = strategy.score(opp, context)
                    total_score += score * strategy.weight
                    total_weight += strategy.weight
                    if score > 0.3:
                        reasons.append(f"{strategy.name}={score:.2f}")
                except Exception as e:
                    logger.warning("Strategy %s failed for %s: %s", strategy.name, opp.id, e)

            priority = total_score / total_weight if total_weight > 0 else 0.0
            ev = opp.estimated_reward_max * opp.confidence

            scored.append(PrioritizedOpportunity(
                opportunity=opp,
                priority=priority,
                reason=" | ".join(reasons),
                estimated_ev=ev,
                estimated_time=opp.estimated_effort_hours,
                strategy_applied=self.__class__.__name__,
            ))

        scored.sort(key=lambda p: p.priority, reverse=True)
        self._emit("strategy:decided", {
            "top_choice": scored[0].opportunity.id if scored else None,
            "total_considered": len(scored),
            "top_3": [p.opportunity.name for p in scored[:3]],
        })
        return scored

    async def should_continue(
        self,
        current: Opportunity,
        new_opportunities: list[Opportunity],
        context: WorkContext,
    ) -> tuple[bool, str]:
        """Should we continue current work or switch? Returns (keep_going, reason)."""
        if not new_opportunities:
            return True, "No new opportunities to consider"

        scored = await self.decide([current] + new_opportunities, context)
        if len(scored) < 2:
            return True, "Only one option"

        current_rank = next(
            (i for i, p in enumerate(scored) if p.opportunity.id == current.id),
            None,
        )
        if current_rank is None or current_rank == 0:
            return True, "Current is still highest priority"

        best_alt = scored[0]
        current_entry = scored[current_rank]

        if best_alt.priority > current_entry.priority * 1.5:
            return False, (
                f"Better opportunity: {best_alt.opportunity.name} "
                f"(priority {best_alt.priority:.2f} vs {current_entry.priority:.2f})"
            )

        return True, "Current priority within acceptable range"

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        if self.event_bus:
            with contextlib.suppress(Exception):
                self.event_bus.publish(event, **data)

    async def initialize(self) -> None:
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "name": self.name,
            "strategies": [s.name for s in self.strategies],
        }
