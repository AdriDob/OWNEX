from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from core.execution.runtime.state_machine import NodeState, WorkflowState


@dataclass
class NodeRuntimeState:
    """Mutable state for a single node during execution."""

    node_id: str
    status: NodeState = NodeState.PENDING
    retry_count: int = 0
    started_at: float | None = None
    completed_at: float | None = None
    duration_ms: float = 0.0
    error: str | None = None
    output: dict[str, Any] = field(default_factory=dict)
    approval_id: str | None = None
    checkpoint_id: str | None = None


@dataclass
class ResourceLock:
    """A named resource lock acquired during execution."""

    resource_name: str
    workflow_id: str
    node_id: str
    acquired_at: float
    ttl_ms: int | None = None


@dataclass
class RuntimeMetrics:
    """Live metrics accumulating during execution."""

    cpu_ms: float = 0.0
    ram_mb: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    api_calls: int = 0
    bandwidth_bytes: int = 0
    cache_hits: int = 0
    retries: int = 0
    failures: int = 0
    approval_time_ms: float = 0.0
    human_time_ms: float = 0.0
    automation_time_ms: float = 0.0
    node_started_at: dict[str, float] = field(default_factory=dict)
    node_durations: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_ms": self.cpu_ms,
            "ram_mb": self.ram_mb,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "api_calls": self.api_calls,
            "bandwidth_bytes": self.bandwidth_bytes,
            "cache_hits": self.cache_hits,
            "retries": self.retries,
            "failures": self.failures,
            "approval_time_ms": self.approval_time_ms,
            "human_time_ms": self.human_time_ms,
            "automation_time_ms": self.automation_time_ms,
        }


class RuntimeContext:
    """Live mutable context for a single workflow execution.

    Holds:
    - variables (shared across nodes)
    - per-node state
    - resources / locks
    - live metrics
    - checkpoints
    - errors
    - pending approvals
    - timers (IDs registered with the VirtualClock)

    This is the single source of truth for a running execution.
    """

    def __init__(
        self,
        workflow_id: str,
        execution_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.workflow_id = workflow_id
        self.execution_id = execution_id or uuid.uuid4().hex[:24]
        self.correlation_id = correlation_id or uuid.uuid4().hex[:24]
        self.state: WorkflowState = WorkflowState.CREATED
        self.variables: dict[str, Any] = {}
        self.node_states: dict[str, NodeRuntimeState] = {}
        self.locks: dict[str, ResourceLock] = {}
        self.metrics: RuntimeMetrics = RuntimeMetrics()
        self.checkpoints: dict[str, dict[str, Any]] = {}
        self.errors: list[str] = []
        self.events: list[str] = []
        self.timer_ids: list[str] = []
        self.approvals: list[str] = []
        self.current_node_id: str | None = None
        self._lock = Lock()
        self.created_at: float = 0.0
        self.started_at: float | None = None
        self.completed_at: float | None = None
        self.updated_at: float = 0.0

    # ── Thread-safe mutations ─────────────────────────────────────

    def set_variable(self, key: str, value: Any) -> None:
        with self._lock:
            self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.variables.get(key, default)

    def set_node_state(self, node_id: str, status: NodeState) -> None:
        with self._lock:
            if node_id not in self.node_states:
                self.node_states[node_id] = NodeRuntimeState(node_id=node_id)
            self.node_states[node_id].status = status

    def get_node_state(self, node_id: str) -> NodeRuntimeState | None:
        with self._lock:
            return self.node_states.get(node_id)

    def add_error(self, error: str) -> None:
        with self._lock:
            self.errors.append(error)

    def add_event(self, event: str) -> None:
        with self._lock:
            self.events.append(event)

    def add_timer(self, timer_id: str) -> None:
        with self._lock:
            self.timer_ids.append(timer_id)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "workflow_id": self.workflow_id,
                "execution_id": self.execution_id,
                "correlation_id": self.correlation_id,
                "state": self.state.value,
                "variables": dict(self.variables),
                "node_states": {
                    nid: {
                        "status": ns.status.value,
                        "retry_count": ns.retry_count,
                        "error": ns.error,
                    }
                    for nid, ns in self.node_states.items()
                },
                "errors": list(self.errors),
                "current_node_id": self.current_node_id,
                "metrics": self.metrics.to_dict(),
            }

    def to_dict(self) -> dict[str, Any]:
        return self.snapshot()
