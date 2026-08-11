from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class StepType(StrEnum):
    discover = "discover"
    recon = "recon"
    scan = "scan"
    hypothesis = "hypothesis"
    validate = "validate"
    report = "report"
    notify = "notify"


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


@dataclass
class WorkflowStep:
    id: str
    type: StepType
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowTemplate:
    name: str
    description: str
    steps: list[WorkflowStep]


@dataclass
class WorkflowResult:
    step_id: str
    status: RunStatus
    output: Any = None
    error: str | None = None


@dataclass
class WorkflowRun:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    template_name: str = ""
    target: str = ""
    status: RunStatus = RunStatus.pending
    steps: list[WorkflowStep] = field(default_factory=list)
    results: list[WorkflowResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "template_name": self.template_name,
            "target": self.target,
            "status": self.status.value,
            "steps": [{"id": s.id, "type": s.type.value, "params": s.params} for s in self.steps],
            "results": [
                {
                    "step_id": r.step_id,
                    "status": r.status.value,
                    "output": r.output,
                    "error": r.error,
                }
                for r in self.results
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
