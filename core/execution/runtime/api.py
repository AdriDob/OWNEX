from __future__ import annotations

import logging
from typing import Any

from core.execution.runtime.kernel import ExecutionKernel
from core.execution.runtime.state_machine import WorkflowState

logger = logging.getLogger("ownex.execution.api")


class RuntimeAPI:
    """High-level API for managing workflow executions.

    This is the public interface. External callers (REST, CLI, COPILOT)
    use this to interact with the Runtime.
    """

    def __init__(self, kernel: ExecutionKernel) -> None:
        self.kernel = kernel

    def start_execution(
        self,
        workflow_id: str,
        execution_id: str | None = None,
        correlation_id: str | None = None,
    ) -> str:
        ctx = self.kernel.create_context(
            workflow_id=workflow_id,
            execution_id=execution_id,
            correlation_id=correlation_id,
        )
        self.kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        self.kernel.publisher.execution_started(ctx.execution_id, workflow_id)
        logger.info("[API] Execution started: %s (workflow %s)", ctx.execution_id, workflow_id)
        return ctx.execution_id

    def pause_execution(self, execution_id: str, reason: str = "") -> bool:
        ok = self.kernel.set_workflow_state(execution_id, WorkflowState.PAUSED)
        if ok:
            self.kernel.publisher.execution_paused(execution_id, reason)
        return ok

    def resume_execution(self, execution_id: str) -> bool:
        ok = self.kernel.set_workflow_state(execution_id, WorkflowState.EXECUTING)
        if ok:
            self.kernel.publisher.execution_resumed(execution_id)
        return ok

    def cancel_execution(self, execution_id: str, reason: str = "") -> bool:
        ok = self.kernel.set_workflow_state(execution_id, WorkflowState.CANCELLED)
        if ok:
            self.kernel.publisher.execution_cancelled(execution_id, reason)
            self.kernel.publisher.workflow_cancelled(
                workflow_id="",
                execution_id=execution_id,
                reason=reason,
            )
        return ok

    def get_status(self, execution_id: str) -> dict[str, Any] | None:
        ctx = self.kernel.get_context(execution_id)
        if not ctx:
            return None
        wf_state = self.kernel.get_workflow_state(execution_id)
        return {
            "execution_id": ctx.execution_id,
            "workflow_id": ctx.workflow_id,
            "state": wf_state.value if wf_state else "unknown",
            "current_node_id": ctx.current_node_id,
            "error": ctx.errors[-1] if ctx.errors else None,
            "node_count": len(ctx.node_states),
            "duration_ms": (self.kernel.clock.now() - ctx.created_at) * 1000 if ctx.created_at else 0.0,
        }

    def get_metrics(self, execution_id: str) -> dict[str, Any] | None:
        ctx = self.kernel.get_context(execution_id)
        if not ctx:
            return None
        return ctx.metrics.to_dict()

    def get_journal(self, execution_id: str) -> list[dict[str, Any]] | None:
        # Try in-memory journal first (fast path during active execution)
        journal = self.kernel.get_journal(execution_id)
        if journal:
            return journal.to_dict()
        # Fall back to EventStore for persisted entries (survives restart)
        try:
            from cores.events.store import get_event_store

            entries = get_event_store().get_journal_entries(execution_id)
            return entries if entries else None
        except Exception:
            return None
