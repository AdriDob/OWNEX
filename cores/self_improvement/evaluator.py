"""Evaluator — judges a self-improvement rollout against its verifier.

Was a stub that returned `score=0.5, passed=True` for **any** proposal — that
certifies as valid a run that was never measured. It now reads the rollout the
harness actually produced.

Two call shapes are supported because both exist in the tree:
- `evaluate(task, rollout)` — `rollout.py:120`, the live path
- `evaluate(proposal)` — a bare dict, kept for backward compatibility
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationResult:
    """Result of an evaluation.

    Carries both shapes the tree uses: the `models.Evaluation` fields the
    Experience persists (`task_id`, `rollout`, `valid`, `notes`) and the
    score/details used by the reports. One object, so `Experience.to_dict()`
    and `Experience.from_dict()` round-trip without losing a key.
    """

    task_id: str = ""
    rollout: Any = None
    valid: bool = False
    validity_score: float = 0.0
    checks_passed: int = 0
    checks_total: int = 0
    notes: list[str] = field(default_factory=list)
    score: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    passed: bool = False

    def __post_init__(self) -> None:
        # `passed` is the historical alias of `valid`; keep one truth.
        if self.valid and not self.passed:
            self.passed = True
        if self.passed:
            self.valid = True

    @property
    def checks_summary(self) -> str:
        return f"{self.checks_passed}/{self.checks_total} checks passed"

    def to_dict(self) -> dict[str, Any]:
        """Keys match `models.Evaluation.to_dict` so the store round-trips."""
        rollout = self.rollout
        return {
            "task_id": self.task_id,
            "rollout": rollout.to_dict() if hasattr(rollout, "to_dict") else None,
            "valid": self.valid,
            "validity_score": self.validity_score,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "notes": list(self.notes),
            "score": self.score,
            "details": self.details,
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationResult:
        return cls(
            task_id=str(data.get("task_id", "")),
            rollout=data.get("rollout"),
            valid=bool(data.get("valid", data.get("passed", False))),
            validity_score=float(data.get("validity_score", data.get("score", 0.0)) or 0.0),
            checks_passed=int(data.get("checks_passed", 0) or 0),
            checks_total=int(data.get("checks_total", 0) or 0),
            notes=list(data.get("notes", []) or []),
            score=float(data.get("score", 0.0) or 0.0),
            details=dict(data.get("details", {}) or {}),
            passed=bool(data.get("passed", data.get("valid", False))),
        )


class Evaluator:
    """Evaluates self-improvement proposals."""

    def evaluate(self, *args: Any) -> EvaluationResult:
        """Evaluate a rollout (task + rollout) or a bare proposal dict."""
        if len(args) >= 2 and hasattr(args[1], "exit_code"):
            return self._evaluate_rollout(args[0], args[1])
        proposal = args[0] if args else {}
        if not isinstance(proposal, dict) and hasattr(proposal, "to_dict"):
            proposal = proposal.to_dict()
        if not isinstance(proposal, dict):
            proposal = {"proposal": str(proposal)}
        return EvaluationResult(
            score=0.0,
            details={"proposal": proposal.get("name", "unknown"), "measured": False},
            passed=False,
        )

    def _evaluate_rollout(self, task: Any, rollout: Any) -> EvaluationResult:
        """A rollout passes when its verifier exited 0 and it produced output.

        UNKNOWN stays UNKNOWN: a timeout or a policy block is not a pass, and
        a missing exit code is reported as such rather than guessed.
        """
        exit_code = getattr(rollout, "exit_code", None)
        error = getattr(rollout, "error", None)
        created = list(getattr(rollout, "created_files", []) or [])
        task_id = str(getattr(task, "id", "") or "")
        if error:
            return EvaluationResult(
                score=0.0, details={"task_id": task_id, "error": str(error), "measured": True}, passed=False
            )
        if exit_code is None:
            return EvaluationResult(
                task_id=task_id,
                rollout=rollout,
                score=0.0,
                notes=["no exit code recorded"],
                details={"task_id": task_id, "reason": "no exit code recorded", "measured": False},
                passed=False,
            )
        passed = exit_code == 0
        return EvaluationResult(
            task_id=task_id,
            rollout=rollout,
            score=1.0 if passed else 0.0,
            validity_score=1.0 if passed else 0.0,
            notes=[f"verifier exit_code={exit_code}"],
            details={
                "task_id": task_id,
                "exit_code": exit_code,
                "created_files": created,
                "measured": True,
            },
            passed=passed,
        )

    def compare(self, before: dict[str, Any], after: dict[str, Any]) -> EvaluationResult:
        """Compare before and after states.

        Without a measured rollout, no honest pass/fail is possible.
        Returns UNKNOWN (score=0.0, passed=False) with note.
        """
        return EvaluationResult(
            score=0.0,
            validity_score=0.0,
            details={"before": before, "after": after},
            notes=["compare: no measured rollout provided — UNKNOWN"],
            passed=False,
        )
