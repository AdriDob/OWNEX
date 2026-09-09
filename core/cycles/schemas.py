"""Cycle Engine — Pydantic schemas for API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CycleStatus(str):
    INACTIVE = "inactive"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


class CycleCategory(str):
    SECURITY = "security"
    FORGE = "forge"
    PULSE = "pulse"
    VAULT = "vault"
    ATLAS = "atlas"


class TaskStatus(str):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(str):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CycleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=64)
    slug: str = Field(..., min_length=1, max_length=32, pattern=r"^[a-z0-9_-]+$")
    description: str = ""
    category: str
    status: str = CycleStatus.INACTIVE
    enabled: bool = True
    priority: int = 0
    config: dict[str, Any] = {}


class CycleCreate(CycleBase):
    pass


class CycleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    description: str | None = None
    category: str | None = None
    status: str | None = None
    enabled: bool | None = None
    priority: int | None = None
    config: dict[str, Any] | None = None


class CycleRead(CycleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    @field_validator("config", mode="before")
    @classmethod
    def parse_config(cls, v: Any) -> Any:
        if isinstance(v, str):
            import json

            try:
                return json.loads(v or "{}")
            except (json.JSONDecodeError, TypeError):
                return {}
        return v


class CycleMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cycle_id: int
    opportunities_found: int = 0
    tasks_active: int = 0
    tasks_completed: int = 0
    estimated_value: float = 0.0
    success_rate: float = 0.0
    last_execution: datetime | None = None
    next_action: str | None = None
    throughput_score: float = 0.0


class CycleStatusUpdate(BaseModel):
    status: str
    next_action: str | None = None


class CycleActionResponse(BaseModel):
    success: bool
    message: str
    cycle: CycleRead | None = None


# ── Task schemas ──


class TaskBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    cycle_id: int
    status: str = TaskStatus.PENDING
    priority: int = 0
    estimated_hours: float | None = None
    estimated_reward: float | None = None
    target_id: int | None = None
    target_type: str | None = None
    config: dict[str, Any] = {}


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    estimated_hours: float | None = None
    estimated_reward: float | None = None
    target_id: int | None = None
    target_type: str | None = None
    config: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None


class TaskRead(TaskBase):
    id: int
    actual_hours: float | None = None
    actual_reward: float | None = None
    result: dict[str, Any] = {}
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ── ExecutionState schemas ──


class ExecutionStateBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    status: str = ExecutionStatus.CREATED
    progress: float = 0.0
    current_step: str | None = None
    total_steps: int | None = None
    completed_steps: int = 0
    logs: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}


class ExecutionStateCreate(ExecutionStateBase):
    pass


class ExecutionStateUpdate(BaseModel):
    status: str | None = None
    progress: float | None = None
    current_step: str | None = None
    total_steps: int | None = None
    completed_steps: int | None = None
    logs: list[dict[str, Any]] | None = None
    metrics: dict[str, Any] | None = None


class ExecutionStateRead(ExecutionStateBase):
    id: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
