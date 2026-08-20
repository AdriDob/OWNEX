"""Novelty scoring for the self-improvement loop.

A task is valuable if it is not a duplicate of what the system already solved.
Novelty is computed deterministically (0.0 .. 1.0) by comparing the task's
textual signature against previously experienced tasks using token overlap.
No embeddings, no network, no external models.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.self_improvement.models import Task

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _signature(text: str) -> Counter[str]:
    """Lowercased alphanumeric token histogram of a piece of text."""
    return Counter(_TOKEN_RE.findall(text.lower()))


class NoveltyScorer:
    """Deterministic novelty scorer based on token-overlap distance."""

    def __init__(self, history: list[Any] | None = None) -> None:
        self._history: list[Counter[str]] = []
        if history:
            for item in history:
                sig = self._extract_signature(item)
                if sig is not None:
                    self._history.append(sig)

    def _extract_signature(self, item: Any) -> Counter[str] | None:
        """Extract a token signature from a stored item (Experience dict or Task)."""
        text_parts: list[str] = []
        if isinstance(item, dict):
            task = item.get("task") or {}
            if isinstance(task, dict):
                text_parts.append(task.get("title", ""))
                text_parts.append(task.get("description", ""))
                text_parts.append(task.get("expected", ""))
            else:
                text_parts.append(str(item.get("title", "")))
                text_parts.append(str(item.get("description", "")))
                text_parts.append(str(item.get("expected", "")))
        else:
            for attr in ("title", "description", "expected"):
                text_parts.append(str(getattr(item, attr, "")))
        joined = " ".join(p for p in text_parts if p)
        return _signature(joined) if joined else None

    @staticmethod
    def _jaccard(a: Counter[str], b: Counter[str]) -> float:
        inter = sum((a & b).values())
        union = sum((a | b).values())
        return inter / union if union else 0.0

    def novelty(self, task) -> float:
        """Return 1.0 if the task is unlike any seen before, 0.0 if it's a duplicate."""
        sig = _signature(f"{task.title} {task.description} {task.expected}")
        if not sig or not self._history:
            return 1.0
        overlaps = [self._jaccard(sig, h) for h in self._history]
        return 1.0 - max(overlaps)

    def novelty_against(self, task, other_tasks: list[Task]) -> float:
        """Novelty against an explicit candidate list (used before generation)."""
        if not other_tasks:
            return 1.0
        sig = _signature(f"{task.title} {task.description} {task.expected}")
        if not sig:
            return 1.0
        overlaps = [self._jaccard(sig, _signature(f"{t.title} {t.description} {t.expected}")) for t in other_tasks]
        return 1.0 - max(overlaps)
