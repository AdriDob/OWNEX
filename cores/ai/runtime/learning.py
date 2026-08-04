"""OAR Learning Engine — Routing optimization over time."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from .interfaces import LearningEngineProtocol, OARConfig, RoutingDecision, TaskType, get_config

logger = logging.getLogger("oar.learning")


class LearningEngine(LearningEngineProtocol):
    """Learns optimal routing from historical outcomes."""

    def __init__(self, config: OARConfig | None = None):
        self._config = config or get_config()
        self._outcomes: list[tuple[RoutingDecision, bool, float, float]] = []  # (decision, success, quality, cost)
        self._preferences: dict[TaskType, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._provider_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "success": 0, "quality_sum": 0.0, "cost_sum": 0.0}
        )

    def record_routing(self, decision: RoutingDecision, success: bool, quality: float) -> None:
        """Record a routing decision outcome."""
        cost = decision.estimated_cost_usd

        # Store outcome
        self._outcomes.append((decision, success, quality, cost))
        if len(self._outcomes) > 10000:
            self._outcomes = self._outcomes[-5000:]

        # Update provider stats
        key = f"{decision.provider_id}:{decision.model_id}"
        stats = self._provider_stats[key]
        stats["total"] += 1
        if success:
            stats["success"] += 1
        stats["quality_sum"] += quality
        stats["cost_sum"] += cost

        # Update preferences for this task type
        task_type = decision.task_type
        provider_key = decision.provider_id
        success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
        avg_quality = stats["quality_sum"] / stats["total"] if stats["total"] > 0 else 0
        avg_cost = stats["cost_sum"] / stats["total"] if stats["total"] > 0 else 0

        # Score: success_rate * 0.5 + avg_quality * 0.3 + (1 - normalized_cost) * 0.2
        cost_score = max(0, 1 - avg_cost / 0.01) if avg_cost > 0 else 1.0
        preference_score = success_rate * 0.5 + avg_quality * 0.3 + cost_score * 0.2

        self._preferences[task_type][provider_key] = preference_score

    def get_preferences(self, task_type: TaskType, user_id: str | None = None) -> dict[str, float]:
        """Get learned provider preferences for a task type."""
        prefs = self._preferences.get(task_type, {}).copy()

        # Apply user-specific adjustments if needed
        if user_id:
            # Could add user-specific learning here
            pass

        return prefs

    def get_provider_stats(self, provider_id: str | None = None) -> dict[str, Any]:
        """Get aggregated provider statistics."""
        if provider_id:
            return {k: v for k, v in self._provider_stats.items() if k.startswith(f"{provider_id}:")}
        return dict(self._provider_stats)

    def get_recommendations(self, task_type: TaskType, top_k: int = 3) -> list[tuple[str, float]]:
        """Get top provider recommendations for a task type."""
        prefs = self.get_preferences(task_type)
        sorted_prefs = sorted(prefs.items(), key=lambda x: x[1], reverse=True)
        return sorted_prefs[:top_k]

    def decay_old_data(self, days: int = 30) -> None:
        """Decay old outcome data."""
        datetime.now() - timedelta(days=days)
        # Note: outcomes don't have timestamps in current implementation
        # This would need to be added for full time-based decay
        logger.info("Learning data decay requested (not fully implemented)")

    def export_learning_data(self) -> dict[str, Any]:
        """Export learning data for persistence."""
        return {
            "preferences": {tt.value: dict(prefs) for tt, prefs in self._preferences.items()},
            "provider_stats": {k: dict(v) for k, v in self._provider_stats.items()},
            "outcomes_count": len(self._outcomes),
        }

    def import_learning_data(self, data: dict[str, Any]) -> None:
        """Import learning data from persistence."""
        for tt_str, prefs in data.get("preferences", {}).items():
            try:
                tt = TaskType(tt_str)
                self._preferences[tt].update(prefs)
            except ValueError:
                pass

        for k, v in data.get("provider_stats", {}).items():
            self._provider_stats[k].update(v)


# Global learning engine instance
_learning_engine: LearningEngine | None = None


def get_learning_engine(config: OARConfig | None = None) -> LearningEngine:
    """Get global learning engine."""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine(config)
    return _learning_engine
