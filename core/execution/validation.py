from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.execution.models import Workflow

logger = logging.getLogger("orion.core.execution.validation")


@dataclass
class ValidationIssue:
    """A single finding produced by a validator."""

    type: str = "error"  # error | warning | suggestion
    code: str = ""
    message: str = ""
    node_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "details": self.details,
        }


@dataclass
class ValidationResult:
    """Output from a single validator."""

    validator_name: str = ""
    passed: bool = True
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    suggestions: list[ValidationIssue] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Compute component score: 100 minus penalties.

        - Each error: -15 points
        - Each warning: -5 points
        - Each suggestion: -2 points
        - Minimum: 0
        """
        penalty = len(self.errors) * 15 + len(self.warnings) * 5 + len(self.suggestions) * 2
        return max(0.0, 100.0 - float(penalty))

    def to_dict(self) -> dict[str, Any]:
        return {
            "validator_name": self.validator_name,
            "passed": self.passed,
            "score": self.score,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "suggestions": [s.to_dict() for s in self.suggestions],
        }


@dataclass
class ValidationReport:
    """Aggregated validation output for a complete workflow."""

    workflow_id: str = ""
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Overall score: average of all validator scores."""
        if not self.results:
            return 100.0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def error_count(self) -> int:
        return sum(len(r.errors) for r in self.results)

    @property
    def warning_count(self) -> int:
        return sum(len(r.warnings) for r in self.results)

    @property
    def suggestion_count(self) -> int:
        return sum(len(r.suggestions) for r in self.results)

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "passed": self.passed,
            "score": round(self.score, 1),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "suggestion_count": self.suggestion_count,
            "results": [r.to_dict() for r in self.results],
        }


class BaseValidator:
    """Base class for all validators.

    Subclasses implement ``validate(workflow)`` and return a ``ValidationResult``.
    """

    name: str = "base"

    def validate(self, workflow: Workflow) -> ValidationResult:
        raise NotImplementedError

    def _error(self, code: str, message: str, node_id: str | None = None, **details: Any) -> ValidationIssue:
        return ValidationIssue(type="error", code=code, message=message, node_id=node_id, details=details)

    def _warning(self, code: str, message: str, node_id: str | None = None, **details: Any) -> ValidationIssue:
        return ValidationIssue(type="warning", code=code, message=message, node_id=node_id, details=details)

    def _suggestion(self, code: str, message: str, node_id: str | None = None, **details: Any) -> ValidationIssue:
        return ValidationIssue(type="suggestion", code=code, message=message, node_id=node_id, details=details)


class ExecutionValidator:
    """Orchestrates all registered validators against a workflow.

    Usage::

        report = ExecutionValidator.run(workflow)
        if report.passed:
            compile_and_execute(workflow)
    """

    def __init__(self) -> None:
        self._validators: list[BaseValidator] = []

    def register(self, validator: BaseValidator) -> None:
        self._validators.append(validator)

    def register_all(self, *validators: BaseValidator) -> None:
        self._validators.extend(validators)

    def validate(self, workflow: Workflow) -> ValidationReport:
        report = ValidationReport(workflow_id=workflow.id)
        for validator in self._validators:
            try:
                result = validator.validate(workflow)
                report.results.append(result)
            except Exception as exc:
                logger.warning("Validator %s raised: %s", validator.name, exc)
                report.results.append(
                    ValidationResult(
                        validator_name=validator.name,
                        passed=False,
                        errors=[self._error("VALIDATOR_CRASH", f"Validator raised: {exc}")],
                    )
                )
        return report

    @staticmethod
    def _error(code: str, message: str, node_id: str | None = None) -> ValidationIssue:
        return ValidationIssue(type="error", code=code, message=message, node_id=node_id)

    @classmethod
    def run(cls, workflow: Workflow) -> ValidationReport:
        """Convenience: create default instance with all built-in validators and run."""
        validator = cls()
        _register_builtin_validators(validator)
        return validator.validate(workflow)


def _register_builtin_validators(validator: ExecutionValidator) -> None:
    """Register all built-in validators on an ExecutionValidator instance."""
    from core.execution.validators.capability import CapabilityValidator
    from core.execution.validators.dependency import DependencyValidator
    from core.execution.validators.documentation import DocumentationValidator
    from core.execution.validators.graph import GraphValidator
    from core.execution.validators.permission import PermissionValidator
    from core.execution.validators.resource import ResourceValidator
    from core.execution.validators.retry import RetryValidator
    from core.execution.validators.security import SecurityValidator
    from core.execution.validators.timeout import TimeoutValidator

    validator.register_all(
        GraphValidator(),
        CapabilityValidator(),
        PermissionValidator(),
        TimeoutValidator(),
        RetryValidator(),
        DependencyValidator(),
        SecurityValidator(),
        ResourceValidator(),
        DocumentationValidator(),
    )
