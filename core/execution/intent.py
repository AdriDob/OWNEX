from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class IntentStatus(StrEnum):
    """Lifecycle of an intent from expression to execution."""

    EXPRESSED = "expressed"
    ANALYZING = "analyzing"
    DESIGNED = "designed"
    VALIDATED = "validated"
    COMPILED = "compiled"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class IntentUrgency(StrEnum):
    """Perceived urgency of an intent."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Intent:
    """A user's intention expressed in natural language.

    Intent is the universal entry point. Every action starts here:

        User -> Intent -> COPILOT -> Workflow -> Execution

    The system never assumes the user knows the workflow syntax.
    They express *what* they want; COPILOT figures out *how*.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    text: str = ""
    status: IntentStatus = IntentStatus.EXPRESSED
    urgency: IntentUrgency = IntentUrgency.MEDIUM
    context: dict[str, Any] = field(default_factory=dict)
    workflow_id: str | None = None
    workflow_name: str | None = None
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "status": self.status.value,
            "urgency": self.urgency.value,
            "context": self.context,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "correlation_id": self.correlation_id,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
