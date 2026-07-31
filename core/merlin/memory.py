"""MERLIN Memory — strategic context built on UnifiedMemoryStore.

Provides MERLIN-specific memory operations:
  - Store daily briefs, decisions, user preferences
  - Retrieve strategic context for planning
  - Track user goals and progress
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from core.memory.store import UnifiedMemoryStore

logger = logging.getLogger("orion.core.merlin.memory")

MERLIN_NAMESPACE = "merlin"
PREFERENCES_KEY = "user_preferences"
GOALS_KEY = "strategic_goals"
DAILY_BRIEF_PREFIX = "daily_brief_"
DECISION_PREFIX = "decision_"


class MerlinMemory:
    """Strategic memory for MERLIN, backed by UnifiedMemoryStore."""

    def __init__(self) -> None:
        self._store = UnifiedMemoryStore()

    def remember(self, key: str, content: str, tags: list[str] | None = None, priority: float = 0.0) -> None:
        self._store.store(namespace=MERLIN_NAMESPACE, key=key, content=content, tags=tags or [], priority=priority)

    def recall(self, key: str) -> str:
        entries = self._store.query(namespace=MERLIN_NAMESPACE, search=key)
        if entries:
            return entries[0].get("content", "")
        return ""

    def store_brief(self, brief_text: str) -> None:
        date_tag = datetime.now(UTC).strftime("%Y-%m-%d")
        self.remember(
            key=f"{DAILY_BRIEF_PREFIX}{date_tag}",
            content=brief_text,
            tags=["brief", date_tag],
            priority=1.0,
        )

    def get_latest_brief(self) -> str:
        entries = self._store.query(namespace=MERLIN_NAMESPACE, tags=["brief"], limit=10)
        brief_entries = [e for e in entries if e.get("key", "").startswith(DAILY_BRIEF_PREFIX)]
        if not brief_entries:
            return ""
        brief_entries.sort(key=lambda e: e.get("created_at", ""), reverse=True)
        return brief_entries[0].get("content", "")

    def store_decision(self, decision_id: str, context: dict[str, Any]) -> None:
        self.remember(
            key=f"{DECISION_PREFIX}{decision_id}",
            content=json.dumps(context, default=str),
            tags=["decision"],
            priority=0.8,
        )

    def set_preferences(self, prefs: dict[str, Any]) -> None:
        self.remember(
            key=PREFERENCES_KEY,
            content=json.dumps(prefs, default=str),
            tags=["preferences"],
            priority=2.0,
        )

    def get_preferences(self) -> dict[str, Any]:
        raw = self.recall(PREFERENCES_KEY)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                pass
        return {}

    def set_goals(self, goals: dict[str, Any]) -> None:
        self.remember(
            key=GOALS_KEY,
            content=json.dumps(goals, default=str),
            tags=["goals", "strategic"],
            priority=3.0,
        )

    def get_goals(self) -> dict[str, Any]:
        raw = self.recall(GOALS_KEY)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                pass
        return {}

    def get_strategic_context(self) -> str:
        goals = self.get_goals()
        prefs = self.get_preferences()
        latest = self.get_latest_brief()
        parts = []
        if goals:
            parts.append(f"Objetivos estratégicos: {json.dumps(goals, indent=2, default=str)}")
        if prefs:
            parts.append(f"Preferencias: {json.dumps(prefs, indent=2, default=str)}")
        if latest:
            parts.append(f"Último brief: {latest[:500]}")
        return "\n\n".join(parts)
