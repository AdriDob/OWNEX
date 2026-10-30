"""Approval Gates — Human-in-the-loop for sensitive actions.

Ensures critical actions require human approval before execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.approval.gates")


class ApprovalLevel(StrEnum):
    """Levels of approval required."""

    AUTO = "auto"  # No approval needed
    NOTIFICATION = "notification"  # Inform only
    CONFIRMATION = "confirmation"  # Quick confirm
    FULL_REVIEW = "full_review"  # Full review required


class ActionType(StrEnum):
    """Types of actions that may require approval."""

    SUBMIT_REPORT = "submit_report"
    SEND_EXTERNAL = "send_external"
    FINANCIAL_TRANSFER = "financial_transfer"
    INVESTMENT = "investment"
    DELETE_DATA = "delete_data"
    MODIFY_CONFIG = "modify_config"
    RUN_AGENT = "run_agent"
    PUBLISH = "publish"


# Default approval levels for each action type
DEFAULT_APPROVAL_LEVELS: dict[ActionType, ApprovalLevel] = {
    ActionType.SUBMIT_REPORT: ApprovalLevel.CONFIRMATION,
    ActionType.SEND_EXTERNAL: ApprovalLevel.FULL_REVIEW,
    ActionType.FINANCIAL_TRANSFER: ApprovalLevel.FULL_REVIEW,
    ActionType.INVESTMENT: ApprovalLevel.FULL_REVIEW,
    ActionType.DELETE_DATA: ApprovalLevel.FULL_REVIEW,
    ActionType.MODIFY_CONFIG: ApprovalLevel.CONFIRMATION,
    ActionType.RUN_AGENT: ApprovalLevel.NOTIFICATION,
    ActionType.PUBLISH: ApprovalLevel.FULL_REVIEW,
}


@dataclass
class ApprovalRequest:
    """A pending approval request."""

    id: str
    action_type: ActionType
    level: ApprovalLevel
    title: str
    description: str
    risk_level: str  # low, medium, high, critical
    estimated_impact: str  # human-readable impact
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "pending"  # pending, approved, rejected, expired
    decided_at: datetime | None = None
    decided_by: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "risk_level": self.risk_level,
            "estimated_impact": self.estimated_impact,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "notes": self.notes,
        }


class ApprovalGate:
    """Manages approval gates for sensitive actions."""

    def __init__(self) -> None:
        self.pending: dict[str, ApprovalRequest] = {}
        self.history: list[ApprovalRequest] = []
        self.configs: dict[ActionType, ApprovalLevel] = dict(DEFAULT_APPROVAL_LEVELS)
        self._request_counter = 0

    def get_level(self, action_type: ActionType) -> ApprovalLevel:
        """Get approval level for an action type."""
        return self.configs.get(action_type, ApprovalLevel.FULL_REVIEW)

    def set_level(self, action_type: ActionType, level: ApprovalLevel) -> None:
        """Set approval level for an action type."""
        self.configs[action_type] = level

    def request_approval(
        self,
        action_type: ActionType,
        title: str,
        description: str,
        risk_level: str = "medium",
        estimated_impact: str = "",
    ) -> ApprovalRequest | None:
        """Request approval for an action. Returns None if AUTO level."""
        level = self.get_level(action_type)

        if level == ApprovalLevel.AUTO:
            return None  # No approval needed

        self._request_counter += 1
        request = ApprovalRequest(
            id=f"approval_{self._request_counter}",
            action_type=action_type,
            level=level,
            title=title,
            description=description,
            risk_level=risk_level,
            estimated_impact=estimated_impact,
        )

        self.pending[request.id] = request
        logger.info(
            "[APPROVAL] Requested %s for %s: %s (risk=%s)",
            level.value,
            action_type.value,
            title,
            risk_level,
        )
        return request

    def approve(self, request_id: str, notes: str = "") -> bool:
        """Approve a pending request."""
        if request_id not in self.pending:
            return False

        request = self.pending.pop(request_id)
        request.status = "approved"
        request.decided_at = datetime.now(UTC)
        request.notes = notes
        self.history.append(request)
        logger.info("[APPROVED] %s: %s", request.action_type.value, request.title)
        return True

    def reject(self, request_id: str, notes: str = "") -> bool:
        """Reject a pending request."""
        if request_id not in self.pending:
            return False

        request = self.pending.pop(request_id)
        request.status = "rejected"
        request.decided_at = datetime.now(UTC)
        request.notes = notes
        self.history.append(request)
        logger.info("[REJECTED] %s: %s", request.action_type.value, request.title)
        return True

    def get_pending(self) -> list[ApprovalRequest]:
        """Get all pending approval requests."""
        return list(self.pending.values())

    def get_history(self, limit: int = 50) -> list[ApprovalRequest]:
        """Get approval history."""
        return self.history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get approval statistics."""
        total = len(self.history) + len(self.pending)
        approved = sum(1 for h in self.history if h.status == "approved")
        rejected = sum(1 for h in self.history if h.status == "rejected")
        pending = len(self.pending)

        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "approval_rate": round(approved / max(total, 1) * 100, 1),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize approval gate state."""
        return {
            "pending": [r.to_dict() for r in self.get_pending()],
            "stats": self.get_stats(),
            "configs": {k.value: v.value for k, v in self.configs.items()},
        }


# Singleton
_approval_gate: ApprovalGate | None = None


def get_approval_gate() -> ApprovalGate:
    """Get or create the global approval gate."""
    global _approval_gate
    if _approval_gate is None:
        _approval_gate = ApprovalGate()
    return _approval_gate
