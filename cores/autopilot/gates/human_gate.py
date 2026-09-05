"""Human Gate System - Minimal human intervention gates for critical decisions."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from cores.autopilot.config.autopilot_config import AutopilotConfig

logger = logging.getLogger(__name__)


class GateType(StrEnum):
    DELIVERY_APPROVAL = "delivery_approval"
    PR_APPROVAL = "pr_approval"
    WEAR_OS_APPROVAL = "wear_os_approval"
    STRATEGIC_DECISION = "strategic_decision"
    CAPITAL_REBALANCE = "capital_rebalance"
    RISK_OVERRIDE = "risk_override"


class GateDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    NEEDS_MORE_INFO = "needs_more_info"


@dataclass
class GateRequest:
    gate_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    gate_type: GateType = GateType.DELIVERY_APPROVAL
    title: str = ""
    description: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    amount_usd: float = 0.0
    platform: str = ""
    auto_approvable: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    waiting_since: datetime | None = field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
    decision: GateDecision | None = None
    resolver_notes: str = ""

    # UI helpers
    @property
    def display_title(self) -> str:
        if self.amount_usd > 0:
            return f"{self.title} — ${self.amount_usd:,.0f}"
        return self.title


@dataclass
class GateRule:
    gate_type: GateType
    auto_approve_threshold_usd: float = 0.0
    auto_approve_conditions: dict[str, Any] = field(default_factory=dict)
    requires_human: bool = True


class HumanGate:
    """
    Manages human-in-the-loop gates for critical decisions.

    Gates that require human approval:
    - Delivery approval (WorkBank items ready_to_deliver)
    - PR approval (CoderAgent generated PRs)
    - Wear OS approvals (high-value submissions)
    - Strategic decisions (mode changes, capital allocation)
    - Risk overrides (drawdown limits, leverage changes)
    """

    def __init__(self, config: AutopilotConfig):
        self.config = config
        self._pending_gates: dict[str, GateRequest] = {}
        self._gate_rules: dict[GateType, GateRule] = {}
        self._wear_os = None
        self._callbacks: list[Callable[[GateRequest], None]] = []
        self._auto_approve_enabled = True

        # Initialize default rules
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        """Initialize default gate rules from config."""
        threshold = self.config.automation.wear_os_auto_approve_usd

        self._gate_rules = {
            GateType.DELIVERY_APPROVAL: GateRule(
                gate_type=GateType.DELIVERY_APPROVAL,
                auto_approve_threshold_usd=0,  # Never auto-approve delivery
                requires_human=True,
            ),
            GateType.PR_APPROVAL: GateRule(
                gate_type=GateType.PR_APPROVAL,
                auto_approve_threshold_usd=0,  # Never auto-approve PRs
                auto_approve_conditions={"confidence": self.config.automation.coder_agent_auto_merge_confidence},
                requires_human=True,
            ),
            GateType.WEAR_OS_APPROVAL: GateRule(
                gate_type=GateType.WEAR_OS_APPROVAL, auto_approve_threshold_usd=threshold, requires_human=True
            ),
            GateType.STRATEGIC_DECISION: GateRule(
                gate_type=GateType.STRATEGIC_DECISION, auto_approve_threshold_usd=0, requires_human=True
            ),
            GateType.CAPITAL_REBALANCE: GateRule(
                gate_type=GateType.CAPITAL_REBALANCE,
                auto_approve_threshold_usd=10000,  # Auto-rebalance under $10k
                requires_human=True,
            ),
            GateType.RISK_OVERRIDE: GateRule(
                gate_type=GateType.RISK_OVERRIDE, auto_approve_threshold_usd=0, requires_human=True
            ),
        }

    def set_wear_os(self, wear_os: Any) -> None:
        self._wear_os = wear_os

    def register_callback(self, callback: Callable[[GateRequest], None]) -> None:
        self._callbacks.append(callback)

    # --- Gate Creation ---

    async def request_delivery_approval(
        self,
        item_id: str,
        platform: str,
        title: str,
        amount_usd: float,
        deliverables: list[str],
        delivery_package_path: str,
        submission_guide: str,
    ) -> GateRequest:
        """Request approval for a WorkBank delivery."""
        gate = GateRequest(
            gate_type=GateType.DELIVERY_APPROVAL,
            title=f"Deliver to {platform}",
            description=f"Submit {title} to {platform} for ${amount_usd:,.0f}",
            payload={
                "item_id": item_id,
                "platform": platform,
                "deliverables": deliverables,
                "package_path": delivery_package_path,
                "submission_guide": submission_guide,
            },
            amount_usd=amount_usd,
            platform=platform,
            auto_approvable=False,
        )
        return await self._queue_gate(gate)

    async def request_pr_approval(
        self,
        pr_url: str,
        repo: str,
        title: str,
        confidence: float,
        changes_summary: str,
        test_results: dict[str, Any],
    ) -> GateRequest:
        """Request approval for a CoderAgent PR."""
        auto_approve = (
            confidence >= self.config.automation.coder_agent_auto_merge_confidence and self._auto_approve_enabled
        )

        gate = GateRequest(
            gate_type=GateType.PR_APPROVAL,
            title=f"Merge PR: {title}",
            description=f"CoderAgent PR for {repo} (confidence: {confidence:.0%})",
            payload={
                "pr_url": pr_url,
                "repo": repo,
                "changes_summary": changes_summary,
                "test_results": test_results,
                "confidence": confidence,
            },
            amount_usd=0.0,
            platform="github",
            auto_approvable=auto_approve,
        )
        return await self._queue_gate(gate)

    async def request_wear_os_approval(
        self,
        platform: str,
        title: str,
        amount_usd: float,
        description: str,
        auto_approve: bool = False,
    ) -> GateRequest:
        """Request approval via Wear OS for high-value submissions."""
        threshold = self.config.automation.wear_os_auto_approve_usd
        auto_approvable = auto_approve and amount_usd <= threshold

        gate = GateRequest(
            gate_type=GateType.WEAR_OS_APPROVAL,
            title=f"Wear OS: {title}",
            description=description,
            payload={
                "platform": platform,
                "original_title": title,
            },
            amount_usd=amount_usd,
            platform=platform,
            auto_approvable=auto_approvable,
        )
        return await self._queue_gate(gate)

    async def request_strategic_decision(
        self,
        title: str,
        description: str,
        options: list[dict[str, Any]],
        impact_usd: float = 0.0,
    ) -> GateRequest:
        """Request a strategic decision from human."""
        gate = GateRequest(
            gate_type=GateType.STRATEGIC_DECISION,
            title=title,
            description=description,
            payload={"options": options, "impact_usd": impact_usd},
            amount_usd=impact_usd,
            platform="strategic",
        )
        return await self._queue_gate(gate)

    async def request_capital_rebalance(
        self,
        current_allocation: dict[str, float],
        target_allocation: dict[str, float],
        amount_usd: float,
        reason: str,
    ) -> GateRequest:
        """Request capital rebalancing approval."""
        auto_approvable = amount_usd <= self._gate_rules[GateType.CAPITAL_REBALANCE].auto_approve_threshold_usd

        gate = GateRequest(
            gate_type=GateType.CAPITAL_REBALANCE,
            title="Capital Rebalancing",
            description=f"Rebalance: {reason} (${amount_usd:,.0f})",
            payload={
                "current": current_allocation,
                "target": target_allocation,
                "reason": reason,
            },
            amount_usd=amount_usd,
            platform="capital",
            auto_approvable=auto_approvable,
        )
        return await self._queue_gate(gate)

    async def _queue_gate(self, gate: GateRequest) -> GateRequest:
        """Queue a gate and check for auto-approval."""
        rule = self._gate_rules.get(gate.gate_type)

        # Check auto-approval
        if (
            rule
            and gate.auto_approvable
            and self._auto_approve_enabled
            and gate.amount_usd <= rule.auto_approve_threshold_usd
        ):
            # Auto-approve
            gate.decision = GateDecision.APPROVED
            gate.resolved_at = datetime.utcnow()
            gate.resolver_notes = "Auto-approved per rules"
            logger.info(f"Gate auto-approved: {gate.gate_id} ({gate.title})")
            return gate

        # Queue for human review
        self._pending_gates[gate.gate_id] = gate
        gate.waiting_since = datetime.utcnow()

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(gate)
            except Exception as e:
                logger.error(f"Gate callback error: {e}")

        # Send to Wear OS if available
        if self._wear_os and gate.gate_type in (GateType.WEAR_OS_APPROVAL, GateType.DELIVERY_APPROVAL):
            await self._send_to_wear_os(gate)

        logger.info(f"Gate queued for human review: {gate.gate_id} ({gate.title})")
        return gate

    async def _send_to_wear_os(self, gate: GateRequest) -> None:
        """Send approval request to Wear OS."""
        if not self._wear_os:
            return

        try:
            await self._wear_os.request_approval(
                request_id=gate.gate_id,
                title=gate.display_title,
                message=gate.description,
                actions=["approve", "reject", "view"],
                priority="high" if gate.amount_usd > 10000 else "normal",
            )
        except Exception as e:
            logger.error(f"Failed to send to Wear OS: {e}")

    # --- Gate Resolution ---

    async def resolve_gate(
        self,
        gate_id: str,
        decision: GateDecision,
        notes: str = "",
    ) -> bool:
        """Resolve a pending gate."""
        gate = self._pending_gates.get(gate_id)
        if not gate:
            logger.warning(f"Gate not found: {gate_id}")
            return False

        gate.decision = decision
        gate.resolved_at = datetime.utcnow()
        gate.resolver_notes = notes

        # Remove from pending
        del self._pending_gates[gate_id]

        logger.info(f"Gate resolved: {gate_id} -> {decision.value}")
        return True

    async def auto_approve_low_value(self, gate_id: str) -> bool:
        """Auto-approve a low-value gate if it meets criteria."""
        gate = self._pending_gates.get(gate_id)
        if not gate:
            return False

        rule = self._gate_rules.get(gate.gate_type)
        if not rule or not gate.auto_approvable:
            return False

        if gate.amount_usd <= rule.auto_approve_threshold_usd:
            return await self.resolve_gate(gate_id, GateDecision.APPROVED, "Auto-approved: below threshold")

        return False

    # --- Query Methods ---

    def get_pending_gates(self) -> list[GateRequest]:
        """Get all pending gates sorted by priority."""
        gates = list(self._pending_gates.values())
        # Sort: high amount first, then by wait time
        gates.sort(key=lambda g: (-g.amount_usd, g.waiting_since or datetime.max))
        return gates

    def get_gate(self, gate_id: str) -> GateRequest | None:
        return self._pending_gates.get(gate_id)

    def get_gates_by_type(self, gate_type: GateType) -> list[GateRequest]:
        return [g for g in self._pending_gates.values() if g.gate_type == gate_type]

    def get_stats(self) -> dict[str, Any]:
        pending = list(self._pending_gates.values())
        waiting_times = [g.waiting_since for g in pending if g.waiting_since is not None]
        oldest = min(waiting_times) if waiting_times else None
        return {
            "total_pending": len(pending),
            "by_type": {gt.value: len([g for g in pending if g.gate_type == gt]) for gt in GateType},
            "total_amount_usd": sum(g.amount_usd for g in pending),
            "oldest_waiting_minutes": (int((datetime.utcnow() - oldest).total_seconds() / 60) if oldest else 0),
        }

    def set_auto_approve_enabled(self, enabled: bool) -> None:
        self._auto_approve_enabled = enabled

    def update_rule(self, gate_type: GateType, rule: GateRule) -> None:
        self._gate_rules[gate_type] = rule
