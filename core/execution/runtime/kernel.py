from __future__ import annotations

import logging
from typing import Any

from core.execution.runtime.clock import VirtualClock
from core.execution.runtime.context import RuntimeContext
from core.execution.runtime.journal import ExecutionJournal
from core.execution.runtime.publisher import ExecutionEventPublisher
from core.execution.runtime.state_machine import (
    NodeState,
    WorkflowState,
    enforce_node_transition,
    enforce_workflow_transition,
)

logger = logging.getLogger("cateye.execution.kernel")


class ExecutionKernel:
    """Tiny, stable core of the Execution Platform.

    Orchestrates:
    - RuntimeContext (live mutable state)
    - VirtualClock (deterministic time)
    - State Machine (node + workflow transitions)
    - ExecutionJournal (persistent log)
    - EventPublisher (typed events)

    The kernel enforces transitions, updates context, journals
    every step, and publishes events. It does NOT execute
    capabilities or decide scheduling — those are service-layer concerns.
    """

    def __init__(
        self,
        clock: VirtualClock | None = None,
        publisher: ExecutionEventPublisher | None = None,
    ) -> None:
        self.clock = clock or VirtualClock()
        self.publisher = publisher or ExecutionEventPublisher()
        self._contexts: dict[str, RuntimeContext] = {}
        self._journals: dict[str, ExecutionJournal] = {}

    # ── Context lifecycle ─────────────────────────────────────────

    def create_context(
        self,
        workflow_id: str,
        execution_id: str | None = None,
        correlation_id: str | None = None,
    ) -> RuntimeContext:
        ctx = RuntimeContext(
            workflow_id=workflow_id,
            execution_id=execution_id,
            correlation_id=correlation_id,
        )
        ctx.created_at = self.clock.now()
        self._contexts[ctx.execution_id] = ctx
        journal = ExecutionJournal(
            execution_id=ctx.execution_id,
            workflow_id=workflow_id,
            correlation_id=ctx.correlation_id,
        )
        self._journals[ctx.execution_id] = journal
        return ctx

    def get_context(self, execution_id: str) -> RuntimeContext | None:
        return self._contexts.get(execution_id)

    def get_journal(self, execution_id: str) -> ExecutionJournal | None:
        return self._journals.get(execution_id)

    def has_context(self, execution_id: str) -> bool:
        return execution_id in self._contexts

    # ── Workflow transitions ──────────────────────────────────────

    def set_workflow_state(self, execution_id: str, new_state: WorkflowState) -> bool:
        ctx = self._contexts.get(execution_id)
        if not ctx:
            return False
        try:
            enforce_workflow_transition(ctx.state, new_state)
        except ValueError as exc:
            logger.warning("Invalid workflow transition %s -> %s: %s", ctx.state.value, new_state.value, exc)
            return False
        ctx.state = new_state
        ctx.updated_at = self.clock.now()
        return True

    def get_workflow_state(self, execution_id: str) -> WorkflowState | None:
        ctx = self._contexts.get(execution_id)
        if not ctx:
            return None
        return ctx.state

    # ── Node transitions ──────────────────────────────────────────

    def set_node_state(self, execution_id: str, node_id: str, new_state: NodeState) -> bool:
        ctx = self._contexts.get(execution_id)
        if not ctx:
            return False
        current_state = NodeState.PENDING
        ns = ctx.get_node_state(node_id)
        if ns:
            current_state = ns.status
        try:
            enforce_node_transition(current_state, new_state)
        except ValueError as exc:
            logger.warning(
                "Invalid node transition %s -> %s for node %s: %s",
                current_state.value,
                new_state.value,
                node_id,
                exc,
            )
            return False
        ctx.set_node_state(node_id, new_state)
        ns = ctx.get_node_state(node_id)
        if ns:
            if new_state in (NodeState.RUNNING, NodeState.RETRYING):
                ns.started_at = self.clock.now()
            if new_state in (NodeState.COMPLETED, NodeState.FAILED, NodeState.CANCELLED):
                ns.completed_at = self.clock.now()
                if ns.started_at:
                    ns.duration_ms = (ns.completed_at - ns.started_at) * 1000.0
        return True

    def get_node_state(self, execution_id: str, node_id: str) -> NodeState | None:
        ctx = self._contexts.get(execution_id)
        if not ctx:
            return None
        ns = ctx.get_node_state(node_id)
        if not ns:
            return None
        return ns.status

    # ── Journal helpers ───────────────────────────────────────────

    def journal_record(
        self,
        execution_id: str,
        node_id: str,
        node_type: str,
        **kwargs: Any,
    ) -> None:
        journal = self._journals.get(execution_id)
        if not journal:
            return
        journal.create_entry(
            node_id=node_id,
            node_type=node_type,
            timestamp=self.clock.now(),
            **kwargs,
        )

    # ── Variable helpers ──────────────────────────────────────────

    def set_variable(self, execution_id: str, key: str, value: Any) -> None:
        ctx = self._contexts.get(execution_id)
        if ctx:
            ctx.set_variable(key, value)

    def get_variable(self, execution_id: str, key: str, default: Any = None) -> Any:
        ctx = self._contexts.get(execution_id)
        if not ctx:
            return default
        return ctx.get_variable(key, default)

    # ── Cleanup ───────────────────────────────────────────────────

    def remove_context(self, execution_id: str) -> None:
        self._contexts.pop(execution_id, None)
        self._journals.pop(execution_id, None)

    def clear(self) -> None:
        self._contexts.clear()
        self._journals.clear()
