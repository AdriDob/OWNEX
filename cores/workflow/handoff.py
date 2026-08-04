"""OWNEX OMEGA Handoff Manager — Departmental handoff system.

Manages task transfers between departments with condition-based routing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.workflow.handoff")


class HandoffStatus(StrEnum):
    """Status of a handoff."""

    PENDING = "pending"
    INITIATED = "initiated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HandoffCondition:
    """Condition for triggering a handoff."""

    condition_type: str  # e.g., "architecture_ready", "test_failed"
    source_agent: str  # Use string to avoid AgentId conflict
    target_agent: str  # Use string to avoid AgentId conflict
    auto_handoff: bool = True
    require_approval: bool = False


@dataclass
class Handoff:
    """A handoff between departments."""

    id: str
    workflow_id: str
    task_id: str
    condition: HandoffCondition
    source_agent: str  # Use string to avoid AgentId conflict
    target_agent: str  # Use string to avoid AgentId conflict
    payload: dict[str, Any]
    status: HandoffStatus = HandoffStatus.PENDING
    created_at: datetime = None
    initiated_at: datetime | None = None
    accepted_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class HandoffManager:
    """Manages handoffs between departments.

    Routes tasks based on conditions and maintains handoff state.
    """

    def __init__(self) -> None:
        self._handoffs: dict[str, Handoff] = {}
        self._conditions: list[HandoffCondition] = []
        self._setup_default_conditions()

    def _setup_default_conditions(self) -> None:
        """Setup default departmental handoff conditions."""
        # Use strings temporarily to avoid AgentId conflict
        self._conditions = [
            # Build Department
            HandoffCondition(
                condition_type="architecture_ready",
                source_agent="architecture",
                target_agent="coding",
                auto_handoff=True,
                require_approval=False,
            ),
            HandoffCondition(
                condition_type="code_review_needed",
                source_agent="coding",
                target_agent="qa",
                auto_handoff=True,
                require_approval=False,
            ),
            HandoffCondition(
                condition_type="error_detected",
                source_agent="coding",
                target_agent="debug",
                auto_handoff=True,
                require_approval=False,
            ),
            # Quality Department
            HandoffCondition(
                condition_type="test_failed",
                source_agent="qa",
                target_agent="coding",
                auto_handoff=True,
                require_approval=False,
            ),
            HandoffCondition(
                condition_type="approval_granted",
                source_agent="qa",
                target_agent="orchestrator",
                auto_handoff=True,
                require_approval=False,
            ),
            # Knowledge Department
            HandoffCondition(
                condition_type="research_completed",
                source_agent="research",
                target_agent="architecture",
                auto_handoff=True,
                require_approval=False,
            ),
            HandoffCondition(
                condition_type="documentation_completed",
                source_agent="documentation",
                target_agent="orchestrator",
                auto_handoff=True,
                require_approval=False,
            ),
            # Business Department
            HandoffCondition(
                condition_type="feature_defined",
                source_agent="product",
                target_agent="coding",
                auto_handoff=True,
                require_approval=False,
            ),
            HandoffCondition(
                condition_type="opportunity_found",
                source_agent="revenue",
                target_agent="orchestrator",
                auto_handoff=True,
                require_approval=True,  # Revenue requires human approval
            ),
            # Operations Department
            HandoffCondition(
                condition_type="workflow_ready",
                source_agent="automation",
                target_agent="infrastructure",
                auto_handoff=True,
                require_approval=False,
            ),
            HandoffCondition(
                condition_type="infrastructure_updated",
                source_agent="infrastructure",
                target_agent="orchestrator",
                auto_handoff=True,
                require_approval=False,
            ),
            # Strategic Department
            HandoffCondition(
                condition_type="improvement_suggested",
                source_agent="evolution",
                target_agent="orchestrator",
                auto_handoff=True,
                require_approval=True,  # Evolution requires human approval
            ),
        ]

    def create_handoff(
        self,
        handoff_id: str,
        workflow_id: str,
        task_id: str,
        condition_type: str,
        source_agent: str,
        target_agent: str,
        payload: dict[str, Any],
    ) -> Handoff | None:
        """Create a new handoff."""
        # Find matching condition
        condition = self._find_condition(condition_type, source_agent, target_agent)
        if not condition:
            logger.warning(f"[HANDOFF] No condition found for {condition_type}")
            return None

        handoff = Handoff(
            id=handoff_id,
            workflow_id=workflow_id,
            task_id=task_id,
            condition=condition,
            source_agent=source_agent,
            target_agent=target_agent,
            payload=payload,
        )
        self._handoffs[handoff_id] = handoff
        logger.info(f"[HANDOFF] Created handoff {handoff_id}: {source_agent} → {target_agent}")
        return handoff

    def initiate_handoff(self, handoff_id: str) -> bool:
        """Initiate a handoff."""
        handoff = self._handoffs.get(handoff_id)
        if not handoff:
            logger.error(f"[HANDOFF] Handoff {handoff_id} not found")
            return False

        if handoff.status != HandoffStatus.PENDING:
            logger.warning(f"[HANDOFF] Handoff {handoff_id} already initiated")
            return False

        handoff.status = HandoffStatus.INITIATED
        handoff.initiated_at = datetime.utcnow()
        logger.info(f"[HANDOFF] Initiated handoff {handoff_id}")

        # Auto-handoff if configured
        if handoff.condition.auto_handoff and not handoff.condition.require_approval:
            return self.accept_handoff(handoff_id)

        return True

    def accept_handoff(self, handoff_id: str) -> bool:
        """Accept a handoff."""
        handoff = self._handoffs.get(handoff_id)
        if not handoff:
            return False

        if handoff.status not in (HandoffStatus.PENDING, HandoffStatus.INITIATED):
            logger.warning(f"[HANDOFF] Handoff {handoff_id} cannot be accepted")
            return False

        handoff.status = HandoffStatus.ACCEPTED
        handoff.accepted_at = datetime.utcnow()
        logger.info(f"[HANDOFF] Accepted handoff {handoff_id}: {handoff.target_agent}")
        return True

    def reject_handoff(self, handoff_id: str, reason: str) -> bool:
        """Reject a handoff."""
        handoff = self._handoffs.get(handoff_id)
        if not handoff:
            return False

        handoff.status = HandoffStatus.REJECTED
        handoff.error = reason
        handoff.completed_at = datetime.utcnow()
        logger.warning(f"[HANDOFF] Rejected handoff {handoff_id}: {reason}")
        return True

    def complete_handoff(self, handoff_id: str) -> bool:
        """Mark a handoff as completed."""
        handoff = self._handoffs.get(handoff_id)
        if not handoff:
            return False

        if handoff.status != HandoffStatus.ACCEPTED:
            logger.warning(f"[HANDOFF] Handoff {handoff_id} not accepted")
            return False

        handoff.status = HandoffStatus.COMPLETED
        handoff.completed_at = datetime.utcnow()
        logger.info(f"[HANDOFF] Completed handoff {handoff_id}")
        return True

    def fail_handoff(self, handoff_id: str, error: str) -> bool:
        """Mark a handoff as failed."""
        handoff = self._handoffs.get(handoff_id)
        if not handoff:
            return False

        handoff.status = HandoffStatus.FAILED
        handoff.error = error
        handoff.completed_at = datetime.utcnow()
        logger.error(f"[HANDOFF] Failed handoff {handoff_id}: {error}")
        return True

    def trigger_handoff(
        self,
        workflow_id: str,
        task_id: str,
        condition_type: str,
        source_agent: str,
        payload: dict[str, Any],
    ) -> Handoff | None:
        """Trigger a handoff based on condition."""
        # Find matching condition
        condition = self._find_condition(condition_type, source_agent)
        if not condition:
            logger.warning(f"[HANDOFF] No condition found for {condition_type}")
            return None

        handoff_id = f"{workflow_id}:{task_id}:{condition_type}"
        handoff = self.create_handoff(
            handoff_id=handoff_id,
            workflow_id=workflow_id,
            task_id=task_id,
            condition_type=condition_type,
            source_agent=source_agent,
            target_agent=condition.target_agent,
            payload=payload,
        )

        if handoff:
            self.initiate_handoff(handoff_id)

        return handoff

    def get_handoff(self, handoff_id: str) -> Handoff | None:
        """Get a handoff by ID."""
        return self._handoffs.get(handoff_id)

    def get_handoffs_for_workflow(self, workflow_id: str) -> list[Handoff]:
        """Get all handoffs for a workflow."""
        return [h for h in self._handoffs.values() if h.workflow_id == workflow_id]

    def get_handoffs_for_agent(self, agent_id: str) -> list[Handoff]:
        """Get all handoffs for an agent (as source or target)."""
        return [h for h in self._handoffs.values() if h.source_agent == agent_id or h.target_agent == agent_id]

    def get_pending_handoffs(self, agent_id: str) -> list[Handoff]:
        """Get pending handoffs for an agent."""
        return [h for h in self._handoffs.values() if h.target_agent == agent_id and h.status == HandoffStatus.ACCEPTED]

    def _find_condition(
        self, condition_type: str, source_agent: str, target_agent: str | None = None
    ) -> HandoffCondition | None:
        """Find a matching condition."""
        for condition in self._conditions:
            if (
                condition.condition_type == condition_type
                and condition.source_agent == source_agent
                and (target_agent is None or condition.target_agent == target_agent)
            ):
                return condition
        return None

    def list_conditions(self) -> list[HandoffCondition]:
        """List all handoff conditions."""
        return self._conditions.copy()
