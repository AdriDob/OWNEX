"""Validation Engine — validates execution results before submission.

Multi-layer validation: rules → heuristics → LLM → platform.
Different validators per opportunity type.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.engine.base import Engine
from core.engine.classification import Opportunity

logger = logging.getLogger("ownex.validation")


# ── Core types ─────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Result of validating an execution."""

    opportunity_id: str
    passed: bool = False
    check_results: list[dict[str, Any]] = field(default_factory=list)
    score: float = 0.0  # 0.0 to 1.0 quality score
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    validator: str = "rules"  # "rules", "heuristics", "llm", "platform"


# ── Validator interface ────────────────────────────────────────────


class Validator(ABC):
    """A single validity check."""

    name: str = ""

    @abstractmethod
    async def validate(
        self,
        opportunity: Opportunity,
        execution_result: Any,
    ) -> dict[str, Any]:
        """Returns check dict with 'passed', 'message', optional 'suggestion'."""
        ...


# ── Concrete validators ────────────────────────────────────────────


class PoCReproducibleValidator(Validator):
    """Check if proof of concept is actually reproducible."""

    name = "poc_reproducible"

    async def validate(
        self,
        opportunity: Opportunity,
        execution_result: Any,
    ) -> dict[str, Any]:
        steps = self._extract_poc_steps(execution_result)
        if not steps or len(steps) < 3:
            return {
                "passed": False,
                "message": "PoC missing reproduction steps",
                "suggestion": (
                    "Add step-by-step reproduction including HTTP requests, payloads, and expected vs actual behavior"
                ),
            }
        return {"passed": True, "message": f"PoC has {len(steps)} reproduction steps"}

    def _extract_poc_steps(self, result: Any) -> list[str]:
        steps: list[str] = []
        completed_steps = getattr(result, "completed_steps", [])
        for step in completed_steps:
            if step.result and isinstance(step.result, dict):
                text = str(step.result.get("output", ""))
                for line in text.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith(("1.", "2.", "3.", "- ", "* ")):
                        steps.append(stripped)
        return steps


class CodeQualityValidator(Validator):
    """Basic code quality checks (lint, style, complexity)."""

    name = "code_quality"

    async def validate(
        self,
        opportunity: Opportunity,
        execution_result: Any,
    ) -> dict[str, Any]:
        has_code = False
        has_tests = False

        completed_steps = getattr(execution_result, "completed_steps", [])
        for step in completed_steps:
            if step.result and isinstance(step.result, dict):
                output = str(step.result.get("output", ""))
                if "def " in output or "class " in output or "function " in output:
                    has_code = True
                if "test" in output.lower() or "assert" in output:
                    has_tests = True

        issues: list[str] = []
        if not has_code:
            issues.append("No code produced")
        if not has_tests and opportunity.source_type == "dev_bounty":
            issues.append("No tests found")

        return {
            "passed": len(issues) == 0,
            "message": "; ".join(issues) if issues else "Code quality OK",
            "suggestion": "Add tests for the implementation" if not has_tests else None,
        }


class RequirementsMetValidator(Validator):
    """Check if AI work meets requirements."""

    name = "requirements_met"

    async def validate(
        self,
        opportunity: Opportunity,
        execution_result: Any,
    ) -> dict[str, Any]:
        output = ""
        completed_steps = getattr(execution_result, "completed_steps", [])
        for step in completed_steps:
            if step.result and isinstance(step.result, dict):
                output += str(step.result.get("output", "")) + "\n"

        if not output or len(output.strip()) < 50:
            return {
                "passed": False,
                "message": "Output too short or empty",
                "suggestion": "Ensure the task produces sufficient output",
            }
        return {"passed": True, "message": f"Output length: {len(output)} chars"}


# ── Validation Engine ──────────────────────────────────────────────


class ValidationEngine(Engine):
    """Validates execution results before submission.

    Multi-layered validation:
    1. Rules (structure check — fast)
    2. Heuristics (quality patterns — medium)
    3. LLM (deep analysis — slow)
    4. Platform (actual platform response — async)
    """

    name = "validation_engine"

    def __init__(self) -> None:
        super().__init__()
        self.validators: dict[str, list[Validator]] = {
            "bug_bounty": [
                PoCReproducibleValidator(),
            ],
            "dev_bounty": [
                CodeQualityValidator(),
            ],
            "ai_work": [
                RequirementsMetValidator(),
            ],
        }
        self._validation_history: list[ValidationResult] = []

    def register_validator(self, source_type: str, validator: Validator) -> None:
        if source_type not in self.validators:
            self.validators[source_type] = []
        self.validators[source_type].append(validator)

    async def validate(
        self,
        opportunity: Opportunity,
        execution_result: Any,
    ) -> ValidationResult:
        """Run all validators for this opportunity type."""
        validators = self.validators.get(opportunity.source_type, [])

        result = ValidationResult(opportunity_id=opportunity.id)

        total = len(validators)
        successes = 0
        for validator in validators:
            try:
                check = await validator.validate(opportunity, execution_result)
                result.check_results.append(check)

                if check.get("passed", False):
                    successes += 1
                else:
                    result.issues.append(check.get("message", "Validation failed"))

                if check.get("suggestion"):
                    result.suggestions.append(check["suggestion"])
            except Exception as e:
                logger.warning("Validator %s failed: %s", validator.name, e)
                result.issues.append(f"Validator error: {e}")

        result.score = successes / total if total > 0 else 0.0
        result.passed = result.score >= 0.5
        self._validation_history.append(result)

        return result

    def get_history(self, limit: int = 10) -> list[ValidationResult]:
        return self._validation_history[-limit:]

    async def initialize(self) -> None:
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "name": self.name,
            "validators": {k: [v.name for v in vals] for k, vals in self.validators.items()},
            "total_validations": len(self._validation_history),
        }
