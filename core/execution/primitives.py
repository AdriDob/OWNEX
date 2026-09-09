from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.copilot.permissions import AuthorityLevel


class PrimitiveType(StrEnum):
    """Universal primitive node types for building workflows.

    Every workflow is composed of these atoms.
    No domain-specific knowledge (CATEYE, ATLAS, etc.) exists here.
    """

    START = "start"
    TRIGGER = "trigger"
    CONDITION = "condition"
    DECISION = "decision"
    CAPABILITY = "capability"
    WAIT = "wait"
    DELAY = "delay"
    RETRY = "retry"
    TIMEOUT = "timeout"
    PARALLEL = "parallel"
    LOOP = "loop"
    PERSIST = "persist"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    CHECKPOINT = "checkpoint"
    ROLLBACK = "rollback"
    END = "end"


# ── Config dataclasses for each primitive ─────────────────────────


@dataclass
class StartConfig:
    """Entry point of a workflow. Carries initial context."""

    initial_variables: dict[str, Any] = field(default_factory=dict)
    label: str = "Start"


@dataclass
class TriggerConfig:
    """Wait for an external event to arrive before proceeding.

    The node stays blocked until an event matching ``event_type``
    is published on the Event Bus, or until ``timeout_ms`` elapses.
    """

    event_type: str = ""
    timeout_ms: int | None = None
    payload_filter: dict[str, Any] | None = None


@dataclass
class ConditionConfig:
    """Branching: evaluate an expression and follow true/false edges.

    The ``expression`` is a Python expression evaluated against
    the execution context variables.
    """

    expression: str = ""
    true_target: str | None = None
    false_target: str | None = None


@dataclass
class DecisionConfig:
    """Multi-branch decision delegated to an external reasoner.

    ``model`` identifies the decider (e.g. ``copilot``, ``llm``, ``rule``).
    The model receives ``prompt`` and context, and returns a choice.
    """

    model: str = "copilot"
    prompt: str = ""
    options: list[str] = field(default_factory=list)
    timeout_ms: int | None = 30000


@dataclass
class CapabilityConfig:
    """Invoke a registered capability from the Capability Registry.

    The capability receives ``params`` and must respect ``timeout_ms``.
    If ``retry_count > 0`` the runtime will re-attempt on failure.
    """

    capability: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    timeout_ms: int | None = 60000
    retry_count: int = 0
    retry_delay_ms: int = 1000
    fail_on_error: bool = True


@dataclass
class WaitConfig:
    """Pause execution for a fixed duration."""

    duration_ms: int = 1000


@dataclass
class DelayConfig:
    """Insert a delay between two steps (similar to wait but
    explicitly used between nodes for pacing)."""

    duration_ms: int = 1000


@dataclass
class RetryConfig:
    """Wrap a subgraph with retry logic.

    If the subgraph fails, re-execute it up to ``max_retries``
    times with exponential backoff.
    """

    max_retries: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 60000
    backoff_multiplier: float = 2.0
    retryable_errors: list[str] | None = None


@dataclass
class TimeoutConfig:
    """Enforce a maximum duration for a subgraph.

    If the subgraph does not complete within ``duration_ms``,
    the node fails with a timeout error.
    """

    duration_ms: int = 30000


@dataclass
class ParallelConfig:
    """Execute multiple branches concurrently.

    ``branches`` lists the first node id of each parallel path.
    The node completes when all branches finish (join).
    """

    branches: list[str] = field(default_factory=list)
    max_concurrency: int = 0  # 0 = unlimited


@dataclass
class LoopConfig:
    """Iterate over a list of items from the execution context.

    ``iteration_input`` is the context variable name holding the list.
    ``body_start`` is the first node id of the loop body.
    After the body completes (hits the END node), the next item is processed.
    """

    iteration_input: str = ""
    body_start: str = ""
    max_iterations: int = 100
    output_variable: str = "loop_results"


@dataclass
class ApprovalConfig:
    """Wait for human approval before proceeding.

    ``required_level`` maps to COPILOT authority levels.
    If ``timeout_ms`` is set, the approval expires after that duration.
    """

    required_level: str = AuthorityLevel.OPERATOR.value
    timeout_ms: int | None = None
    reason: str = ""
    notification_channels: list[str] | None = None


@dataclass
class NotificationConfig:
    """Send a notification through the configured channel."""

    channel: str = "default"
    title: str = ""
    body: str = ""
    level: str = "info"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckpointConfig:
    """Save a snapshot of the execution context at this point.

    ``frequency`` controls when a snapshot is taken:
    - ``always``: every time this node is reached
    - ``once``: only the first time
    """

    frequency: str = "always"
    label: str = ""


@dataclass
class RollbackConfig:
    """Restore execution context to a previous checkpoint.

    If ``to_checkpoint`` is set, roll back to that specific
    checkpoint node. Otherwise, roll back to the nearest one.
    """

    to_checkpoint: str | None = None
    strategy: str = "restore"  # restore | restart | skip
