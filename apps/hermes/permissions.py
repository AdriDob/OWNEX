"""Hermes Permission System — risk classification, confirmation, audit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ActionPermission:
    """Evaluated permission for a Hermes action."""

    allowed: bool
    command: str
    risk: str  # none | low | medium | high | critical
    destructive: bool
    impact: str
    requires_confirmation: bool
    rollback_available: bool
    reason: str | None = None
    blocked_by: str | None = None


class RiskLevel:
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    ALL = frozenset({NONE, LOW, MEDIUM, HIGH, CRITICAL})


# ── Risk levels per Hermes command ────────────────────────────────

COMMAND_RISK: dict[str, dict[str, Any]] = {
    "backup": {"risk": RiskLevel.LOW, "destructive": False},
    "status": {"risk": RiskLevel.NONE, "destructive": False},
    "health": {"risk": RiskLevel.NONE, "destructive": False},
    "logs": {"risk": RiskLevel.NONE, "destructive": False},
    "doctor": {"risk": RiskLevel.LOW, "destructive": False},
    "help": {"risk": RiskLevel.NONE, "destructive": False},
    "tools": {"risk": RiskLevel.NONE, "destructive": False},
    "snapshot": {"risk": RiskLevel.NONE, "destructive": False},
    "top": {"risk": RiskLevel.NONE, "destructive": False},
    "ps": {"risk": RiskLevel.NONE, "destructive": False},
    "packages": {"risk": RiskLevel.NONE, "destructive": False},
    "disks": {"risk": RiskLevel.NONE, "destructive": False},
    "services": {"risk": RiskLevel.NONE, "destructive": False},
    "kill": {"risk": RiskLevel.HIGH, "destructive": True},
}


def get_command_risk(command: str) -> dict[str, Any]:
    """Return risk config for a command. Unknown commands default to HIGH."""
    return COMMAND_RISK.get(
        command,
        {"risk": RiskLevel.HIGH, "destructive": True},
    )


def needs_confirmation(command: str, safe_mode: bool) -> bool:
    """Whether an action needs human confirmation before execution."""
    risk = get_command_risk(command)
    return risk["risk"] in (RiskLevel.HIGH, RiskLevel.CRITICAL) or bool(risk["destructive"] and safe_mode)


def evaluate_action(command: str, safe_mode: bool, force: bool = False) -> ActionPermission:
    """Evaluate whether an action is allowed to proceed.

    Args:
        command: The Hermes command name.
        safe_mode: Whether safe mode is enabled.
        force: If True, skip confirmation requirements (for approved actions).

    Returns:
        ActionPermission with evaluation result.
    """
    risk_cfg = get_command_risk(command)
    impact = _describe_impact(command)

    if risk_cfg["risk"] == RiskLevel.CRITICAL and not force:
        return ActionPermission(
            allowed=False,
            command=command,
            risk=RiskLevel.CRITICAL,
            destructive=True,
            impact=impact,
            requires_confirmation=True,
            rollback_available=False,
            reason="Critical risk — human approval required",
            blocked_by="risk_threshold",
        )

    if safe_mode and risk_cfg["destructive"] and not force:
        return ActionPermission(
            allowed=False,
            command=command,
            risk=risk_cfg["risk"],
            destructive=True,
            impact=impact,
            requires_confirmation=True,
            rollback_available=True,
            reason="Safe mode blocks destructive actions",
            blocked_by="safe_mode",
        )

    return ActionPermission(
        allowed=True,
        command=command,
        risk=risk_cfg["risk"],
        destructive=risk_cfg["destructive"],
        impact=impact,
        requires_confirmation=needs_confirmation(command, safe_mode) and not force,
        rollback_available=risk_cfg["risk"] in (RiskLevel.LOW, RiskLevel.MEDIUM),
        reason=None,
        blocked_by=None,
    )


def _describe_impact(command: str) -> str:
    descriptions = {
        "backup": "Creates a full system backup (database + config). Safe to run.",
        "kill": "Terminates a running process by PID. Data loss possible.",
        "doctor": "Reads disk, DB, backup, and update status. Read-only.",
    }
    return descriptions.get(command, "No impact description available.")


# ── Action History (in-memory) ────────────────────────────────────


@dataclass
class ActionRecord:
    command: str
    status: str  # requested | approved | denied | started | completed | failed
    risk: str
    destructive: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class ActionHistory:
    """In-memory action history with optional JSONL persistence."""

    def __init__(self, max_size: int = 1000) -> None:
        self._records: list[ActionRecord] = []
        self._max_size = max_size

    def record(self, record: ActionRecord) -> None:
        self._records.append(record)
        if len(self._records) > self._max_size:
            self._records.pop(0)

    def recent(self, limit: int = 20) -> list[ActionRecord]:
        return list(reversed(self._records[-limit:]))

    def by_command(self, command: str, limit: int = 10) -> list[ActionRecord]:
        return [r for r in self._records if r.command == command][-limit:]
