"""Self-Healer Data Models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ProblemSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProblemCategory(StrEnum):
    HEALTH_DEGRADATION = "health_degradation"
    ERROR_SPIKE = "error_spike"
    PERFORMANCE_REGRESSION = "performance_regression"
    TEST_FAILURE = "test_failure"
    SLA_VIOLATION = "sla_violation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONFIG_DRIFT = "config_drift"
    DEPENDENCY_FAILURE = "dependency_failure"
    SECURITY_ANOMALY = "security_anomaly"
    UNKNOWN = "unknown"


class DiagnosisConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class FixStrategy(StrEnum):
    CONFIG_CHANGE = "config_change"
    CODE_PATCH = "code_patch"
    DEPENDENCY_UPDATE = "dependency_update"
    RESTART_SERVICE = "restart_service"
    ROLLBACK = "rollback"
    WORKAROUND = "workaround"
    MANUAL_INTERVENTION = "manual_intervention"


class DeploymentStatus(StrEnum):
    PENDING = "pending"
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    COMPLETED = "completed"


class ApprovalRequired(StrEnum):
    NONE = "none"
    LOW_RISK = "low_risk"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"


@dataclass(slots=True)
class Problem:
    id: str = field(default_factory=lambda: f"prob_{uuid.uuid4().hex[:12]}")
    category: ProblemCategory = ProblemCategory.UNKNOWN
    severity: ProblemSeverity = ProblemSeverity.MEDIUM
    title: str = ""
    description: str = ""
    source: str = "detector"
    metrics: dict[str, Any] = field(default_factory=dict)
    affected_components: list[str] = field(default_factory=list)
    first_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    occurrence_count: int = 1
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "metrics": self.metrics,
            "affected_components": self.affected_components,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "occurrence_count": self.occurrence_count,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class Diagnosis:
    id: str = field(default_factory=lambda: f"diag_{uuid.uuid4().hex[:12]}")
    problem_id: str = ""
    root_cause: str = ""
    contributing_factors: list[str] = field(default_factory=list)
    confidence: DiagnosisConfidence = DiagnosisConfidence.MEDIUM
    evidence: list[str] = field(default_factory=list)
    reasoning: str = ""
    suggested_strategy: FixStrategy = FixStrategy.MANUAL_INTERVENTION
    estimated_effort_hours: float = 0.0
    risk_level: ProblemSeverity = ProblemSeverity.MEDIUM
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    analyzer_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "problem_id": self.problem_id,
            "root_cause": self.root_cause,
            "contributing_factors": self.contributing_factors,
            "confidence": self.confidence.value,
            "evidence": self.evidence,
            "reasoning": self.reasoning,
            "suggested_strategy": self.suggested_strategy.value,
            "estimated_effort_hours": self.estimated_effort_hours,
            "risk_level": self.risk_level.value,
            "created_at": self.created_at.isoformat(),
            "analyzer_version": self.analyzer_version,
        }


@dataclass(slots=True)
class FixPlan:
    id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    diagnosis_id: str = ""
    strategy: FixStrategy = FixStrategy.MANUAL_INTERVENTION
    description: str = ""
    steps: list[str] = field(default_factory=list)
    files_to_modify: list[str] = field(default_factory=list)
    config_changes: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    tests_to_add: list[str] = field(default_factory=list)
    rollback_plan: str = ""
    approval_required: ApprovalRequired = ApprovalRequired.HIGH_RISK
    estimated_duration_minutes: int = 30
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: str = "self_healer"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "diagnosis_id": self.diagnosis_id,
            "strategy": self.strategy.value,
            "description": self.description,
            "steps": self.steps,
            "files_to_modify": self.files_to_modify,
            "config_changes": self.config_changes,
            "dependencies": self.dependencies,
            "tests_to_add": self.tests_to_add,
            "rollback_plan": self.rollback_plan,
            "approval_required": self.approval_required.value,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }


@dataclass(slots=True)
class Patch:
    id: str = field(default_factory=lambda: f"patch_{uuid.uuid4().hex[:12]}")
    plan_id: str = ""
    diff: str = ""
    files_changed: list[str] = field(default_factory=list)
    tests_generated: list[str] = field(default_factory=list)
    validation_results: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    applied_at: datetime | None = None
    is_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "diff": self.diff,
            "files_changed": self.files_changed,
            "tests_generated": self.tests_generated,
            "validation_results": self.validation_results,
            "created_at": self.created_at.isoformat(),
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "is_applied": self.is_applied,
        }


@dataclass(slots=True)
class Deployment:
    id: str = field(default_factory=lambda: f"deploy_{uuid.uuid4().hex[:12]}")
    patch_id: str = ""
    status: DeploymentStatus = DeploymentStatus.PENDING
    environment: str = "staging"
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    rolled_back_at: datetime | None = None
    health_checks: dict[str, bool] = field(default_factory=dict)
    metrics_before: dict[str, float] = field(default_factory=dict)
    metrics_after: dict[str, float] = field(default_factory=dict)
    rollback_triggered: bool = False
    rollback_reason: str = ""
    version_backup_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "patch_id": self.patch_id,
            "status": self.status.value,
            "environment": self.environment,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rolled_back_at": self.rolled_back_at.isoformat() if self.rolled_back_at else None,
            "health_checks": self.health_checks,
            "metrics_before": self.metrics_before,
            "metrics_after": self.metrics_after,
            "rollback_triggered": self.rollback_triggered,
            "rollback_reason": self.rollback_reason,
            "version_backup_id": self.version_backup_id,
        }


@dataclass(slots=True)
class HealerConfig:
    enabled: bool = True
    scan_interval_minutes: int = 15
    max_concurrent_fixes: int = 2
    auto_approve_low_risk: bool = True
    require_approval_for: list[ApprovalRequired] = field(
        default_factory=lambda: [ApprovalRequired.HIGH_RISK, ApprovalRequired.CRITICAL]
    )
    excluded_paths: list[str] = field(
        default_factory=lambda: [
            "core/",
            "cores/security/",
            "cores/license/",
            "cores/identity_vault.py",
            "cores/vault_crypto.py",
            "cores/auth/",
        ]
    )
    protected_branches: list[str] = field(default_factory=lambda: ["main", "master", "release/*"])
    max_rollback_time_minutes: int = 30
    health_check_timeout_seconds: int = 60
    canary_duration_minutes: int = 10
    learning_enabled: bool = True
    max_learning_entries: int = 10000
