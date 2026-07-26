"""Modelos para el Command Center ORION."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class CommandResult:
    success: bool = True
    command: str = ""
    summary: str = ""
    details: str = ""
    debug: dict[str, Any] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    error: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DailyBriefData:
    targets: int = 0
    endpoints: int = 0
    findings: int = 0
    confirmed_findings: int = 0
    pending_findings: int = 0
    reports_pending: int = 0
    reports_submitted: int = 0
    opportunities: int = 0
    revenue_today: float = 0.0
    trades_today: int = 0
    health_score: float = 0.0
    scheduler_running: bool = False
    active_agents: int = 0
    pipelines_active: int = 0
    bottlenecks: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    events_24h: int = 0
