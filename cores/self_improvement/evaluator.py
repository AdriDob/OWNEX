"""Evaluator — Minimal stub for self-improvement evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationResult:
    """Result of an evaluation."""

    score: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    passed: bool = False


class Evaluator:
    """Evaluates self-improvement proposals."""

    def evaluate(self, proposal: dict[str, Any]) -> EvaluationResult:
        """Evaluate a proposal."""
        return EvaluationResult(
            score=0.5,
            details={"proposal": proposal.get("name", "unknown")},
            passed=True,
        )

    def compare(self, before: dict[str, Any], after: dict[str, Any]) -> EvaluationResult:
        """Compare before and after states."""
        return EvaluationResult(
            score=0.5,
            details={"before": before, "after": after},
            passed=True,
        )
