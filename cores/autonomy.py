"""Progressive Autonomy Levels — tiered autonomy control for OWNEX.

Implements four levels of autonomy:
- Level 0: OBSERVER — Read-only analysis, no actions
- Level 1: PREPARER — Generates plans/drafts, requires approval
- Level 2: SUPERVISOR — Executes with human approval gates
- Level 3: AUTONOMOUS — Executes pre-authorized repetitive tasks

Each level builds on the previous, adding capabilities.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from core.events.event_bus import get_core_event_bus
from cores.prometheus_metrics import (
    record_approval_gate,
)

logger = logging.getLogger("ownex.autonomy")


class AutonomyLevel(Enum):
    """Autonomy levels from most restricted to least."""

    OBSERVER = 0  # Read-only, analysis only
    PREPARER = 1  # Plans/drafts, no execution
    SUPERVISOR = 2  # Executes with approval
    AUTONOMOUS = 3  # Executes pre-authorized tasks


class ApprovalDecision(Enum):
    """Approval decision outcomes."""

    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    MODIFIED = "modified"


class ApprovalGateType(Enum):
    """Types of approval gates."""

    TASK_EXECUTION = "task_execution"
    TOOL_USE = "tool_use"
    CREDENTIAL_ACCESS = "credential_access"
    EXTERNAL_ACTION = "external_action"  # API calls, submissions, etc.
    FINANCIAL_ACTION = "financial_action"  # Anything involving money
    DESTRUCTIVE_ACTION = "destructive_action"  # Deletes, overwrites


@dataclass
class ApprovalRequest:
    """Request for human approval."""

    id: str
    gate_type: ApprovalGateType
    autonomy_level: AutonomyLevel
    title: str
    description: str
    details: dict[str, Any]
    requested_at: datetime
    requested_by: str  # agent name or "system"
    expires_at: datetime | None = None
    decision: ApprovalDecision | None = None
    decided_at: datetime | None = None
    decided_by: str | None = None
    modifications: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutonomyPolicy:
    """Policy defining what each autonomy level can do."""

    level: AutonomyLevel

    # Capabilities
    can_read: bool = True
    can_analyze: bool = True
    can_create_plans: bool = False
    can_create_drafts: bool = False
    can_execute_with_approval: bool = False
    can_execute_preauthorized: bool = False
    can_use_tools: set[str] = field(default_factory=set)
    can_access_credentials: bool = False
    can_make_external_calls: bool = False
    can_handle_financial: bool = False
    can_perform_destructive: bool = False

    # Limits
    max_concurrent_tasks: int = 0
    max_daily_actions: int = 0
    max_action_duration_minutes: int = 0
    requires_approval_for: set[ApprovalGateType] = field(default_factory=set)
    preauthorized_categories: set[str] = field(default_factory=set)

    # Learning
    learn_from_feedback: bool = False
    auto_escalate_failures: bool = False


# Default policies for each level
DEFAULT_POLICIES: dict[AutonomyLevel, AutonomyPolicy] = {
    AutonomyLevel.OBSERVER: AutonomyPolicy(
        level=AutonomyLevel.OBSERVER,
        can_read=True,
        can_analyze=True,
        can_create_plans=False,
        can_create_drafts=False,
        can_execute_with_approval=False,
        can_execute_preauthorized=False,
        max_concurrent_tasks=0,
        max_daily_actions=0,
        max_action_duration_minutes=0,
    ),
    AutonomyLevel.PREPARER: AutonomyPolicy(
        level=AutonomyLevel.PREPARER,
        can_read=True,
        can_analyze=True,
        can_create_plans=True,
        can_create_drafts=True,
        can_execute_with_approval=False,
        can_execute_preauthorized=False,
        can_use_tools={"api", "document", "editor"},  # Read-only tools
        max_concurrent_tasks=5,
        max_daily_actions=50,
        max_action_duration_minutes=10,
        requires_approval_for=set(),  # Nothing to approve - no execution
    ),
    AutonomyLevel.SUPERVISOR: AutonomyPolicy(
        level=AutonomyLevel.SUPERVISOR,
        can_read=True,
        can_analyze=True,
        can_create_plans=True,
        can_create_drafts=True,
        can_execute_with_approval=True,
        can_execute_preauthorized=False,
        can_use_tools={"api", "browser", "editor", "git", "terminal", "database"},
        can_access_credentials=True,
        can_make_external_calls=True,
        max_concurrent_tasks=10,
        max_daily_actions=100,
        max_action_duration_minutes=60,
        requires_approval_for={
            ApprovalGateType.TASK_EXECUTION,
            ApprovalGateType.CREDENTIAL_ACCESS,
            ApprovalGateType.EXTERNAL_ACTION,
            ApprovalGateType.FINANCIAL_ACTION,
            ApprovalGateType.DESTRUCTIVE_ACTION,
        },
        learn_from_feedback=True,
        auto_escalate_failures=True,
    ),
    AutonomyLevel.AUTONOMOUS: AutonomyPolicy(
        level=AutonomyLevel.AUTONOMOUS,
        can_read=True,
        can_analyze=True,
        can_create_plans=True,
        can_create_drafts=True,
        can_execute_with_approval=True,
        can_execute_preauthorized=True,
        can_use_tools={"api", "browser", "editor", "git", "terminal", "database", "document", "voice"},
        can_access_credentials=True,
        can_make_external_calls=True,
        can_handle_financial=True,
        can_perform_destructive=True,
        max_concurrent_tasks=20,
        max_daily_actions=500,
        max_action_duration_minutes=240,
        requires_approval_for={
            ApprovalGateType.FINANCIAL_ACTION,
            ApprovalGateType.DESTRUCTIVE_ACTION,
        },
        preauthorized_categories={
            "bug_bounty_recon",
            "dev_task_implementation",
            "data_collection",
            "report_generation",
            "research_summary",
        },
        learn_from_feedback=True,
        auto_escalate_failures=True,
    ),
}


@dataclass
class ActionContext:
    """Context for an action being evaluated."""

    action_type: str
    category: str
    tool: str | None = None
    requires_credentials: bool = False
    is_external_call: bool = False
    is_financial: bool = False
    is_destructive: bool = False
    estimated_duration_minutes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutonomyDecision:
    """Decision on whether an action is allowed."""

    allowed: bool
    level: AutonomyLevel
    reason: str
    requires_approval: bool = False
    gate_type: ApprovalGateType | None = None
    policy: AutonomyPolicy | None = None
    suggested_level: AutonomyLevel | None = None


class ApprovalGate(ABC):
    """Abstract approval gate for human-in-the-loop decisions."""

    @abstractmethod
    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Request approval and return decision."""
        pass

    @abstractmethod
    async def get_pending(self) -> list[ApprovalRequest]:
        """Get pending approval requests."""
        pass


class ConsoleApprovalGate(ApprovalGate):
    """Console-based approval gate for development/testing."""

    def __init__(self):
        self._pending: dict[str, ApprovalRequest] = {}
        self._responses: dict[str, asyncio.Future] = {}

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        self._pending[request.id] = request

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._responses[request.id] = future

        # Print to console
        print(f"\n{'=' * 60}")
        print(f"APPROVAL REQUEST: {request.title}")
        print(f"{'=' * 60}")
        print(f"Type: {request.gate_type.value}")
        print(f"Level: {request.autonomy_level.name}")
        print(f"Description: {request.description}")
        print(f"Details: {request.details}")
        print(f"Requested by: {request.requested_by}")
        print(f"{'=' * 60}")
        print("Options: [a]pprove, [r]eject, [d]efer, [m]odify")

        # Wait for response (with timeout)
        try:
            decision = await asyncio.wait_for(future, timeout=300)  # 5 min timeout
            return decision
        except TimeoutError:
            return ApprovalDecision.DEFERRED
        finally:
            self._pending.pop(request.id, None)
            self._responses.pop(request.id, None)

    async def get_pending(self) -> list[ApprovalRequest]:
        return list(self._pending.values())

    def respond(self, request_id: str, decision: ApprovalDecision, modifications: dict | None = None) -> bool:
        """Respond to an approval request (called from console input handler)."""
        if request_id not in self._responses:
            return False

        future = self._responses[request_id]
        if not future.done():
            future.set_result(decision)
        return True


class AutonomyManager:
    """
    Manages autonomy levels and enforces policies.

    This is the central authority that decides what actions are allowed
    at each autonomy level and manages approval gates.
    """

    def __init__(
        self,
        initial_level: AutonomyLevel = AutonomyLevel.OBSERVER,
        policies: dict[AutonomyLevel, AutonomyPolicy] | None = None,
        approval_gate: ApprovalGate | None = None,
    ):
        self.current_level = initial_level
        self.policies = policies or DEFAULT_POLICIES.copy()
        self.approval_gate = approval_gate or ConsoleApprovalGate()

        # State tracking
        self._action_counts: dict[str, int] = {}  # date -> count
        self._concurrent_tasks: int = 0
        self._daily_actions: int = 0
        self._last_reset_date: str = datetime.now(UTC).date().isoformat()

        # Approval tracking
        self._pending_approvals: dict[str, ApprovalRequest] = {}
        self._approval_history: list[ApprovalRequest] = []

        # Callbacks
        self._level_change_callbacks: list[Callable[[AutonomyLevel, AutonomyLevel], None]] = []
        self._approval_callbacks: list[Callable[[ApprovalRequest], None]] = []

        self.event_bus = get_core_event_bus()
        logger.info("AutonomyManager initialized at level %s", initial_level.name)

    def get_policy(self, level: AutonomyLevel | None = None) -> AutonomyPolicy:
        """Get policy for a level (current if not specified)."""
        return self.policies.get(level or self.current_level, self.policies[AutonomyLevel.OBSERVER])

    def set_level(self, level: AutonomyLevel) -> bool:
        """Change autonomy level."""
        if level not in self.policies:
            logger.error("No policy defined for level %s", level.name)
            return False

        old_level = self.current_level
        self.current_level = level

        logger.info("Autonomy level changed: %s -> %s", old_level.name, level.name)

        self.event_bus.publish(
            "autonomy:level_changed",
            {
                "old_level": old_level.name,
                "new_level": level.name,
            },
        )

        for callback in self._level_change_callbacks:
            try:
                callback(old_level, level)
            except Exception as e:
                logger.error("Level change callback failed: %s", e)

        return True

    def can_perform(self, context: ActionContext) -> AutonomyDecision:
        """Check if an action is allowed at current autonomy level."""
        policy = self.get_policy()

        # Check basic capabilities
        if context.requires_credentials and not policy.can_access_credentials:
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason="Credential access not allowed at this autonomy level",
                suggested_level=AutonomyLevel.SUPERVISOR,
                policy=policy,
            )

        if context.is_external_call and not policy.can_make_external_calls:
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason="External calls not allowed at this autonomy level",
                suggested_level=AutonomyLevel.SUPERVISOR,
                policy=policy,
            )

        if context.is_financial and not policy.can_handle_financial:
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason="Financial actions not allowed at this autonomy level",
                suggested_level=AutonomyLevel.AUTONOMOUS,
                policy=policy,
            )

        if context.is_destructive and not policy.can_perform_destructive:
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason="Destructive actions not allowed at this autonomy level",
                suggested_level=AutonomyLevel.AUTONOMOUS,
                policy=policy,
            )

        if context.tool and context.tool not in policy.can_use_tools:
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason=f"Tool '{context.tool}' not allowed at this autonomy level",
                suggested_level=self._suggest_level_for_tool(context.tool),
                policy=policy,
            )

        # Check limits
        if self._concurrent_tasks >= policy.max_concurrent_tasks and policy.max_concurrent_tasks > 0:
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason=f"Max concurrent tasks ({policy.max_concurrent_tasks}) reached",
                policy=policy,
            )

        if self._daily_actions >= policy.max_daily_actions and policy.max_daily_actions > 0:
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason=f"Max daily actions ({policy.max_daily_actions}) reached",
                policy=policy,
            )

        if (
            context.estimated_duration_minutes > policy.max_action_duration_minutes
            and policy.max_action_duration_minutes > 0
        ):
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason=f"Action duration ({context.estimated_duration_minutes}min) exceeds limit ({policy.max_action_duration_minutes}min)",
                policy=policy,
            )

        # Check if pre-authorized
        if context.category in policy.preauthorized_categories and policy.can_execute_preauthorized:
            return AutonomyDecision(
                allowed=True,
                level=self.current_level,
                reason="Pre-authorized category",
                policy=policy,
            )

        # Check if execution allowed
        if not policy.can_execute_with_approval and not policy.can_execute_preauthorized:
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason="Execution not allowed at this autonomy level (preparer/observer only)",
                suggested_level=AutonomyLevel.SUPERVISOR,
                policy=policy,
            )

        # Determine if approval needed
        gate_type = self._determine_gate_type(context)
        requires_approval = gate_type in policy.requires_approval_for

        if requires_approval and not policy.can_execute_with_approval:
            return AutonomyDecision(
                allowed=False,
                level=self.current_level,
                reason=f"Approval required for {gate_type.value} but not allowed at this level",
                requires_approval=True,
                gate_type=gate_type,
                suggested_level=AutonomyLevel.SUPERVISOR,
                policy=policy,
            )

        return AutonomyDecision(
            allowed=True,
            level=self.current_level,
            reason="Action allowed",
            requires_approval=requires_approval,
            gate_type=gate_type if requires_approval else None,
            policy=policy,
        )

    def _determine_gate_type(self, context: ActionContext) -> ApprovalGateType:
        """Determine the approval gate type for an action."""
        if context.is_financial:
            return ApprovalGateType.FINANCIAL_ACTION
        if context.is_destructive:
            return ApprovalGateType.DESTRUCTIVE_ACTION
        if context.requires_credentials:
            return ApprovalGateType.CREDENTIAL_ACCESS
        if context.is_external_call:
            return ApprovalGateType.EXTERNAL_ACTION
        return ApprovalGateType.TASK_EXECUTION

    def _suggest_level_for_tool(self, tool: str) -> AutonomyLevel | None:
        """Suggest minimum autonomy level for a tool."""
        for level in [AutonomyLevel.PREPARER, AutonomyLevel.SUPERVISOR, AutonomyLevel.AUTONOMOUS]:
            if tool in self.policies[level].can_use_tools:
                return level
        return AutonomyLevel.AUTONOMOUS

    async def request_approval(
        self,
        gate_type: ApprovalGateType,
        title: str,
        description: str,
        details: dict[str, Any],
        requested_by: str = "system",
        expires_in_minutes: int = 30,
    ) -> ApprovalDecision:
        """Request human approval for an action."""
        self.get_policy()

        request = ApprovalRequest(
            id=f"appr_{int(time.time() * 1000)}",
            gate_type=gate_type,
            autonomy_level=self.current_level,
            title=title,
            description=description,
            details=details,
            requested_at=datetime.now(UTC),
            requested_by=requested_by,
            expires_at=datetime.now(UTC).replace(minute=datetime.now(UTC).minute + expires_in_minutes),
        )

        self._pending_approvals[request.id] = request

        start_time = time.time()

        try:
            decision = await self.approval_gate.request_approval(request)
        except Exception as e:
            logger.error("Approval gate error: %s", e)
            decision = ApprovalDecision.REJECTED

        duration = time.time() - start_time

        request.decision = decision
        request.decided_at = datetime.now(UTC)

        # Record metrics
        record_approval_gate(gate_type.value, decision.value, duration)

        # Move to history
        self._approval_history.append(request)
        del self._pending_approvals[request.id]

        # Notify callbacks
        for callback in self._approval_callbacks:
            try:
                callback(request)
            except Exception as e:
                logger.error("Approval callback failed: %s", e)

        self.event_bus.publish(
            "autonomy:approval_decision",
            {
                "request_id": request.id,
                "gate_type": gate_type.value,
                "decision": decision.value,
                "duration": duration,
            },
        )

        logger.info("Approval %s for %s: %s", request.id, gate_type.value, decision.value)
        return decision

    def start_action(self) -> None:
        """Mark start of an action (for limit tracking)."""
        self._concurrent_tasks += 1
        self._daily_actions += 1
        self._check_daily_reset()

    def end_action(self) -> None:
        """Mark end of an action."""
        self._concurrent_tasks = max(0, self._concurrent_tasks - 1)

    def _check_daily_reset(self) -> None:
        """Reset daily counters if new day."""
        today = datetime.now(UTC).date().isoformat()
        if today != self._last_reset_date:
            self._daily_actions = 0
            self._last_reset_date = today

    def get_status(self) -> dict[str, Any]:
        """Get current autonomy status."""
        policy = self.get_policy()
        return {
            "current_level": self.current_level.name,
            "current_level_value": self.current_level.value,
            "policy": {
                "can_read": policy.can_read,
                "can_analyze": policy.can_analyze,
                "can_create_plans": policy.can_create_plans,
                "can_create_drafts": policy.can_create_drafts,
                "can_execute_with_approval": policy.can_execute_with_approval,
                "can_execute_preauthorized": policy.can_execute_preauthorized,
                "can_use_tools": list(policy.can_use_tools),
                "can_access_credentials": policy.can_access_credentials,
                "can_make_external_calls": policy.can_make_external_calls,
                "can_handle_financial": policy.can_handle_financial,
                "can_perform_destructive": policy.can_perform_destructive,
                "max_concurrent_tasks": policy.max_concurrent_tasks,
                "max_daily_actions": policy.max_daily_actions,
                "preauthorized_categories": list(policy.preauthorized_categories),
            },
            "usage": {
                "concurrent_tasks": self._concurrent_tasks,
                "daily_actions": self._daily_actions,
                "pending_approvals": len(self._pending_approvals),
            },
            "available_levels": [level.name for level in AutonomyLevel],
        }

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        """Get pending approval requests."""
        return list(self._pending_approvals.values())

    def get_approval_history(self, limit: int = 50) -> list[ApprovalRequest]:
        """Get approval history."""
        return self._approval_history[-limit:]

    def register_level_change_callback(self, callback: Callable[[AutonomyLevel, AutonomyLevel], None]) -> None:
        """Register callback for level changes."""
        self._level_change_callbacks.append(callback)

    def register_approval_callback(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """Register callback for approval decisions."""
        self._approval_callbacks.append(callback)

    async def health_check(self) -> dict[str, Any]:
        """Health check."""
        issues = []

        if self._concurrent_tasks < 0:
            issues.append("Negative concurrent task count")

        if self._concurrent_tasks > self.get_policy().max_concurrent_tasks:
            issues.append("Concurrent tasks exceed policy limit")

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "current_level": self.current_level.name,
            "concurrent_tasks": self._concurrent_tasks,
            "daily_actions": self._daily_actions,
            "pending_approvals": len(self._pending_approvals),
        }


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON
# ──────────────────────────────────────────────────────────────────────────

_autonomy_manager: AutonomyManager | None = None


def get_autonomy_manager() -> AutonomyManager:
    """Get or create the global autonomy manager."""
    global _autonomy_manager
    if _autonomy_manager is None:
        _autonomy_manager = AutonomyManager()
    return _autonomy_manager


async def initialize_autonomy(
    initial_level: AutonomyLevel = AutonomyLevel.OBSERVER,
    approval_gate: ApprovalGate | None = None,
) -> AutonomyManager:
    """Initialize the autonomy system."""
    global _autonomy_manager
    _autonomy_manager = AutonomyManager(
        initial_level=initial_level,
        approval_gate=approval_gate,
    )

    health = await _autonomy_manager.health_check()
    logger.info("Autonomy system initialized: %s", "healthy" if health["healthy"] else "issues found")
    return _autonomy_manager
