from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

STEP_STATUS_PENDING = "pending"
STEP_STATUS_ACTIVE = "active"
STEP_STATUS_COMPLETED = "completed"
STEP_STATUS_SKIPPED = "skipped"
STEP_STATUS_FAILED = "failed"


@dataclass
class WizardStepDef:
    step_id: str
    label: str
    description: str
    icon: str = "circle"
    order: int = 0
    required: bool = True
    execute_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    validate_fn: Callable[[dict[str, Any]], tuple[bool, str]] | None = None
    schema: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.step_id,
            "label": self.label,
            "description": self.description,
            "icon": self.icon,
            "order": self.order,
            "required": self.required,
            "schema": self.schema,
        }


@dataclass
class WizardState:
    current_step_index: int = 0
    started: bool = False
    completed: bool = False
    started_at: float | None = None
    completed_at: float | None = None
    step_data: dict[str, dict[str, Any]] = field(default_factory=dict)
    step_status: dict[str, str] = field(default_factory=dict)

    def to_dict(self, steps: list[WizardStepDef]) -> dict[str, Any]:
        total = len(steps)
        if self.completed:
            progress = 100.0
        elif not self.started:
            progress = 0.0
        else:
            progress = round((self.current_step_index / total) * 100, 1) if total > 0 else 0.0

        current_step_id = steps[self.current_step_index].step_id if steps and self.current_step_index < total else ""

        return {
            "current_step": self.current_step_index,
            "current_step_id": current_step_id,
            "total_steps": total,
            "started": self.started,
            "completed": self.completed,
            "progress": progress,
            "steps": [
                {
                    "id": s.step_id,
                    "label": s.label,
                    "description": s.description,
                    "icon": s.icon,
                    "order": s.order,
                    "required": s.required,
                    "status": self._get_step_status(s.step_id, s.order),
                }
                for s in steps
            ],
            "step_data": self.step_data,
        }

    def _get_step_status(self, step_id: str, order: int) -> str:
        if step_id in self.step_status:
            return self.step_status[step_id]
        if order < self.current_step_index:
            return STEP_STATUS_SKIPPED
        if order == self.current_step_index:
            return STEP_STATUS_ACTIVE
        return STEP_STATUS_PENDING

    def get_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "wizard_version": "2.0",
            "completed": self.completed,
            "completed_at": self.completed_at,
            "steps": {},
            "config": {},
        }
        for step_id, data in self.step_data.items():
            config["steps"][step_id] = {
                "status": self.step_status.get(step_id, STEP_STATUS_PENDING),
                "data": data,
            }
        return config

    def mark_step(self, step_id: str, status: str, data: dict[str, Any] | None = None) -> None:
        self.step_status[step_id] = status
        if data is not None:
            self.step_data[step_id] = data
