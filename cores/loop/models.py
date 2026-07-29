"""OWNEX Loop Engineering — data models.

Maps loop-engineering concepts (patterns, skills, phases, state)
to Python dataclasses for the OWNEX ecosystem.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any


class PatternRisk(enum.Enum):
    """Risk level for a loop pattern (from registry.yaml)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Phase(enum.Enum):
    """Execution phases for a loop pattern.

    Each pattern defines its own ordered phases.
    """

    REPORT = "report"
    DISCOVER = "discover"
    TRIAGE = "triage"
    CLASSIFY = "classify"
    ACT = "act"
    FIX = "fix"
    VERIFY = "verify"
    ESCALATE = "escalate"
    NOTIFY = "notify"
    CLEANUP = "cleanup"
    REVIEW = "review"
    PUBLISH = "publish"


class WeekOneMode(enum.Enum):
    """Maturity level for a freshly scaffolded loop."""

    L1 = "L1"  # Report-only — no auto-fix
    L2 = "L2"  # Fix-capable — with verifier
    L3 = "L3"  # Unattended — full autonomy


class CycleState(enum.Enum):
    """State of an OWNEX Work Cycle (extends LoopState)."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class Skill:
    """A loop-engineering skill definition."""

    name: str
    description: str
    template: str | None = None  # Path to SKILL.md template

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description}


@dataclass
class PatternBudget:
    """Token/cost budget for a loop pattern."""

    tokens_noop: int = 5000
    tokens_report: int = 50000
    tokens_action: int = 200000
    stable_fraction: float = 0.35
    suggested_daily_cap: int = 100000
    max_runs_per_day: int = 2
    max_spawns_l1: int = 0
    max_spawns_l2: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "tokens_noop": self.tokens_noop,
            "tokens_report": self.tokens_report,
            "tokens_action": self.tokens_action,
            "suggested_daily_cap": self.suggested_daily_cap,
            "max_runs_per_day": self.max_runs_per_day,
        }


@dataclass
class LoopPattern:
    """A deployable loop pattern — the core abstraction.

    Maps directly to patterns/registry.yaml in loop-engineering.

    OWNEX Work Cycles are LoopPatterns registered with the PatternRegistry.
    """

    id: str
    name: str
    goal: str
    cadence: str  # e.g. "1d", "2h", "5m"
    risk: PatternRisk = PatternRisk.LOW

    # Components
    skills: list[Skill] = field(default_factory=list)
    phases: list[Phase] = field(default_factory=list)
    human_gates: list[str] = field(default_factory=list)
    budget: PatternBudget = field(default_factory=PatternBudget)
    week_one_mode: WeekOneMode = WeekOneMode.L1

    # OWNEX-specific
    app_id: str | None = None  # Which OWNEX app owns this pattern
    event_triggers: list[str] | None = None  # Events that trigger this pattern
    cycle_states: list[CycleState] | None = None  # State machine

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "cadence": self.cadence,
            "risk": self.risk.value,
            "skills": [s.to_dict() for s in self.skills],
            "phases": [p.value for p in self.phases],
            "human_gates": self.human_gates,
            "budget": self.budget.to_dict(),
            "week_one_mode": self.week_one_mode.value,
            "app_id": self.app_id,
        }


@dataclass
class LoopState:
    """Persistent state for a loop run.

    Written to STATE.md or similar after each run cycle.
    """

    pattern_id: str
    last_run: float = 0.0
    cycle_state: CycleState = CycleState.IDLE
    high_priority: list[dict[str, Any]] = field(default_factory=list)
    watch_list: list[dict[str, Any]] = field(default_factory=list)
    recent_noise: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    human_decisions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "last_run": self.last_run,
            "cycle_state": self.cycle_state.value,
            "high_priority_count": len(self.high_priority),
            "watch_list_count": len(self.watch_list),
        }


@dataclass
class LoopRunResult:
    """Result of a single loop execution cycle."""

    pattern_id: str
    success: bool
    duration_ms: float
    phases_completed: list[Phase] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    state: LoopState | None = None
    timestamp: float = field(default_factory=time.time)


# ── Convenience factory ──────────────────────────────────────────


def ownex_pattern(
    pattern_id: str,
    name: str,
    goal: str,
    cadence: str,
    app_id: str,
    risk: str = "low",
    skills: list[Skill] | None = None,
    phases: list[str] | None = None,
    human_gates: list[str] | None = None,
) -> LoopPattern:
    """Create an OWNEX-specific loop pattern with sensible defaults."""
    return LoopPattern(
        id=pattern_id,
        name=name,
        goal=goal,
        cadence=cadence,
        risk=PatternRisk(risk),
        skills=skills or [],
        phases=[Phase(p) for p in phases] if phases else [],
        human_gates=human_gates or [],
        budget=PatternBudget(),
        week_one_mode=WeekOneMode.L1,
        app_id=app_id,
    )
