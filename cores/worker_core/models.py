from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class WorkPhase(str, Enum):
    """Phases of the autonomous work loop."""

    IDLE = "idle"
    DISCOVER = "discover"
    EVALUATE = "evaluate"
    SELECT = "select"
    PREPARE = "prepare"
    EXECUTE = "execute"
    VALIDATE = "validate"
    DELIVER = "deliver"
    LEARN = "learn"
    BLOCKED = "blocked"
    ERROR = "error"


class WorkState(str, Enum):
    """High-level state of the worker."""

    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    DEGRADED = "degraded"
    ERROR = "error"
    IDLE = "idle"


class AutonomyLevel(str, Enum):
    """What the worker can do without human approval."""

    NONE = "none"  # Everything requires approval
    DISCOVER = "discover"  # Can discover and evaluate
    PREPARE = "prepare"  # Can prepare work items
    EXECUTE = "execute"  # Can execute autonomous tasks
    FULL = "full"  # Full autonomy including delivery


@dataclass
class WorkGoal:
    """A high-level goal for the worker."""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    description: str = ""
    target_monthly_usd: float = 10000.0
    max_hours_per_day: float = 4.0
    preferred_categories: list[str] = field(default_factory=list)
    excluded_categories: list[str] = field(default_factory=list)
    min_reward_usd: float = 50.0
    max_risk_score: float = 0.7
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    active: bool = True


@dataclass
class WorkerConfig:
    """Configuration for the worker core."""

    autonomy_level: AutonomyLevel = AutonomyLevel.PREPARE
    checkpoint_interval_seconds: int = 300
    max_concurrent_work: int = 3
    discovery_interval_seconds: int = 1800
    evaluation_threshold: float = 0.6
    human_approval_required: bool = True
    safe_mode: bool = True
    log_level: str = "INFO"
    test_mode: bool = False  # If True, run one cycle and stop

    # Week 2: Spending limits
    max_cost_per_workflow_usd: float = 5.0  # Max AI cost per single workflow
    max_cost_per_session_usd: float = 20.0  # Max AI cost per session


@dataclass
class WorkItem:
    """A single unit of work being processed."""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    goal_id: str = ""
    opportunity_id: str = ""
    title: str = ""
    description: str = ""
    platform: str = ""
    category: str = ""
    estimated_reward_usd: float = 0.0
    estimated_hours: float = 0.0
    risk_score: float = 0.0
    acceptance_probability: float = 0.0
    expected_value_usd_per_hour: float = 0.0

    phase: WorkPhase = WorkPhase.IDLE
    state: WorkState = WorkState.IDLE

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    last_checkpoint_at: str | None = None

    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    error: str | None = None

    human_action_required: bool = False
    human_action_description: str = ""
    approved_by_human: bool = False
    workflow_id: str | None = None

    def add_checkpoint(self, phase: WorkPhase, data: dict[str, Any]) -> None:
        """Add a checkpoint for resume capability."""
        checkpoint = {
            "phase": phase.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        }
        self.checkpoints.append(checkpoint)
        self.last_checkpoint_at = checkpoint["timestamp"]

    def can_resume_from(self, phase: WorkPhase) -> bool:
        """Check if work can resume from a given phase."""
        return any(cp["phase"] == phase.value for cp in self.checkpoints)

    def get_latest_checkpoint(self) -> dict[str, Any] | None:
        """Get the most recent checkpoint."""
        return self.checkpoints[-1] if self.checkpoints else None


@dataclass
class WorkerMetrics:
    """Runtime metrics for the worker."""

    cycles_completed: int = 0
    work_items_completed: int = 0
    work_items_failed: int = 0
    total_revenue_usd: float = 0.0
    total_hours_invested: float = 0.0
    avg_expected_value_usd_per_hour: float = 0.0
    uptime_seconds: float = 0.0
    last_cycle_at: str | None = None
    errors: list[str] = field(default_factory=list)

    def record_completion(self, reward: float, hours: float) -> None:
        self.work_items_completed += 1
        self.total_revenue_usd += reward
        self.total_hours_invested += hours
        if self.total_hours_invested > 0:
            self.avg_expected_value_usd_per_hour = self.total_revenue_usd / self.total_hours_invested

    def record_failure(self, error: str) -> None:
        self.work_items_failed += 1
        self.errors.append(f"{datetime.now(UTC).isoformat()}: {error}")
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]
