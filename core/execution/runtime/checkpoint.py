from __future__ import annotations

import logging
from typing import Any

from core.execution.runtime.context import RuntimeContext
from core.execution.runtime.kernel import ExecutionKernel
from core.execution.runtime.publisher import ExecutionEventPublisher
from core.execution.runtime.state_machine import NodeState

logger = logging.getLogger("cateye.execution.checkpoint")


class CheckpointManager:
    """Manages execution snapshots for resume, rollback, clone, and replay.

    Every N nodes, a full snapshot of the RuntimeContext is saved.
    The snapshot includes variables, node states, metrics, and errors.
    """

    def __init__(
        self,
        kernel: ExecutionKernel,
        publisher: ExecutionEventPublisher | None = None,
        snapshot_interval: int = 5,
    ) -> None:
        self.kernel = kernel
        self.publisher = publisher or kernel.publisher
        self._snapshot_interval = snapshot_interval
        self._node_counter: dict[str, int] = {}

    def should_checkpoint(self, execution_id: str) -> bool:
        count = self._node_counter.get(execution_id, 0)
        return count > 0 and count % self._snapshot_interval == 0

    def increment(self, execution_id: str) -> None:
        self._node_counter[execution_id] = self._node_counter.get(execution_id, 0) + 1

    def save_checkpoint(
        self,
        ctx: RuntimeContext,
        node_id: str,
        label: str = "",
    ) -> str:
        cp_id = f"cp_{ctx.execution_id[:8]}_{node_id[:8]}_{self._node_counter.get(ctx.execution_id, 0)}"
        ctx.current_node_id = node_id
        snapshot = ctx.snapshot()
        ctx.checkpoints[cp_id] = snapshot

        eid = ctx.execution_id
        self.kernel.set_node_state(eid, node_id, NodeState.READY)
        self.kernel.set_node_state(eid, node_id, NodeState.RUNNING)
        self.kernel.set_node_state(eid, node_id, NodeState.COMPLETED)
        self.publisher.checkpoint_saved(
            execution_id=ctx.execution_id,
            node_id=node_id,
            checkpoint_id=cp_id,
        )

        logger.debug("[Checkpoint] Saved %s for node %s (execution %s)", cp_id, node_id, ctx.execution_id)
        return cp_id

    def restore_checkpoint(
        self,
        ctx: RuntimeContext,
        checkpoint_id: str,
    ) -> bool:
        snapshot = ctx.checkpoints.get(checkpoint_id)
        if not snapshot:
            logger.warning("[Checkpoint] %s not found for execution %s", checkpoint_id, ctx.execution_id)
            return False

        ctx.variables = dict(snapshot.get("variables", {}))
        ctx.state = snapshot.get("state", ctx.state)
        ctx.current_node_id = snapshot.get("current_node_id")
        ctx.errors = list(snapshot.get("errors", []))

        self.publisher.checkpoint_restored(
            execution_id=ctx.execution_id,
            node_id=ctx.current_node_id or "unknown",
            checkpoint_id=checkpoint_id,
        )

        logger.info("[Checkpoint] Restored %s for execution %s", checkpoint_id, ctx.execution_id)
        return True

    def list_checkpoints(self, ctx: RuntimeContext) -> list[dict[str, Any]]:
        return [
            {
                "id": cp_id,
                "node_id": snap.get("current_node_id"),
                "state": snap.get("state"),
            }
            for cp_id, snap in ctx.checkpoints.items()
        ]

    def clear_checkpoints(self, ctx: RuntimeContext) -> None:
        ctx.checkpoints.clear()
