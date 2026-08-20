"""Reward computation for the self-improvement loop.

R_task = Validity x Difficulty x Novelty

  - Validity: 1.0 when the rollout objectively passed, 0.0 otherwise.
  - Difficulty: normalized task difficulty (0.0 .. 1.0) with a small boost so
    a successfully solved hard task scores higher than an easy one.
  - Novelty: 0.0 .. 1.0 overlap distance against the already-solved history.

The reward is a deterministic float used by the curriculum to pick the next
difficulty and by the capability stats to track per-skill progress.
"""

from __future__ import annotations

from core.self_improvement.models import Evaluation, Task
from core.self_improvement.novelty import NoveltyScorer


class RewardModel:
    """Computes R_task from an evaluation, difficulty and novelty."""

    def compute(self, task: Task, evaluation: Evaluation, novelty: float) -> float:
        validity = evaluation.validity_score if evaluation.valid else 0.0
        difficulty = max(0.0, min(1.0, task.difficulty))
        # Penalize too-easy successes slightly; reward hard-but-valid.
        difficulty_term = 0.5 + 0.5 * difficulty
        novelty_term = max(0.0, min(1.0, novelty))
        return round(validity * difficulty_term * novelty_term, 6)

    def compute_with_history(self, task: Task, evaluation: Evaluation, history: list) -> float:
        """Compute reward, deriving novelty from the experience history."""
        scorer = NoveltyScorer(history)
        novelty = scorer.novelty(task)
        return self.compute(task, evaluation, novelty)
