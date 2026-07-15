from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RollbackPlan:
    """Describes how to roll back if the workflow fails."""

    available: bool = False
    strategy: str = "none"  # none | restore | compensate
    checkpoint_nodes: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ExecutionPlan:
    """Compiled execution plan produced after validation.

    This sits between the Validator and the Compiler::

        Intent → Workflow → Validation → ExecutionPlan → Compiler → Runtime

    The plan contains resolved execution order, parallelism,
    capability availability, timing estimates, risks, and rollback info.
    The Runtime only consumes this plan — it never interprets YAML/JSON.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow_id: str = ""
    workflow_name: str = ""

    # ── Execution order ─────────────────────────────────────────
    execution_order: list[str] = field(default_factory=list)

    # ── Resolved dependencies ───────────────────────────────────
    dependencies: dict[str, list[str]] = field(default_factory=dict)

    # ── Parallelism groups ──────────────────────────────────────
    parallelism: list[list[str]] = field(default_factory=list)

    # ── Capability availability ─────────────────────────────────
    available_capabilities: dict[str, bool] = field(default_factory=dict)
    missing_capabilities: list[str] = field(default_factory=list)

    # ── Timing estimates ────────────────────────────────────────
    estimated_duration_ms: int = 0
    estimated_cost_usd: float = 0.0
    estimated_tokens: int = 0
    estimated_api_calls: int = 0

    # ── Risks ───────────────────────────────────────────────────
    risks: list[str] = field(default_factory=list)
    risk_score: float = 0.0  # 0.0 (safe) to 1.0 (very risky)

    # ── Rollback ────────────────────────────────────────────────
    rollback: RollbackPlan = field(default_factory=RollbackPlan)

    # ── Approvals ───────────────────────────────────────────────
    pending_approvals: list[str] = field(default_factory=list)

    # ── Validation score ────────────────────────────────────────
    validation_score: float = 100.0
    safe: bool = True

    # ── Metadata ────────────────────────────────────────────────
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "execution_order": self.execution_order,
            "dependencies": self.dependencies,
            "parallelism": self.parallelism,
            "available_capabilities": self.available_capabilities,
            "missing_capabilities": self.missing_capabilities,
            "estimated_duration_ms": self.estimated_duration_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "estimated_tokens": self.estimated_tokens,
            "estimated_api_calls": self.estimated_api_calls,
            "risks": self.risks,
            "risk_score": self.risk_score,
            "rollback": {
                "available": self.rollback.available,
                "strategy": self.rollback.strategy,
                "checkpoint_nodes": self.rollback.checkpoint_nodes,
                "description": self.rollback.description,
            },
            "pending_approvals": self.pending_approvals,
            "validation_score": self.validation_score,
            "safe": self.safe,
            "created_at": self.created_at.isoformat(),
        }


def build_execution_plan(
    workflow_id: str,
    workflow_name: str,
    node_ids: list[str],
    dependencies: dict[str, list[str]] | None = None,
    parallelism_groups: list[list[str]] | None = None,
) -> ExecutionPlan:
    """Convenience factory to create an ExecutionPlan from a workflow's validated structure."""
    return ExecutionPlan(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        execution_order=node_ids,
        dependencies=dependencies or {},
        parallelism=parallelism_groups or [],
    )
