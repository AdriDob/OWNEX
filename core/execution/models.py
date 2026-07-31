from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ExecutionState(str, Enum):
    """Lifecycle state of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class ApprovalStatus(str, Enum):
    """Outcome of a human approval gate."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class NodeResult:
    """Output produced by a single node execution."""

    node_id: str
    status: ExecutionState
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    retry_count: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


@dataclass
class Edge:
    """A directed connection between two workflow nodes."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_id: str = ""
    target_id: str = ""
    condition: str | None = None
    label: str | None = None


@dataclass
class Node:
    """A single step in a workflow graph.

    Each node references a PrimitiveType and carries
    type-specific configuration inside ``config``.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: str = ""
    label: str = ""
    description: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    input_mapping: dict[str, str] = field(default_factory=dict)
    output_mapping: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timeout_ms: int | None = None


@dataclass
class Workflow:
    """A directed graph of nodes and edges that defines an executable process.

    This is the **definition** (blueprint). An execution is created from it.
    The graph must be acyclic and fully connected (validated by the Validator).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:24])
    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "description": n.description,
                    "config": n.config,
                    "input_mapping": n.input_mapping,
                    "output_mapping": n.output_mapping,
                    "metadata": n.metadata,
                    "timeout_ms": n.timeout_ms,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "condition": e.condition,
                    "label": e.label,
                }
                for e in self.edges
            ],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ExecutionContext:
    """Live runtime state for a single workflow execution.

    Carries the shared variable store, current position,
    node result history, and correlation ID for tracing.
    """

    workflow_id: str
    execution_id: str
    correlation_id: str
    state: ExecutionState = ExecutionState.PENDING
    current_node_id: str | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    history: list[NodeResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "state": self.state.value,
            "current_node_id": self.current_node_id,
            "variables": self.variables,
            "history": [
                {
                    "node_id": r.node_id,
                    "status": r.status.value,
                    "output": r.output,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                    "retry_count": r.retry_count,
                }
                for r in self.history
            ],
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error": self.error,
        }


@dataclass
class ExecutionResult:
    """Final output produced when a workflow execution completes."""

    execution_id: str
    workflow_id: str
    status: ExecutionState = ExecutionState.PENDING
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    node_count: int = 0
    retry_total: int = 0
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Checkpoint:
    """Snapshot of an execution context at a specific node.

    Enables rollback: the runtime can restore variables and
    resume from the checkpoint's node position.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    execution_id: str = ""
    node_id: str = ""
    label: str = ""
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Approval:
    """A human approval gate attached to a specific node execution.

    When a node type is ``primitive_type = "approval"``, the runtime
    pauses and waits for a human to approve or reject.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    execution_id: str = ""
    node_id: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: str = ""
    responded_by: str | None = None
    reason: str = ""
    response_notes: str | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    responded_at: datetime | None = None
    timeout_ms: int | None = None
