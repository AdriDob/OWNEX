"""Unified Memory — Single entry point for all memory tiers (Personal, Operational, Strategic).

Phase 2 of Consolidation Plan: wraps existing systems into 3-tier structure.
- Personal: preferences, goals, constraints (MerlinMemory + UnifiedMemoryStore)
- Operational: what ran, what worked, what failed (DecisionJournal + TaskOutcome)
- Strategic: patterns, platform performance, task-type ROI (KnowledgeGraph + learning_scorer)
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.unified_memory")


@dataclass
class PersonalMemory:
    """Tier 1: User preferences, goals, constraints."""

    _store: Any = field(default=None, repr=False)
    _merlin: Any = field(default=None, repr=False)

    def set_preference(self, key: str, value: Any, namespace: str = "user") -> int:
        """Set a user preference."""
        if self._store:
            return self._store.store(
                namespace=namespace,
                key=key,
                content=str(value),
                metadata={"type": "preference", "value": value},
                tags=["preference"],
            )
        return -1

    def get_preference(self, key: str, namespace: str = "user") -> Any:
        """Get a user preference."""
        if self._store:
            entry = self._store.get(namespace, key)
            if entry:
                return entry.get("metadata", {}).get("value", entry.get("content"))
        return None

    def set_goal(self, goal: str, target_date: str | None = None) -> int:
        """Set a strategic goal."""
        if self._store:
            return self._store.store(
                namespace="user",
                key=f"goal_{goal[:50]}",
                content=goal,
                metadata={"type": "goal", "target_date": target_date},
                tags=["goal"],
                priority=2.0,
            )
        return -1

    def get_goals(self) -> list[dict]:
        """Get all goals."""
        if self._store:
            return self._store.query(namespace="user", tags=["goal"], limit=50)
        return []

    def set_constraint(self, constraint: str) -> int:
        """Set a user constraint (e.g., 'no weekends', 'max 4h/day')."""
        if self._store:
            return self._store.store(
                namespace="user",
                key=f"constraint_{constraint[:50]}",
                content=constraint,
                metadata={"type": "constraint"},
                tags=["constraint"],
            )
        return -1

    def get_constraints(self) -> list[dict]:
        """Get all constraints."""
        if self._store:
            return self._store.query(namespace="user", tags=["constraint"], limit=50)
        return []


@dataclass
class OperationalMemory:
    """Tier 2: What ran, what worked, what failed (DecisionJournal + TaskOutcome)."""

    _store: Any = field(default=None, repr=False)
    _decision_journal: Any = field(default=None, repr=False)

    def record_decision(
        self,
        app_id: str,
        agent_id: str,
        action: str,
        reason: str,
        data_snapshot: dict | None = None,
        confidence: float = 0.0,
        risk_score: float = 0.0,
    ) -> str:
        """Record a decision (wraps DecisionJournal)."""
        if self._decision_journal:
            return self._decision_journal.log_decision(
                app_id=app_id,
                agent_id=agent_id,
                action=action,
                reason=reason,
                data_snapshot=data_snapshot,
                confidence=confidence,
                risk_score=risk_score,
            )
        return ""

    def record_outcome(self, decision_id: str, outcome: str, reward: float = 0.0, notes: str = "") -> bool:
        """Record outcome for a decision (feedback loop)."""
        if self._decision_journal:
            return self._decision_journal.record_outcome(decision_id, outcome, reward, notes)
        return False

    def get_decisions(
        self,
        app_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
        outcome: str | None = None,
    ) -> list[dict]:
        """Query decisions."""
        if self._decision_journal:
            return self._decision_journal.get_decisions(app_id, agent_id, limit, outcome)
        return []

    def record_task_outcome(
        self,
        task_id: str,
        task_type: str,
        success: bool,
        reward: float = 0.0,
        duration_seconds: float = 0.0,
        error: str | None = None,
    ) -> int:
        """Record a task execution outcome."""
        if self._store:
            return self._store.store(
                namespace="operational",
                key=f"task_{task_id}",
                content=task_type,
                metadata={
                    "type": "task_outcome",
                    "task_id": task_id,
                    "task_type": task_type,
                    "success": success,
                    "reward": reward,
                    "duration_seconds": duration_seconds,
                    "error": error,
                },
                tags=["task_outcome", task_type, "success" if success else "failure"],
                priority=1.0 if success else 2.0,
            )
        return -1

    def get_task_outcomes(self, task_type: str | None = None, limit: int = 100) -> list[dict]:
        """Query task outcomes."""
        if self._store:
            tags = ["task_outcome"]
            if task_type:
                tags.append(task_type)
            return self._store.query(namespace="operational", tags=tags, limit=limit)
        return []

    def get_success_rate(self, task_type: str) -> float:
        """Get success rate for a task type."""
        outcomes = self.get_task_outcomes(task_type)
        if not outcomes:
            return 0.0
        total = len(outcomes)
        successes = sum(1 for o in outcomes if o.get("metadata", {}).get("success"))
        return successes / total if total > 0 else 0.0


@dataclass
class StrategicMemory:
    """Tier 3: Patterns, platform performance, task-type ROI (KnowledgeGraph + learning_scorer)."""

    _store: Any = field(default=None, repr=False)
    _knowledge_graph: Any = field(default=None, repr=False)
    _pattern_library: Any = field(default=None, repr=False)
    _learning_scorer: Any = field(default=None, repr=False)

    def record_pattern(self, pattern_type: str, pattern_data: dict) -> int:
        """Record a learned pattern."""
        if self._pattern_library and hasattr(self._pattern_library, "record_confirmed_finding"):
            return 0
        if self._store:
            return self._store.store(
                namespace="strategic",
                key=f"pattern_{pattern_type}_{datetime.now(UTC).timestamp()}",
                content=str(pattern_data),
                metadata={"type": "pattern", "pattern_type": pattern_type, **pattern_data},
                tags=["pattern", pattern_type],
                priority=2.0,
            )
        return -1

    def find_similar_patterns(self, pattern_type: str, query: str, limit: int = 10) -> list[dict]:
        """Find similar patterns."""
        if self._store:
            return self._store.query(namespace="strategic", tags=["pattern", pattern_type], search=query, limit=limit)
        return []

    def boost_confidence(
        self, base_confidence: float, endpoint_path: str, entity_type: str | None, vuln_type: str, severity: str
    ) -> dict:
        """Boost confidence using pattern library."""
        if self._pattern_library and hasattr(self._pattern_library, "boost_endpoint_score"):
            return self._pattern_library.boost_endpoint_score(
                base_confidence, endpoint_path, entity_type, vuln_type, severity
            )
        return {"confidence": base_confidence, "reasoning": []}

    def estimate_payout(self, finding_type: str, severity: str, entity_type: str | None) -> float:
        """Estimate payout using learning scorer."""
        if self._pattern_library and hasattr(self._pattern_library, "estimate_payout"):
            return self._pattern_library.estimate_payout(finding_type, severity, entity_type)
        return 0.0

    def record_payout(self, finding_type: str, entity_type: str | None, amount: float) -> None:
        """Record actual payout for learning."""
        if self._pattern_library and hasattr(self._pattern_library, "record_payout"):
            self._pattern_library.record_payout(finding_type, entity_type, amount)
        if self._store:
            self._store.store(
                namespace="strategic",
                key=f"payout_{finding_type}_{entity_type}_{datetime.now(UTC).timestamp()}",
                content=f"{amount}",
                metadata={"type": "payout", "finding_type": finding_type, "entity_type": entity_type, "amount": amount},
                tags=["payout", finding_type],
                priority=3.0,
            )

    def get_platform_performance(self, platform: str) -> dict:
        """Get performance metrics for a platform."""
        if self._knowledge_graph:
            return {}
        return {"platform": platform, "success_rate": 0.0, "avg_payout": 0.0, "total_tasks": 0}


class UnifiedMemory:
    """Single entry point for all memory tiers.

    Usage:
        um = UnifiedMemory()
        um.personal.set_preference("language", "es")
        um.operational.record_decision("cateye", "agent1", "scan_target", "high EV")
        um.strategic.estimate_payout("xss", "high", "api")
    """

    def __init__(self):
        self._store = None
        self._merlin = None
        self._decision_journal = None
        self._knowledge_graph = None
        self._pattern_library = None
        self._learning_scorer = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization to avoid import cycles."""
        if self._initialized:
            return
        try:
            from cores.memory.store import get_memory_store

            self._store = get_memory_store()
        except Exception as e:
            logger.debug("UnifiedMemoryStore not available: %s", e)

        try:
            from cores.merlin.memory import get_merlin_memory

            self._merlin = get_merlin_memory()
        except Exception as e:
            logger.debug("MerlinMemory not available: %s", e)

        try:
            from cores.decision_journal import get_decisions, log_decision, record_outcome

            class DJWrapper:
                def log_decision(self, **kwargs):
                    return log_decision(**kwargs)

                def record_outcome(self, **kwargs):
                    return record_outcome(**kwargs)

                def get_decisions(self, **kwargs):
                    return get_decisions(**kwargs)

            self._decision_journal = DJWrapper()
        except Exception as e:
            logger.debug("DecisionJournal not available: %s", e)

        try:
            from cores.engine.knowledge_graph import KnowledgeGraph

            self._knowledge_graph = KnowledgeGraph()
            self._knowledge_graph._init_db()
        except Exception as e:
            logger.debug("KnowledgeGraph not available: %s", e)

        try:
            from cores.memory.memory import MemoryPatternLibrary

            self._pattern_library = MemoryPatternLibrary()
        except Exception as e:
            logger.debug("MemoryPatternLibrary not available: %s", e)

        try:
            from cores.memory.learning_scorer import LearningScorer

            self._learning_scorer = LearningScorer()
        except Exception as e:
            logger.debug("LearningScorer not available: %s", e)

        self._initialized = True

    @property
    def personal(self) -> PersonalMemory:
        self._lazy_init()
        return PersonalMemory(_store=self._store, _merlin=self._merlin)

    @property
    def operational(self) -> OperationalMemory:
        self._lazy_init()
        return OperationalMemory(_store=self._store, _decision_journal=self._decision_journal)

    @property
    def strategic(self) -> StrategicMemory:
        self._lazy_init()
        return StrategicMemory(
            _store=self._store,
            _knowledge_graph=self._knowledge_graph,
            _pattern_library=self._pattern_library,
            _learning_scorer=self._learning_scorer,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get combined stats from all tiers."""
        self._lazy_init()
        stats = {"personal": {}, "operational": {}, "strategic": {}}

        if self._store:
            with contextlib.suppress(Exception):
                stats["unified_store"] = self._store.get_stats()
        if self._merlin:
            with contextlib.suppress(Exception):
                stats["merlin"] = self._merlin.get_memory_stats()
        return stats


_Singleton: UnifiedMemory | None = None


def get_unified_memory() -> UnifiedMemory:
    """Get the singleton UnifiedMemory instance."""
    global _Singleton
    if _Singleton is None:
        _Singleton = UnifiedMemory()
    return _Singleton
