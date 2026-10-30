from __future__ import annotations

import logging
from typing import Any

from cores.events.types import EventEnvelope, Events

logger = logging.getLogger("ownex.execution.publisher")


class ExecutionEventPublisher:
    """Typed publisher for all execution-related events.

    Never call the EventBus directly from runtime code.
    Always go through this publisher so events are consistent.
    """

    def __init__(self, publish_fn: Any = None) -> None:
        """Optionally inject an EventBus publish function.

        If not provided, events are logged but not sent.
        """
        self._publish = publish_fn

    def bind(self, publish_fn: Any) -> None:
        self._publish = publish_fn

    # ── Workflow lifecycle ────────────────────────────────────────

    def workflow_started(self, workflow_id: str, execution_id: str, correlation_id: str) -> None:
        self._emit(
            Events.EXECUTION_WORKFLOW_STARTED,
            {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "correlation_id": correlation_id,
            },
        )

    def workflow_completed(self, workflow_id: str, execution_id: str, result: dict[str, Any]) -> None:
        self._emit(
            Events.EXECUTION_WORKFLOW_COMPLETED,
            {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "result": result,
            },
        )

    def workflow_failed(self, workflow_id: str, execution_id: str, error: str) -> None:
        self._emit(
            Events.EXECUTION_WORKFLOW_FAILED,
            {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "error": error,
            },
        )

    def workflow_cancelled(self, workflow_id: str, execution_id: str, reason: str) -> None:
        self._emit(
            Events.EXECUTION_WORKFLOW_CANCELLED,
            {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "reason": reason,
            },
        )

    # ── Execution lifecycle ───────────────────────────────────────

    def execution_started(self, execution_id: str, workflow_id: str) -> None:
        self._emit(
            Events.EXECUTION_STARTED,
            {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
            },
        )

    def execution_paused(self, execution_id: str, reason: str = "") -> None:
        self._emit(
            Events.EXECUTION_PAUSED,
            {
                "execution_id": execution_id,
                "reason": reason,
            },
        )

    def execution_resumed(self, execution_id: str) -> None:
        self._emit(
            Events.EXECUTION_RESUMED,
            {
                "execution_id": execution_id,
            },
        )

    def execution_completed(self, execution_id: str, result: dict[str, Any]) -> None:
        self._emit(
            Events.EXECUTION_COMPLETED,
            {
                "execution_id": execution_id,
                "result": result,
            },
        )

    def execution_failed(self, execution_id: str, error: str) -> None:
        self._emit(
            Events.EXECUTION_FAILED,
            {
                "execution_id": execution_id,
                "error": error,
            },
        )

    def execution_cancelled(self, execution_id: str, reason: str) -> None:
        self._emit(
            Events.EXECUTION_CANCELLED,
            {
                "execution_id": execution_id,
                "reason": reason,
            },
        )

    # ── Node lifecycle ────────────────────────────────────────────

    def node_started(self, execution_id: str, node_id: str, node_type: str) -> None:
        self._emit(
            Events.EXECUTION_NODE_STARTED,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "node_type": node_type,
            },
        )

    def node_completed(self, execution_id: str, node_id: str, output: dict[str, Any]) -> None:
        self._emit(
            Events.EXECUTION_NODE_COMPLETED,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "output": output,
            },
        )

    def node_failed(self, execution_id: str, node_id: str, error: str, retry_count: int = 0) -> None:
        self._emit(
            Events.EXECUTION_NODE_FAILED,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "error": error,
                "retry_count": retry_count,
            },
        )

    def node_retrying(self, execution_id: str, node_id: str, attempt: int, max_retries: int) -> None:
        self._emit(
            Events.EXECUTION_NODE_RETRYING,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "attempt": attempt,
                "max_retries": max_retries,
            },
        )

    # ── Approval events ───────────────────────────────────────────

    def approval_requested(self, execution_id: str, node_id: str, approval_id: str, reason: str) -> None:
        self._emit(
            Events.EXECUTION_APPROVAL_REQUESTED,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "approval_id": approval_id,
                "reason": reason,
            },
        )

    def approval_approved(self, execution_id: str, node_id: str, approval_id: str) -> None:
        self._emit(
            Events.EXECUTION_APPROVAL_APPROVED,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "approval_id": approval_id,
            },
        )

    def approval_rejected(self, execution_id: str, node_id: str, approval_id: str) -> None:
        self._emit(
            Events.EXECUTION_APPROVAL_REJECTED,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "approval_id": approval_id,
            },
        )

    def approval_expired(self, execution_id: str, node_id: str, approval_id: str) -> None:
        self._emit(
            Events.EXECUTION_APPROVAL_EXPIRED,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "approval_id": approval_id,
            },
        )

    # ── Checkpoint events ─────────────────────────────────────────

    def checkpoint_saved(self, execution_id: str, node_id: str, checkpoint_id: str) -> None:
        self._emit(
            Events.EXECUTION_CHECKPOINT_SAVED,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "checkpoint_id": checkpoint_id,
            },
        )

    def checkpoint_restored(self, execution_id: str, node_id: str, checkpoint_id: str) -> None:
        self._emit(
            Events.EXECUTION_CHECKPOINT_RESTORED,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "checkpoint_id": checkpoint_id,
            },
        )

    # ── Rollback events ───────────────────────────────────────────

    def rollback_started(self, execution_id: str, reason: str) -> None:
        self._emit(
            Events.EXECUTION_ROLLBACK_STARTED,
            {
                "execution_id": execution_id,
                "reason": reason,
            },
        )

    def rollback_completed(self, execution_id: str) -> None:
        self._emit(
            Events.EXECUTION_ROLLBACK_COMPLETED,
            {
                "execution_id": execution_id,
            },
        )

    # ── Journal events ────────────────────────────────────────────

    def journal_entry(self, execution_id: str, node_id: str, node_type: str, entry: dict[str, Any]) -> None:
        """Publish a journal entry — the rich record for Time Machine replay."""
        self._emit(
            Events.EXECUTION_JOURNAL_ENTRY,
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "node_type": node_type,
                **entry,
            },
        )

    # ── Metrics events ────────────────────────────────────────────

    def metrics_collected(self, execution_id: str, metrics: dict[str, Any]) -> None:
        self._emit(
            Events.EXECUTION_METRICS_COLLECTED,
            {
                "execution_id": execution_id,
                "metrics": metrics,
            },
        )

    # ── Internal ──────────────────────────────────────────────────

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        envelope = EventEnvelope.create(
            event_type=event_type,
            source="execution.runtime",
            payload=data,
        )
        if self._publish:
            try:
                self._publish(envelope)
            except Exception as exc:
                logger.warning("Failed to publish event %s: %s", event_type, exc)
        else:
            logger.debug("[Publisher] %s %s", event_type, data)
