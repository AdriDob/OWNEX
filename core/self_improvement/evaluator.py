"""Evaluation of rollouts in the self-improvement loop.

Evaluation maps a Rollout (real harness output) to an Evaluation verdict using
deterministic rules: exit code 0 + expected marker => success; timeout/policy/
os errors => failure with a reason. No LLM is used for grading, keeping the
reward signal objective and reproducible.
"""

from __future__ import annotations

import re

from core.self_improvement.models import Evaluation, Rollout, Task, TaskCategory

# Markers each category's verifier prints on success.
_SUCCESS_MARKERS: dict[TaskCategory, str] = {
    TaskCategory.CODE: "CODE_OK",
    TaskCategory.TEST: "passed",
    TaskCategory.DEBUG: "PASS",
    TaskCategory.ANALYSIS: "ANALYSIS_OK",
    TaskCategory.GENERATION: "GENERATION_OK",
    TaskCategory.SECURITY: "SECURITY_OK",
    TaskCategory.REASONING: "REASONING_OK",
}


class Evaluator:
    """Deterministic grader for harness rollouts."""

    def evaluate(self, task: Task, rollout: Rollout) -> Evaluation:
        notes: list[str] = []
        valid = False

        if rollout.error:
            notes.append(f"harness error: {rollout.error}")
        elif rollout.exit_code == -9:
            notes.append("timeout")
        elif rollout.exit_code != 0:
            notes.append(self._failure_reason(task, rollout))
        else:
            marker = _SUCCESS_MARKERS.get(task.category)
            combined = (rollout.stdout or "") + (rollout.stderr or "")
            if marker is None or marker in combined:
                valid = True
                notes.append("verification passed")
            else:
                notes.append(f"exit 0 but missing success marker {marker!r}")

        return Evaluation(
            task_id=task.id,
            rollout=rollout,
            valid=valid,
            validity_score=1.0 if valid else 0.0,
            checks_passed=1 if valid else 0,
            checks_total=1,
            notes=notes,
        )

    def _failure_reason(self, task: Task, rollout: Rollout) -> str:
        if task.category == TaskCategory.TEST:
            return "pytest reported failures"
        combined = (rollout.stdout or "") + (rollout.stderr or "")
        match = re.search(r"(?:FAIL|Error|BAD)[^\n]*", combined)
        return f"exit {rollout.exit_code}" + (f": {match.group(0)[:200]}" if match else "")
