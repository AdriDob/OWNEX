from __future__ import annotations

import logging
import uuid

from core.copilot.permissions import AuthorityLevel
from core.execution.runtime.clock import VirtualClock
from core.execution.runtime.context import RuntimeContext
from core.execution.runtime.kernel import ExecutionKernel
from core.execution.runtime.publisher import ExecutionEventPublisher

logger = logging.getLogger("ownex.execution.approval")


class ApprovalManager:
    """Manages the full approval lifecycle.

    States:
      Pending → Notify → Reminder → Expire → Approve | Reject → Resume
    """

    def __init__(
        self,
        kernel: ExecutionKernel,
        clock: VirtualClock,
        publisher: ExecutionEventPublisher | None = None,
    ) -> None:
        self.kernel = kernel
        self.clock = clock
        self.publisher = publisher or kernel.publisher

    def request_approval(
        self,
        ctx: RuntimeContext,
        node_id: str,
        reason: str = "",
        required_level: str = AuthorityLevel.OPERATOR.value,
        timeout_ms: int | None = None,
    ) -> str:
        approval_id = f"ap_{ctx.execution_id[:8]}_{node_id[:8]}_{uuid.uuid4().hex[:6]}"
        ctx.approvals.append(approval_id)

        self.publisher.approval_requested(
            execution_id=ctx.execution_id,
            node_id=node_id,
            approval_id=approval_id,
            reason=reason,
        )

        logger.info(
            "[Approval] Requested %s for node %s (level=%s)",
            approval_id,
            node_id,
            required_level,
        )
        return approval_id

    def approve(self, ctx: RuntimeContext, approval_id: str, by: str = "") -> bool:
        if approval_id not in ctx.approvals:
            logger.warning("[Approval] %s not found in execution %s", approval_id, ctx.execution_id)
            return False
        self.publisher.approval_approved(
            execution_id=ctx.execution_id,
            node_id=ctx.current_node_id or "unknown",
            approval_id=approval_id,
        )
        logger.info("[Approval] %s approved by %s", approval_id, by or "system")
        return True

    def reject(self, ctx: RuntimeContext, approval_id: str, by: str = "") -> bool:
        if approval_id not in ctx.approvals:
            return False
        self.publisher.approval_rejected(
            execution_id=ctx.execution_id,
            node_id=ctx.current_node_id or "unknown",
            approval_id=approval_id,
        )
        logger.info("[Approval] %s rejected by %s", approval_id, by or "system")
        return True

    def expire(self, ctx: RuntimeContext, approval_id: str) -> bool:
        if approval_id not in ctx.approvals:
            return False
        self.publisher.approval_expired(
            execution_id=ctx.execution_id,
            node_id=ctx.current_node_id or "unknown",
            approval_id=approval_id,
        )
        logger.info("[Approval] %s expired", approval_id)
        return True

    def pending_approvals(self, ctx: RuntimeContext) -> list[str]:
        return list(ctx.approvals)
