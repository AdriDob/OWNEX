"""Solution Learner — Learns from problem→solution outcomes."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from cores.events.event_bus import get_event_bus
from cores.memory.store import get_memory_store

logger = logging.getLogger("ownex.self_healer.learner")

LEARNING_NAMESPACE = "self_healer"
MAX_ENTRIES = 10000


class SolutionLearner:
    """Learns from problem→solution outcomes to improve future diagnoses."""

    def __init__(self):
        self.memory = get_memory_store()
        self.event_bus = get_event_bus()
        self._learning_count = 0

        # Subscribe to deployment outcomes
        self.event_bus.subscribe("self_healer:deployment_completed", self._on_deployment_completed)
        self.event_bus.subscribe("self_healer:deployment_failed", self._on_deployment_failed)

    def _on_deployment_completed(self, **data) -> None:
        """Record successful deployment as positive learning."""
        deployment_id = data.get("id")
        patch_id = data.get("patch_id")
        self._record_outcome(
            deployment_id=deployment_id,
            patch_id=patch_id,
            success=True,
            metrics=data.get("metrics_after", {}),
            health_checks=data.get("health_checks", {}),
        )

    def _on_deployment_failed(self, **data) -> None:
        """Record failed deployment as negative learning."""
        deployment_id = data.get("id")
        patch_id = data.get("patch_id")
        rollback_reason = data.get("rollback_reason", "")
        self._record_outcome(
            deployment_id=deployment_id,
            patch_id=patch_id,
            success=False,
            error=rollback_reason,
        )

    def _record_outcome(
        self,
        deployment_id: str,
        patch_id: str,
        success: bool,
        metrics: dict[str, float] | None = None,
        health_checks: dict[str, bool] | None = None,
        error: str = "",
    ) -> None:
        """Record a deployment outcome for learning."""
        self._learning_count += 1

        entry = {
            "type": "deployment_outcome",
            "deployment_id": deployment_id,
            "patch_id": patch_id,
            "success": success,
            "metrics": metrics or {},
            "health_checks": health_checks or {},
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
            "learning_id": f"learn_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{self._learning_count}",
        }

        # Store in memory
        self.memory.store(
            namespace=LEARNING_NAMESPACE,
            key=entry["learning_id"],
            content=json.dumps(entry),
            tags=["deployment", "outcome", "success" if success else "failure"],
            priority=2.0 if success else 3.0,
        )

        # Also store pattern for quick lookup
        self._store_pattern(entry)

        logger.info(f"Recorded learning: {entry['learning_id']} (success={success})")

    def _store_pattern(self, outcome: dict[str, Any]) -> None:
        """Extract and store problem→solution pattern."""
        # This would ideally correlate with the original problem
        # For now, store the outcome as a pattern
        pattern_key = f"pattern_{outcome['patch_id']}"
        self.memory.store(
            namespace=LEARNING_NAMESPACE,
            key=pattern_key,
            content=json.dumps(outcome),
            tags=["pattern", "deployment"],
            priority=1.5,
        )

    def get_successful_patterns(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get successful deployment patterns for reference."""
        results = self.memory.query(
            namespace=LEARNING_NAMESPACE,
            tags=["deployment", "outcome", "success"],
            limit=limit,
        )
        patterns = []
        for entry in results:
            try:
                content = json.loads(entry.content)
                if content.get("success"):
                    patterns.append(content)
            except Exception:
                pass
        return patterns

    def get_failed_patterns(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get failed deployment patterns to avoid."""
        results = self.memory.query(
            namespace=LEARNING_NAMESPACE,
            tags=["deployment", "outcome", "failure"],
            limit=limit,
        )
        patterns = []
        for entry in results:
            try:
                content = json.loads(entry.content)
                if not content.get("success"):
                    patterns.append(content)
            except Exception:
                pass
        return patterns

    def get_similar_successful_fixes(self, problem_category: str, limit: int = 5) -> list[dict[str, Any]]:
        """Find successful fixes for similar problem categories."""
        results = self.memory.query(
            namespace=LEARNING_NAMESPACE,
            tags=["pattern"],
            search=problem_category,
            limit=limit,
        )
        patterns = []
        for entry in results:
            try:
                content = json.loads(entry.content)
                if content.get("success"):
                    patterns.append(content)
            except Exception:
                pass
        return patterns

    def get_learning_stats(self) -> dict[str, Any]:
        """Get learning statistics."""
        all_entries = self.memory.query(namespace=LEARNING_NAMESPACE, limit=10000)
        total = len(all_entries)
        successes = sum(1 for e in all_entries if json.loads(e.content).get("success", False))
        failures = total - successes

        return {
            "total_entries": total,
            "successful_deployments": successes,
            "failed_deployments": failures,
            "success_rate": successes / total if total > 0 else 0,
            "learning_count": self._learning_count,
        }

    def prune_old_entries(self, max_entries: int = MAX_ENTRIES) -> int:
        """Prune old learning entries if over limit."""
        all_entries = self.memory.query(namespace=LEARNING_NAMESPACE, limit=MAX_ENTRIES * 2)
        if len(all_entries) <= max_entries:
            return 0

        # Sort by timestamp and remove oldest
        entries_with_time = []
        for entry in all_entries:
            try:
                content = json.loads(entry.content)
                ts = content.get("timestamp", "")
                entries_with_time.append((ts, entry.key))
            except Exception:
                pass

        entries_with_time.sort()
        to_remove = len(entries_with_time) - max_entries
        removed = 0

        for ts, key in entries_with_time[:to_remove]:
            self.memory.delete(LEARNING_NAMESPACE, key)
            removed += 1

        logger.info(f"Pruned {removed} old learning entries")
        return removed


# Singleton
_solution_learner: SolutionLearner | None = None


def get_solution_learner() -> SolutionLearner:
    global _solution_learner
    if _solution_learner is None:
        _solution_learner = SolutionLearner()
    return _solution_learner
