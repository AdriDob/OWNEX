"""Reward model for a self-improvement rollout.

Was a bare stub (`class RewardModel: pass`) while
`SelfImprovementEngine.run_once()` calls `.compute(task, evaluation, novelty)`.

The formula is the one already documented on `Experience.reward`
(models.py:242): **R_task = Validity × Difficulty × Novelty**. No coefficients
are invented here; this is the contract the data model already states.
"""

from __future__ import annotations

from typing import Any


class RewardModel:
    """Deterministic reward in [0, 1]. No LLM, no tunable magic weights."""

    def compute(self, task: Any, evaluation: Any, novelty: float) -> float:
        """R = validity × difficulty × novelty.

        - validity: did the verifier pass? (`evaluation.valid`, else `score`)
        - difficulty: harder task ⇒ more reward for the same success
        - novelty: a repeat of a solved task is worth less

        Any missing signal is UNKNOWN ⇒ 0.0, never a default 1.0 that would
        reward a run we could not measure.
        """
        validity = 1.0 if getattr(evaluation, "valid", False) else 0.0
        if not validity:
            return 0.0
        difficulty = float(getattr(task, "difficulty", 0.0) or 0.0)
        novelty = float(novelty or 0.0)
        return round(validity * difficulty * novelty, 6)
