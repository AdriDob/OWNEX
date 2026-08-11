from __future__ import annotations

from enum import StrEnum


class NodeState(StrEnum):
    """Possible states for a single node during execution.

    Transitions:
      PENDING → READY → RUNNING → COMPLETED
                                         → FAILED → (optionally RETRYING → READY)
                                          → CANCELLED
               RUNNING → WAITING → RUNNING (e.g. waiting for approval)
               RUNNING → PAUSED → RUNNING
               PENDING → SKIPPED
               READY → SKIPPED
    """

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    RETRYING = "retrying"
    APPROVED = "approved"
    SKIPPED = "skipped"
    ROLLBACK = "rollback"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_NODE_TRANSITIONS: dict[NodeState, set[NodeState]] = {
    NodeState.PENDING: {NodeState.READY, NodeState.SKIPPED, NodeState.CANCELLED},
    NodeState.READY: {NodeState.RUNNING, NodeState.SKIPPED, NodeState.CANCELLED},
    NodeState.RUNNING: {
        NodeState.COMPLETED,
        NodeState.FAILED,
        NodeState.WAITING,
        NodeState.PAUSED,
        NodeState.CANCELLED,
    },
    NodeState.WAITING: {NodeState.RUNNING, NodeState.FAILED, NodeState.CANCELLED},
    NodeState.PAUSED: {NodeState.RUNNING, NodeState.CANCELLED},
    NodeState.RETRYING: {NodeState.READY, NodeState.FAILED, NodeState.CANCELLED},
    NodeState.APPROVED: {NodeState.READY, NodeState.RUNNING, NodeState.CANCELLED},
    NodeState.SKIPPED: set(),
    NodeState.ROLLBACK: {NodeState.COMPLETED, NodeState.FAILED},
    NodeState.COMPLETED: set(),
    NodeState.FAILED: {NodeState.RETRYING, NodeState.CANCELLED},
    NodeState.CANCELLED: set(),
}


class WorkflowState(StrEnum):
    """States for the entire workflow execution."""

    CREATED = "created"
    VALIDATED = "validated"
    COMPILED = "compiled"
    EXECUTING = "executing"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SIMULATING = "simulating"


_WORKFLOW_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.CREATED: {
        WorkflowState.VALIDATED,
        WorkflowState.COMPILED,
        WorkflowState.EXECUTING,
        WorkflowState.SIMULATING,
        WorkflowState.CANCELLED,
    },
    WorkflowState.VALIDATED: {WorkflowState.COMPILED, WorkflowState.CANCELLED},
    WorkflowState.COMPILED: {WorkflowState.EXECUTING, WorkflowState.SIMULATING, WorkflowState.CANCELLED},
    WorkflowState.EXECUTING: {
        WorkflowState.PAUSED,
        WorkflowState.WAITING_APPROVAL,
        WorkflowState.ROLLING_BACK,
        WorkflowState.FINISHED,
        WorkflowState.FAILED,
        WorkflowState.CANCELLED,
    },
    WorkflowState.PAUSED: {WorkflowState.EXECUTING, WorkflowState.CANCELLED},
    WorkflowState.WAITING_APPROVAL: {WorkflowState.EXECUTING, WorkflowState.ROLLING_BACK, WorkflowState.CANCELLED},
    WorkflowState.ROLLING_BACK: {WorkflowState.ROLLED_BACK, WorkflowState.FAILED, WorkflowState.CANCELLED},
    WorkflowState.ROLLED_BACK: {WorkflowState.FINISHED, WorkflowState.CANCELLED},
    WorkflowState.FINISHED: set(),
    WorkflowState.FAILED: set(),
    WorkflowState.CANCELLED: set(),
    WorkflowState.SIMULATING: {WorkflowState.FINISHED, WorkflowState.FAILED, WorkflowState.CANCELLED},
}


def validate_node_transition(current: NodeState, next_state: NodeState) -> bool:
    allowed = _NODE_TRANSITIONS.get(current, set())
    return next_state in allowed


def validate_workflow_transition(current: WorkflowState, next_state: WorkflowState) -> bool:
    allowed = _WORKFLOW_TRANSITIONS.get(current, set())
    return next_state in allowed


class TransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""


def enforce_node_transition(current: NodeState, next_state: NodeState) -> None:
    if not validate_node_transition(current, next_state):
        msg = f"Invalid node transition: {current.value} → {next_state.value}"
        raise TransitionError(msg)


def enforce_workflow_transition(current: WorkflowState, next_state: WorkflowState) -> None:
    if not validate_workflow_transition(current, next_state):
        msg = f"Invalid workflow transition: {current.value} → {next_state.value}"
        raise TransitionError(msg)
