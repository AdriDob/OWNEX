"""Command System Models — command definitions, permission levels, results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PermissionLevel(str, Enum):
    """Permission levels for command execution.

    Mirrors the COMMAND_SYSTEM.md taxonomy and Hermes risk levels.
    """

    PUBLIC = "PUBLIC"  # any agent, no restriction
    OPERATOR = "OPERATOR"  # advanced user, autonomous COPILOT
    ADMIN = "ADMIN"  # system administrators
    SYSTEM = "SYSTEM"  # self-operations only
    DANGEROUS = "DANGEROUS"  # explicit confirmation required


class CommandFlag:
    """Universal command flags as defined in COMMAND_SYSTEM.md."""

    SILENT = "silent"
    DRY_RUN = "dry_run"
    SIMULATE = "simulate"
    PREVIEW = "preview"
    WHY = "why"
    INTERACTIVE = "interactive"
    FORMAT = "format"
    CONTEXT = "context"

    ALL = frozenset({SILENT, DRY_RUN, SIMULATE, PREVIEW, WHY, INTERACTIVE, FORMAT, CONTEXT})


@dataclass
class CommandParam:
    """Parameter definition for a command."""

    name: str
    type: str
    required: bool = False
    description: str = ""


@dataclass
class CommandCost:
    """Estimated cost of executing a command."""

    time: str = ""
    cpu: str = ""
    network: bool = False
    tokens: int = 0
    money: str = ""


@dataclass
class CommandDefinition:
    """Full definition of a single command in the system."""

    name: str
    aliases: list[str] = field(default_factory=list)
    category: str = ""
    description: str = ""
    permission: PermissionLevel = PermissionLevel.PUBLIC
    interactive: bool = False
    silent: bool = False
    risk: str = "low"

    cost: CommandCost = field(default_factory=CommandCost)

    params: list[CommandParam] = field(default_factory=list)
    flags: list[dict[str, Any]] = field(default_factory=list)

    events_published: list[str] = field(default_factory=list)
    capabilities_used: list[str] = field(default_factory=list)

    chains: list[str] = field(default_factory=list)
    expands_to: list[str] = field(default_factory=list)

    why: str = ""

    def dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "aliases": self.aliases,
            "category": self.category,
            "description": self.description,
            "permission": self.permission.value,
            "interactive": self.interactive,
            "silent": self.silent,
            "risk": self.risk,
            "cost": {
                "time": self.cost.time,
                "cpu": self.cost.cpu,
                "network": self.cost.network,
                "tokens": self.cost.tokens,
                "money": self.cost.money,
            },
            "params": [
                {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                for p in self.params
            ],
            "flags": self.flags,
            "events_published": self.events_published,
            "capabilities_used": self.capabilities_used,
            "chains": self.chains,
            "expands_to": self.expands_to,
            "why": self.why,
        }


@dataclass
class CommandResult:
    """Result of a command execution."""

    command: str
    status: str  # executed | failed | rejected | simulated
    permission: str
    reason: str = ""
    output: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str | None = None


# ── Execution history record ────────────────────────────────────


@dataclass
class CommandRecord:
    """Persistent record of a command execution."""

    command: str
    status: str
    permission: str
    args: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    duration_ms: float = 0.0
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
