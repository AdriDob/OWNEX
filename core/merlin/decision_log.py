"""MERLIN Decision Log — structured record of decisions with expected vs actual outcomes.

Enables MERLIN to learn from past decisions and improve recommendations over time.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from core.merlin.memory import MerlinMemory

logger = logging.getLogger("orion.core.merlin.decisions")


class MerlinDecisionLog:
    """Records and retrieves strategic decisions with outcome tracking."""

    def __init__(self, memory: MerlinMemory | None = None) -> None:
        self._memory = memory or MerlinMemory()

    def record(
        self,
        decision_id: str,
        category: str,
        description: str,
        expected_impact: str,
        confidence: float = 0.5,
        alternatives: list[str] | None = None,
    ) -> None:
        entry = {
            "decision_id": decision_id,
            "category": category,
            "description": description,
            "expected_impact": expected_impact,
            "confidence": confidence,
            "alternatives": alternatives or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
            "actual_impact": None,
        }
        self._memory.store_decision(decision_id, entry)
        logger.info("Decision recorded: %s — %s", decision_id, description[:80])

    def resolve(self, decision_id: str, actual_impact: str, success: bool) -> None:
        entries = self._memory._store.query(
            namespace="merlin",
            search=decision_id,
            limit=1,
        )
        if not entries:
            logger.warning("Decision not found for resolution: %s", decision_id)
            return

        entry = entries[0]
        try:
            data = json.loads(entry.get("content", "{}"))
        except (json.JSONDecodeError, ValueError):
            data = {}

        data["status"] = "resolved" if success else "failed"
        data["actual_impact"] = actual_impact
        data["resolved_at"] = datetime.now(timezone.utc).isoformat()
        self._memory.store_decision(decision_id, data)

    def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        entries = self._memory._store.query(
            namespace="merlin",
            tags=["decision"],
            limit=limit,
        )
        results = []
        for e in entries:
            try:
                data = json.loads(e.get("content", "{}"))
                results.append(data)
            except (json.JSONDecodeError, ValueError):
                pass
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]

    def get_learning_insights(self) -> dict[str, Any]:
        recent = self.get_recent(50)
        total = len(recent)
        resolved = sum(1 for d in recent if d.get("status") == "resolved")
        failed = sum(1 for d in recent if d.get("status") == "failed")
        pending = total - resolved - failed

        categories: dict[str, int] = {}
        for d in recent:
            cat = d.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_decisions": total,
            "resolved": resolved,
            "failed": failed,
            "pending": pending,
            "categories": categories,
        }
