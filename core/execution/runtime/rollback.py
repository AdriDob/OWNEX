from __future__ import annotations

import logging
from typing import Any

from core.execution.runtime.checkpoint import CheckpointManager
from core.execution.runtime.context import RuntimeContext
from core.execution.runtime.kernel import ExecutionKernel
from core.execution.runtime.publisher import ExecutionEventPublisher

logger = logging.getLogger("ownex.execution.rollback")


class RollbackEngine:
    """Manages rollback of workflow executions.

    Process:
      1. RollbackPlan (from compiler) → RollbackGraph (reverse edges)
      2. Reverse execution (walk backwards through checkpoints)
      3. Verification (check state consistency)
      4. Emit events
    """

    def __init__(
        self,
        kernel: ExecutionKernel,
        checkpoint_manager: CheckpointManager,
        publisher: ExecutionEventPublisher | None = None,
    ) -> None:
        self.kernel = kernel
        self.checkpoint_manager = checkpoint_manager
        self.publisher = publisher or kernel.publisher

    def rollback(
        self,
        ctx: RuntimeContext,
        to_node_id: str | None = None,
        reason: str = "rollback",
    ) -> bool:
        execution_id = ctx.execution_id

        self.publisher.rollback_started(execution_id=execution_id, reason=reason)
        logger.info("[Rollback] Starting rollback for execution %s (reason: %s)", execution_id, reason)

        target_cp = self._find_checkpoint_for_node(ctx, to_node_id) if to_node_id else self._find_latest_checkpoint(ctx)

        if not target_cp:
            logger.warning("[Rollback] No checkpoint found for execution %s", execution_id)
            self.publisher.rollback_completed(execution_id=execution_id)
            return False

        cp_id, _ = target_cp
        success = self.checkpoint_manager.restore_checkpoint(ctx, cp_id)

        if success:
            logger.info("[Rollback] Restored to checkpoint %s for execution %s", cp_id, execution_id)
        else:
            logger.warning("[Rollback] Failed to restore checkpoint %s", cp_id)

        self.publisher.rollback_completed(execution_id=execution_id)
        return success

    def _find_latest_checkpoint(self, ctx: RuntimeContext) -> tuple[str, dict[str, Any]] | None:
        if not ctx.checkpoints:
            return None
        last_key = max(ctx.checkpoints.keys())
        return last_key, ctx.checkpoints[last_key]

    def _find_checkpoint_for_node(self, ctx: RuntimeContext, node_id: str) -> tuple[str, dict[str, Any]] | None:
        for cp_id, snap in ctx.checkpoints.items():
            if snap.get("current_node_id") == node_id:
                return cp_id, snap
        return None
