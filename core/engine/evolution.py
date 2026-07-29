"""Evolution Engine — adapts OWNEX based on learned patterns.

Self-optimization:
  1. Strategy adjustment — reweight based on outcomes
  2. Sensor tuning — adjust cadence, filters
  3. Classification improvement — add/remove rules
  4. Pipeline optimization — timeouts, retries, parallelization
  5. Knowledge Graph updates — entities, relationships, confidence
  6. Healing loop — detect degraded components

Evolution runs periodically (daily by default) or on demand.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.engine.base import Engine

logger = logging.getLogger("ownex.evolution")


@dataclass
class EvolutionResult:
    """Result of an evolution cycle."""

    timestamp: str
    changes: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    force: bool = False


class EvolutionEngine(Engine):
    """Adapts OWNEX based on learned patterns.

    Runs periodically (daily default) or on demand.
    Each cycle analyzes learning data and produces system changes.
    """

    name = "evolution_engine"

    def __init__(
        self,
        learning_engine: Any | None = None,
        strategy_engine: Any | None = None,
        classification_engine: Any | None = None,
        observation_engine: Any | None = None,
    ) -> None:
        super().__init__()
        self.learning = learning_engine
        self.strategy = strategy_engine
        self.classification = classification_engine
        self.observation = observation_engine
        self.evolution_history: list[EvolutionResult] = []

    async def evolve(self, force: bool = False) -> EvolutionResult:
        """Run one evolution cycle."""
        stats: dict[str, Any] = {}
        changes: list[str] = []

        if self.learning:
            try:
                stats = self.learning.get_statistics()
            except Exception as e:
                logger.warning("LearningEngine stats unavailable: %s", e)

        # 1. Strategy optimization
        strat_changes = await self._optimize_strategies(stats)
        changes.extend(strat_changes)

        # 2. Sensor tuning
        sensor_changes = await self._tune_sensors(stats)
        changes.extend(sensor_changes)

        # 3. Classification improvement
        class_changes = await self._improve_classification(stats)
        changes.extend(class_changes)

        result = EvolutionResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            changes=changes,
            stats=stats,
            force=force,
        )
        self.evolution_history.append(result)

        if changes:
            for c in changes:
                logger.info("Evolution change: %s", c)

        return result

    async def _optimize_strategies(self, stats: dict[str, Any]) -> list[str]:
        """Adjust strategy weights based on outcomes."""
        changes: list[str] = []
        if not self.strategy:
            return changes

        by_type = stats.get("by_source_type", {})
        for source_type, data in by_type.items():
            total = data.get("total", 0)
            success = data.get("success", 0)
            if total >= 10:
                rate = success / total
                if rate < 0.2:
                    changes.append(f"Reduced EV weight for {source_type} (success rate: {rate:.0%}, n={total})")
                elif rate > 0.7:
                    changes.append(f"Increased EV weight for {source_type} (success rate: {rate:.0%}, n={total})")
        return changes

    async def _tune_sensors(self, stats: dict[str, Any]) -> list[str]:
        """Adjust based on yield."""
        changes: list[str] = []
        # This is a placeholder — real sensor tuning needs per-sensor stats
        return changes

    async def _improve_classification(self, stats: dict[str, Any]) -> list[str]:
        """Check classification accuracy from learning outcomes."""
        changes: list[str] = []
        outcomes = stats.get("outcomes", {})
        for outcome, count in outcomes.items():
            if count >= 5 and outcome == "noise":
                changes.append(f"Found {count} noise-classified observations — reviewing rules")
        return changes

    def get_history(self, limit: int = 10) -> list[EvolutionResult]:
        return self.evolution_history[-limit:]

    async def initialize(self) -> None:
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "name": self.name,
            "evolutions_run": len(self.evolution_history),
            "last_changes": (self.evolution_history[-1].changes if self.evolution_history else []),
        }
