"""Novelty scoring for the self-improvement curriculum.

Was a bare stub (`class NoveltyScorer: pass`) while
`SelfImprovementEngine.run_once()` calls `NoveltyScorer(history).novelty(task)`
and `TaskGenerator` uses it to avoid re-proposing solved tasks.

Deterministic and honest: a task identical to one already solved scores 0.0,
and a task that only overlaps partially scores by overlap. No LLM judgment.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def _fingerprint(task: Any) -> frozenset[str]:
    """Comparable tokens of a task: category + prompt words."""
    category = str(getattr(getattr(task, "category", None), "value", "") or "")
    prompt = str(getattr(task, "prompt", "") or getattr(task, "description", "") or "")
    words = {w for w in "".join(c if c.isalnum() else " " for c in prompt.lower()).split() if len(w) > 3}
    return frozenset({category.lower()} | words)


class NoveltyScorer:
    """Scores how much a task differs from the already-solved history."""

    def __init__(self, history: Sequence[Any] | None = None) -> None:
        self._history = list(history or [])

    def novelty(self, task: Any) -> float:
        """1.0 = never seen, 0.0 = identical to something already solved.

        With empty history the honest answer is 1.0 (nothing is a repeat),
        not a neutral 0.5.
        """
        seen = [_fingerprint(t) for t in self._history]
        if not seen:
            return 1.0
        candidate = _fingerprint(task)
        if not candidate:
            return 1.0
        best_overlap = max((len(candidate & s) / len(candidate | s)) if (candidate | s) else 0.0 for s in seen)
        return round(max(0.0, 1.0 - best_overlap), 4)

    def is_duplicate(self, task: Any) -> bool:
        """True when the task adds nothing to what was already solved."""
        return self.novelty(task) <= 0.0

    def novelty_against(self, task: Any, history: Sequence[Any]) -> float:
        """Novelty of `task` against an explicit history.

        Consumer: `TaskGenerator.generate_batch` (task_generator.py:167), which
        filters with `>= 0.3`. Scored with the same rule as `novelty()` so the
        two paths cannot disagree.
        """
        return NoveltyScorer(history).novelty(task)
