"""ORION CORE — contracts and data models for the brain of OWNEX."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class PlatformID(str, Enum):
    """Known income platforms — extend as new adapters are added."""

    HACKERONE = "hackerone"
    BUGGROWD = "bugcrowd"
    INTIGRITI = "intigriti"
    ALGORA = "algora"
    ISSUEHUNT = "issuehunt"
    GITHUB = "github"
    FREELANCER = "freelancer"
    SUPERTEAM = "superteam"
    OPENCOLLECTIVE = "opencollective"
    OPIRE = "opire"
    UNKNOWN = "unknown"


class PriorityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


class TaskKind(str, Enum):
    """Types of tasks ORION can dispatch."""

    RECON = "recon"
    SCAN = "scan"
    HYPOTHESIS = "hypothesis"
    VALIDATE = "validate"
    REPORT = "report"
    SUBMIT = "submit"
    REVIEW = "review"
    LEARNING = "learning"
    EXPLORE = "explore"
    MONITOR = "monitor"
    MAINTENANCE = "maintenance"


@dataclass
class ROIScore:
    """Live ROI computation for a platform or program."""

    platform: PlatformID
    score: float  # 0-100
    rank: int = 0
    earnings_30d: float = 0.0
    earnings_7d: float = 0.0
    acceptance_rate: float = 0.0  # 0-1
    avg_response_time_hours: float = 0.0
    finding_count: int = 0
    confirmed_count: int = 0
    pending_payout: float = 0.0
    effort_per_finding: float = 0.0  # estimated hours
    trend: str = "stable"  # rising | falling | stable
    last_active: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class OrionDecision:
    """A decision made by ORION CORE — what to do and why."""

    task_id: str = ""
    kind: TaskKind = TaskKind.EXPLORE
    platform: PlatformID = PlatformID.UNKNOWN
    priority: PriorityLevel = PriorityLevel.LOW
    score: float = 0.0
    reason: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str = ""

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            return datetime.now(UTC) > expiry
        except (ValueError, TypeError):
            return False


@dataclass
class OrionTask:
    """A concrete task dispatched by ORION to a module/agent."""

    id: str = ""
    kind: TaskKind = TaskKind.EXPLORE
    target: str = ""  # platform, endpoint, host, etc.
    description: str = ""
    priority: PriorityLevel = PriorityLevel.LOW
    score: float = 0.0
    status: str = "pending"  # pending | running | completed | failed
    handler: str = ""  # scheduler handler path
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str = ""


@dataclass
class MemoryRecord:
    """A piece of working memory ORION persists across cycles."""

    key: str
    value: Any = None
    category: str = "observation"  # observation | decision | pattern | fact
    source: str = ""
    ttl_hours: int = 0  # 0 = permanent
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def is_expired(self) -> bool:
        if self.ttl_hours <= 0:
            return False
        try:
            created = datetime.fromisoformat(self.created_at)
            age = (datetime.now(UTC) - created).total_seconds() / 3600
            return age > self.ttl_hours
        except (ValueError, TypeError):
            return False


@dataclass
class OODAState:
    """Snapshot of the OODA loop state."""

    cycle: int = 0
    started_at: str = ""
    completed_at: str = ""
    decisions: list[OrionDecision] = field(default_factory=list)
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    scores: dict[str, ROIScore] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str = ""
