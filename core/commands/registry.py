"""Command Registry — singleton catalog of all 107 OWNEX commands.

Registered in Capability Registry as ``command:<name>`` for COPILOT discovery.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from core.commands.models import (
    CommandCost,
    CommandDefinition,
    CommandParam,
    PermissionLevel,
)

logger = logging.getLogger("ownex.core.commands.registry")


def _cmd(
    name: str,
    aliases: list[str] | None = None,
    category: str = "",
    description: str = "",
    permission: PermissionLevel = PermissionLevel.PUBLIC,
    interactive: bool = False,
    silent: bool = False,
    risk: str = "low",
    time: str = "",
    cpu: str = "",
    network: bool = False,
    tokens: int = 0,
    money: str = "",
    params: list[CommandParam] | None = None,
    flags: list[dict[str, Any]] | None = None,
    events_published: list[str] | None = None,
    capabilities_used: list[str] | None = None,
    chains: list[str] | None = None,
    expands_to: list[str] | None = None,
    why: str = "",
) -> CommandDefinition:
    return CommandDefinition(
        name=name,
        aliases=aliases or [],
        category=category,
        description=description,
        permission=permission,
        interactive=interactive,
        silent=silent,
        risk=risk,
        cost=CommandCost(time=time, cpu=cpu, network=network, tokens=tokens, money=money),
        params=params or [],
        flags=flags or [],
        events_published=events_published or [],
        capabilities_used=capabilities_used or [],
        chains=chains or [],
        expands_to=expands_to or [],
        why=why,
    )


_UNIVERSAL_FLAGS = [
    {"name": "silent", "alias": "-s", "description": "No UI output, only events"},
    {"name": "dry-run", "alias": "-d", "description": "Preview without executing"},
    {"name": "why", "alias": "-w", "description": "Explain why this command/priority"},
    {"name": "format", "alias": "-f", "description": "Output format: text/json/markdown/html"},
]


class CommandRegistry:
    """Singleton registry of all ORION commands.

    Commands are defined here and also registered in CapabilityRegistry
    for COPILOT discovery.
    """

    def __init__(self) -> None:
        self._commands: dict[str, CommandDefinition] = {}
        self._alias_index: dict[str, str] = {}
        self._lock = threading.Lock()
        self._register_all()

    # ── Registration ────────────────────────────────────────────

    def register(self, cmd: CommandDefinition) -> None:
        with self._lock:
            self._commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self._alias_index[alias.lstrip("/")] = cmd.name
        logger.debug("Registered command '%s' (%s)", cmd.name, cmd.permission.value)

    def get(self, name: str) -> CommandDefinition | None:
        raw = name.lstrip("/")
        with self._lock:
            cmd = self._commands.get(raw)
            if cmd is None and raw in self._alias_index:
                cmd = self._commands.get(self._alias_index[raw])
        return cmd

    def list(self, category: str | None = None, permission: str | None = None) -> list[CommandDefinition]:
        with self._lock:
            cmds = list(self._commands.values())
        if category:
            cmds = [c for c in cmds if c.category == category]
        if permission:
            cmds = [c for c in cmds if c.permission.value == permission]
        return sorted(cmds, key=lambda c: c.name)

    def categories(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for cmd in self._commands.values():
            if cmd.category and cmd.category not in seen:
                seen.add(cmd.category)
                result.append(cmd.category)
        return result

    def count(self) -> int:
        return len(self._commands)

    def to_capability_registry(self) -> list[tuple[str, str, dict[str, Any]]]:
        entries: list[tuple[str, str, dict[str, Any]]] = []
        for cmd in self._commands.values():
            cap = f"command:{cmd.name}"
            meta: dict[str, Any] = {
                "permission": cmd.permission.value,
                "category": cmd.category,
                "risk": cmd.risk,
                "aliases": cmd.aliases,
            }
            entries.append((cap, "command_system", meta))
        return entries

    # ── All 107 commands from COMMAND_SYSTEM.md taxonomy ─────────

    def _register_all(self) -> None:
        # ── A — Architecture & Quality (10) ──────────────────────
        self.register(
            _cmd(
                "audit",
                ["/a"],
                "architecture",
                "Full system audit",
                PermissionLevel.ADMIN,
                time="5min",
                tokens=20000,
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Evaluates code quality, security, and architecture across the system",
            )
        )
        self.register(
            _cmd(
                "audit quick",
                ["/aq"],
                "architecture",
                "Quick focused audit",
                PermissionLevel.OPERATOR,
                time="1min",
                tokens=5000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Fast check of a specific module or concern",
            )
        )
        self.register(
            _cmd(
                "review",
                ["/rv"],
                "architecture",
                "Code review pass",
                PermissionLevel.ADMIN,
                time="3min",
                tokens=10000,
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Reviews code for bugs, security, and style",
            )
        )
        self.register(
            _cmd(
                "refactor",
                ["/rf"],
                "architecture",
                "Refactor module",
                PermissionLevel.ADMIN,
                time="5min",
                tokens=30000,
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Restructures code without changing behavior",
            )
        )
        self.register(
            _cmd(
                "clean",
                ["/cln"],
                "architecture",
                "Clean project artifacts",
                PermissionLevel.ADMIN,
                time="2min",
                tokens=5000,
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Removes temp files, caches, and build artifacts",
            )
        )
        self.register(
            _cmd(
                "optimize",
                ["/op"],
                "architecture",
                "Optimize system performance",
                PermissionLevel.ADMIN,
                time="3min",
                tokens=10000,
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Identifies and applies performance improvements",
            )
        )
        self.register(
            _cmd(
                "simplify",
                ["/sp"],
                "architecture",
                "Simplify complex code",
                PermissionLevel.ADMIN,
                time="2min",
                tokens=8000,
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Reduces cyclomatic complexity and duplication",
            )
        )
        self.register(
            _cmd(
                "score",
                ["/sc"],
                "architecture",
                "System health score",
                PermissionLevel.PUBLIC,
                time="30s",
                tokens=2000,
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Calculates overall system health and quality metrics",
            )
        )
        self.register(
            _cmd(
                "roadmap",
                ["/rm"],
                "architecture",
                "Show project roadmap",
                PermissionLevel.PUBLIC,
                time="10s",
                tokens=1000,
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Displays current phase, completed items, and next steps",
            )
        )
        self.register(
            _cmd(
                "debt",
                ["/db"],
                "architecture",
                "Show technical debt",
                PermissionLevel.ADMIN,
                time="2min",
                tokens=5000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Lists known technical debt with priorities",
            )
        )

        # ── B — Bug Bounty & Offensive (12) ──────────────────────
        self.register(
            _cmd(
                "recon",
                ["/rc"],
                "bugbounty",
                "Intelligent recon pipeline",
                PermissionLevel.OPERATOR,
                time="5min",
                money="$0.05",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Subfinder → Katana → Wayback → KG → COPILOT analysis",
            )
        )
        self.register(
            _cmd(
                "idor",
                ["/id"],
                "bugbounty",
                "IDOR vulnerability analysis",
                PermissionLevel.OPERATOR,
                time="3min",
                money="$0.03",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Tests for Insecure Direct Object References",
            )
        )
        self.register(
            _cmd(
                "api",
                ["/ap"],
                "bugbounty",
                "API security testing",
                PermissionLevel.OPERATOR,
                time="4min",
                money="$0.04",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Tests REST/GraphQL endpoints for common vulns",
            )
        )
        self.register(
            _cmd(
                "auth",
                ["/au"],
                "bugbounty",
                "Authentication testing",
                PermissionLevel.OPERATOR,
                time="3min",
                money="$0.03",
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Tests auth mechanisms for bypasses and flaws",
            )
        )
        self.register(
            _cmd(
                "businesslogic",
                ["/bl"],
                "bugbounty",
                "Business logic testing",
                PermissionLevel.OPERATOR,
                time="4min",
                money="$0.04",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Tests for business logic vulnerabilities",
            )
        )
        self.register(
            _cmd(
                "attack",
                ["/at"],
                "bugbounty",
                "Execute offensive attack",
                PermissionLevel.OPERATOR,
                time="5min",
                money="$0.05",
                risk="high",
                flags=_UNIVERSAL_FLAGS,
                why="Runs offensive intelligence pipeline against target",
            )
        )
        self.register(
            _cmd(
                "validate",
                ["/va"],
                "bugbounty",
                "Validate finding",
                PermissionLevel.OPERATOR,
                time="2min",
                money="$0.02",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Validates whether a finding is reproducible",
            )
        )
        self.register(
            _cmd(
                "poc",
                ["/pc"],
                "bugbounty",
                "Generate proof of concept",
                PermissionLevel.OPERATOR,
                time="3min",
                money="$0.03",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Creates reproduction steps and PoC code",
            )
        )
        self.register(
            _cmd(
                "evidence",
                ["/evd"],
                "bugbounty",
                "Compose evidence package",
                PermissionLevel.OPERATOR,
                time="2min",
                money="$0.02",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Assembles full evidence with CVSS, CWE, request/response",
            )
        )
        self.register(
            _cmd(
                "report",
                ["/rpt"],
                "bugbounty",
                "Generate security report",
                PermissionLevel.OPERATOR,
                time="3min",
                money="$0.03",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Creates platform-ready security report",
            )
        )
        self.register(
            _cmd(
                "acceptance",
                ["/ac"],
                "bugbounty",
                "Check report acceptance odds",
                PermissionLevel.OPERATOR,
                time="1min",
                money="$0.01",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Estimates probability of report acceptance",
            )
        )
        self.register(
            _cmd(
                "attack graph",
                ["/ag"],
                "bugbounty",
                "Build attack graph",
                PermissionLevel.OPERATOR,
                time="3min",
                money="$0.03",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Maps attack paths from entry point to vulnerability",
            )
        )

        # ── C — COPILOT (8) ──────────────────────────────────────
        self.register(
            _cmd(
                "copilot think",
                ["/ct"],
                "copilot",
                "COPILOT deep analysis",
                PermissionLevel.OPERATOR,
                time="2min",
                tokens=10000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="COPILOT analyzes a situation and provides insights",
            )
        )
        self.register(
            _cmd(
                "copilot plan",
                ["/cp"],
                "copilot",
                "COPILOT workflow planning",
                PermissionLevel.OPERATOR,
                time="3min",
                tokens=15000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="COPILOT creates a plan for a given objective",
            )
        )
        self.register(
            _cmd(
                "copilot explain",
                ["/ce"],
                "copilot",
                "COPILOT explains a decision",
                PermissionLevel.PUBLIC,
                time="1min",
                tokens=5000,
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="COPILOT explains its reasoning for any action",
            )
        )
        self.register(
            _cmd(
                "copilot decide",
                ["/cd"],
                "copilot",
                "COPILOT decision analysis",
                PermissionLevel.OPERATOR,
                time="2min",
                tokens=10000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="COPILOT evaluates options and recommends the best path",
            )
        )
        self.register(
            _cmd(
                "copilot critique",
                ["/cc"],
                "copilot",
                "COPILOT critical review",
                PermissionLevel.OPERATOR,
                time="2min",
                tokens=8000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="COPILOT provides constructive criticism of work",
            )
        )
        self.register(
            _cmd(
                "copilot learn",
                ["/clr"],
                "copilot",
                "COPILOT outcome learning",
                PermissionLevel.SYSTEM,
                time="3min",
                tokens=20000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="COPILOT learns from outcomes to improve future decisions",
            )
        )
        self.register(
            _cmd(
                "copilot simulate",
                ["/cs"],
                "copilot",
                "COPILOT strategy simulation",
                PermissionLevel.OPERATOR,
                time="2min",
                tokens=10000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="COPILOT simulates a strategy to predict outcomes",
            )
        )
        self.register(
            _cmd(
                "copilot status",
                ["/cst"],
                "copilot",
                "COPILOT status report",
                PermissionLevel.PUBLIC,
                time="5s",
                tokens=500,
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Shows COPILOT agent status and capabilities",
            )
        )

        # ── D — Execution Platform (9) ──────────────────────────
        self.register(
            _cmd(
                "workflow",
                ["/wf"],
                "execution",
                "Manage workflows",
                PermissionLevel.OPERATOR,
                time="1min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="List, create, or inspect workflows",
            )
        )
        self.register(
            _cmd(
                "workflow run",
                ["/wfr"],
                "execution",
                "Run a workflow",
                PermissionLevel.OPERATOR,
                time="variable",
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Executes a compiled workflow",
            )
        )
        self.register(
            _cmd(
                "compile",
                ["/cpl"],
                "execution",
                "Compile a workflow",
                PermissionLevel.OPERATOR,
                time="30s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Compiles intent into executable workflow",
            )
        )
        self.register(
            _cmd(
                "validate wf",
                ["/vw"],
                "execution",
                "Validate a workflow",
                PermissionLevel.OPERATOR,
                time="20s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Checks workflow for correctness",
            )
        )
        self.register(
            _cmd(
                "run",
                ["/rn"],
                "execution",
                "Run an ad-hoc task",
                PermissionLevel.OPERATOR,
                time="variable",
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Executes a task directly",
            )
        )
        self.register(
            _cmd(
                "replay",
                ["/rp"],
                "execution",
                "Replay an execution",
                PermissionLevel.ADMIN,
                time="30s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Replays a previous execution step by step",
            )
        )
        self.register(
            _cmd(
                "checkpoint",
                ["/ch"],
                "execution",
                "Manage checkpoints",
                PermissionLevel.SYSTEM,
                time="10s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Save, list, or restore execution checkpoints",
            )
        )
        self.register(
            _cmd(
                "rollback",
                ["/rb"],
                "execution",
                "Rollback execution",
                PermissionLevel.DANGEROUS,
                time="30s",
                risk="critical",
                flags=_UNIVERSAL_FLAGS,
                why="Rolls back to a previous checkpoint",
            )
        )
        self.register(
            _cmd(
                "metrics",
                ["/mt"],
                "execution",
                "Execution metrics",
                PermissionLevel.PUBLIC,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Shows execution performance metrics",
            )
        )

        # ── E — Runtime & System (8) ────────────────────────────
        self.register(
            _cmd(
                "status",
                ["/st"],
                "runtime",
                "System status overview",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Shows all services, load, and recent activity",
            )
        )
        self.register(
            _cmd(
                "health",
                ["/h"],
                "runtime",
                "System health check",
                PermissionLevel.PUBLIC,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Runs health checks across all subsystems",
            )
        )
        self.register(
            _cmd(
                "jobs",
                ["/jb"],
                "runtime",
                "Active jobs",
                PermissionLevel.OPERATOR,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Lists running and queued jobs",
            )
        )
        self.register(
            _cmd(
                "resources",
                ["/rs"],
                "runtime",
                "Resource usage",
                PermissionLevel.ADMIN,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Shows CPU, RAM, disk, network usage",
            )
        )
        self.register(
            _cmd(
                "events",
                ["/ev"],
                "runtime",
                "Event system browser",
                PermissionLevel.OPERATOR,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Browse recent events or search by type",
            )
        )
        self.register(
            _cmd(
                "journal",
                ["/jn"],
                "runtime",
                "Execution journal",
                PermissionLevel.ADMIN,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Inspect execution journal entries",
            )
        )
        self.register(
            _cmd(
                "queue",
                ["/qu"],
                "runtime",
                "Task queue status",
                PermissionLevel.OPERATOR,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Shows pending and active task queue",
            )
        )
        self.register(
            _cmd(
                "scheduler",
                ["/sch"],
                "runtime",
                "Scheduler status",
                PermissionLevel.ADMIN,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Shows scheduled jobs and worker status",
            )
        )

        # ── F — Knowledge Graph (5) ─────────────────────────────
        self.register(
            _cmd(
                "kg search",
                ["/ks"],
                "knowledge",
                "Search knowledge graph",
                PermissionLevel.PUBLIC,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Search nodes by type, pattern, or attributes",
            )
        )
        self.register(
            _cmd(
                "kg explain",
                ["/ke"],
                "knowledge",
                "Explain node context",
                PermissionLevel.PUBLIC,
                time="15s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Shows full context around a node",
            )
        )
        self.register(
            _cmd(
                "kg neighbors",
                ["/kn"],
                "knowledge",
                "Find node neighbors",
                PermissionLevel.PUBLIC,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Shows direct connections of a node",
            )
        )
        self.register(
            _cmd(
                "kg path",
                ["/kp"],
                "knowledge",
                "Find path between nodes",
                PermissionLevel.PUBLIC,
                time="15s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Finds shortest path between two nodes",
            )
        )
        self.register(
            _cmd(
                "kg stats",
                ["/kg"],
                "knowledge",
                "Knowledge graph stats",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Shows node/edge counts and graph health",
            )
        )

        # ── G — Event System (5) ────────────────────────────────
        self.register(
            _cmd(
                "events recent",
                ["/er"],
                "events",
                "Recent events",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Lists most recent events",
            )
        )
        self.register(
            _cmd(
                "events replay",
                ["/erp"],
                "events",
                "Replay events",
                PermissionLevel.ADMIN,
                time="20s",
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Replays events by correlation or execution",
            )
        )
        self.register(
            _cmd(
                "events search",
                ["/es"],
                "events",
                "Search events",
                PermissionLevel.OPERATOR,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Search events by type, source, or time range",
            )
        )
        self.register(
            _cmd(
                "events trace",
                ["/et"],
                "events",
                "Trace correlation ID",
                PermissionLevel.OPERATOR,
                time="15s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Trace all events sharing a correlation ID",
            )
        )
        self.register(
            _cmd(
                "events stats",
                ["/est"],
                "events",
                "Event statistics",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Event volume stats by period",
            )
        )

        # ── H — Testing (7) ─────────────────────────────────────
        self.register(
            _cmd(
                "test",
                ["/t"],
                "testing",
                "Run tests",
                PermissionLevel.OPERATOR,
                time="2min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Runs test suite with smart defaults",
            )
        )
        self.register(
            _cmd(
                "test quick",
                ["/tq"],
                "testing",
                "Quick test run",
                PermissionLevel.OPERATOR,
                time="30s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Fast test run on changed files",
            )
        )
        self.register(
            _cmd(
                "test module",
                ["/tm"],
                "testing",
                "Test specific module",
                PermissionLevel.OPERATOR,
                time="1min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run tests for a specific module",
            )
        )
        self.register(
            _cmd(
                "test runtime",
                ["/tr"],
                "testing",
                "Test runtime execution",
                PermissionLevel.OPERATOR,
                time="1min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run execution runtime tests",
            )
        )
        self.register(
            _cmd(
                "test security",
                ["/ts"],
                "testing",
                "Security tests",
                PermissionLevel.ADMIN,
                time="3min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run security-focused test suite",
            )
        )
        self.register(
            _cmd(
                "test regression",
                ["/tg"],
                "testing",
                "Regression tests",
                PermissionLevel.ADMIN,
                time="5min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run full regression suite against baseline",
            )
        )
        self.register(
            _cmd(
                "test coverage",
                ["/tc"],
                "testing",
                "Test coverage report",
                PermissionLevel.OPERATOR,
                time="30s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Show code coverage metrics",
            )
        )

        # ── I — Linting & Quality (7) ───────────────────────────
        self.register(
            _cmd(
                "ruff",
                ["/r"],
                "quality",
                "Run Ruff linter",
                PermissionLevel.OPERATOR,
                time="30s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Lint Python code with Ruff",
            )
        )
        self.register(
            _cmd(
                "lint",
                ["/l"],
                "quality",
                "Run linters",
                PermissionLevel.OPERATOR,
                time="30s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run all configured linters",
            )
        )
        self.register(
            _cmd(
                "types",
                ["/ty"],
                "quality",
                "Type checking",
                PermissionLevel.OPERATOR,
                time="1min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run mypy type checker",
            )
        )
        self.register(
            _cmd(
                "security",
                ["/sec"],
                "quality",
                "Security scan",
                PermissionLevel.ADMIN,
                time="3min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run security analysis tools",
            )
        )
        self.register(
            _cmd(
                "performance",
                ["/perf"],
                "quality",
                "Performance benchmark",
                PermissionLevel.ADMIN,
                time="2min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run performance benchmarks",
            )
        )
        self.register(
            _cmd(
                "coverage",
                ["/cov"],
                "quality",
                "Coverage report",
                PermissionLevel.OPERATOR,
                time="30s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Show test coverage",
            )
        )
        self.register(
            _cmd(
                "quality",
                ["/q"],
                "quality",
                "Quality gate",
                PermissionLevel.OPERATOR,
                time="2min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run quality gate checks",
            )
        )

        # ── J — Documentation (5) ───────────────────────────────
        self.register(
            _cmd(
                "docs",
                ["/d"],
                "documentation",
                "View documentation",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Show documentation for a module",
            )
        )
        self.register(
            _cmd(
                "docs build",
                ["/dbd"],
                "documentation",
                "Build documentation",
                PermissionLevel.ADMIN,
                time="2min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Generate documentation from source",
            )
        )
        self.register(
            _cmd(
                "docs module",
                ["/dm"],
                "documentation",
                "Module documentation",
                PermissionLevel.PUBLIC,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Show documentation for specific module",
            )
        )
        self.register(
            _cmd(
                "docs api",
                ["/da"],
                "documentation",
                "API documentation",
                PermissionLevel.PUBLIC,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Show API reference documentation",
            )
        )
        self.register(
            _cmd(
                "docs search",
                ["/ds"],
                "documentation",
                "Search documentation",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Search across all documentation",
            )
        )

        # ── K — Setup & Config (6) ─────────────────────────────
        self.register(
            _cmd(
                "setup",
                ["/s"],
                "setup",
                "System setup status",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Show setup status and configuration",
            )
        )
        self.register(
            _cmd(
                "setup wizard",
                ["/sw"],
                "setup",
                "Configuration wizard",
                PermissionLevel.OPERATOR,
                time="2min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run guided setup wizard",
            )
        )
        self.register(
            _cmd(
                "setup doctor",
                ["/sd"],
                "setup",
                "System diagnostics",
                PermissionLevel.ADMIN,
                time="1min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Run system diagnostics and health checks",
            )
        )
        self.register(
            _cmd(
                "setup repair",
                ["/sr"],
                "setup",
                "Repair system setup",
                PermissionLevel.DANGEROUS,
                time="2min",
                risk="high",
                flags=_UNIVERSAL_FLAGS,
                why="Attempt to repair system configuration",
            )
        )
        self.register(
            _cmd(
                "setup validate",
                ["/sv"],
                "setup",
                "Validate setup",
                PermissionLevel.PUBLIC,
                time="30s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Validate system configuration",
            )
        )
        self.register(
            _cmd(
                "setup context",
                ["/sctx"],
                "setup",
                "Manage session context",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Get/set/clear persistent context variables",
            )
        )

        # ── L — Integrations (7) ────────────────────────────────
        self.register(
            _cmd(
                "integrations",
                ["/i"],
                "integrations",
                "List integrations",
                PermissionLevel.PUBLIC,
                time="10s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="List all integrations with status",
            )
        )
        self.register(
            _cmd(
                "integrations test",
                ["/it"],
                "integrations",
                "Test integration",
                PermissionLevel.OPERATOR,
                time="30s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Test connection for a specific integration",
            )
        )
        self.register(
            _cmd(
                "integrations setup",
                ["/is"],
                "integrations",
                "Setup integration",
                PermissionLevel.OPERATOR,
                time="1min",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Setup wizard for a specific integration",
            )
        )
        self.register(
            _cmd(
                "outlook",
                ["/ol"],
                "integrations",
                "Outlook integration",
                PermissionLevel.OPERATOR,
                time="10s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Check Outlook status or sync",
            )
        )
        self.register(
            _cmd(
                "arca",
                ["/ar"],
                "integrations",
                "ARCA integration",
                PermissionLevel.OPERATOR,
                time="10s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Check ARCA status or sync",
            )
        )
        self.register(
            _cmd(
                "mode",
                ["/m"],
                "integrations",
                "Set work mode",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Switch between developer/hunter/architect/admin/auditor",
            )
        )
        self.register(
            _cmd(
                "profile",
                ["/pf"],
                "integrations",
                "User profile",
                PermissionLevel.PUBLIC,
                time="5s",
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Show or switch user profile",
            )
        )

        # ── M — Intelligence & Strategy (9) ─────────────────────
        self.register(
            _cmd(
                "strategy",
                ["/stg"],
                "intelligence",
                "Strategy analysis",
                PermissionLevel.OPERATOR,
                time="2min",
                tokens=10000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Analyze current strategy and suggest improvements",
            )
        )
        self.register(
            _cmd(
                "priorities",
                ["/pr"],
                "intelligence",
                "Show priorities",
                PermissionLevel.PUBLIC,
                time="10s",
                tokens=1000,
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Show prioritized task list",
            )
        )
        self.register(
            _cmd(
                "revenue",
                ["/$"],
                "intelligence",
                "Revenue analysis",
                PermissionLevel.OPERATOR,
                time="1min",
                tokens=5000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Revenue breakdown by target, type, program",
            )
        )
        self.register(
            _cmd(
                "opportunities",
                ["/opp"],
                "intelligence",
                "Find opportunities",
                PermissionLevel.OPERATOR,
                time="1min",
                tokens=5000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Identify high-value opportunities",
            )
        )
        self.register(
            _cmd(
                "improve",
                ["/im"],
                "intelligence",
                "Suggest improvements",
                PermissionLevel.OPERATOR,
                time="2min",
                tokens=8000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Analyze and suggest system improvements",
            )
        )
        self.register(
            _cmd(
                "learn",
                ["/lr"],
                "intelligence",
                "System learning",
                PermissionLevel.SYSTEM,
                time="3min",
                tokens=20000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Learn from outcomes and update models",
            )
        )
        self.register(
            _cmd(
                "decisions",
                ["/dc"],
                "intelligence",
                "Decision history",
                PermissionLevel.PUBLIC,
                time="10s",
                tokens=1000,
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Browse recent COPILOT decisions",
            )
        )
        self.register(
            _cmd(
                "next",
                ["/nx"],
                "intelligence",
                "Next recommended action",
                PermissionLevel.OPERATOR,
                time="30s",
                tokens=5000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="ORION recommends the single most impactful next action",
            )
        )
        self.register(
            _cmd(
                "goal",
                ["/g"],
                "intelligence",
                "Manage goals",
                PermissionLevel.OPERATOR,
                time="variable",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="List, set, or check progress on goals",
            )
        )

        # ── N — Smart Commands (9) ──────────────────────────────
        self.register(
            _cmd(
                "ship",
                ["/sh"],
                "smart",
                "Full release gate",
                PermissionLevel.ADMIN,
                time="5min",
                money="$0.05",
                risk="high",
                flags=_UNIVERSAL_FLAGS,
                why="Complete release pipeline: lint → test → audit → security → docs → changelog",
            )
        )
        self.register(
            _cmd(
                "audit all",
                ["/aa"],
                "smart",
                "Full system audit",
                PermissionLevel.ADMIN,
                time="5min",
                tokens=25000,
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Comprehensive system-wide audit",
            )
        )
        self.register(
            _cmd(
                "ready",
                ["/rd"],
                "smart",
                "Release readiness check",
                PermissionLevel.ADMIN,
                time="3min",
                tokens=15000,
                risk="medium",
                flags=_UNIVERSAL_FLAGS,
                why="Check if system is ready for release",
            )
        )
        self.register(
            _cmd(
                "money",
                ["/$$"],
                "smart",
                "Revenue intelligence",
                PermissionLevel.OPERATOR,
                time="2min",
                tokens=10000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Full revenue analysis and opportunity mapping",
            )
        )
        self.register(
            _cmd(
                "doctor",
                ["/dr"],
                "smart",
                "System diagnosis",
                PermissionLevel.ADMIN,
                time="3min",
                tokens=10000,
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="System diagnostics with repair recommendations",
            )
        )
        self.register(
            _cmd(
                "morning",
                ["/am"],
                "smart",
                "Morning briefing",
                PermissionLevel.PUBLIC,
                time="30s",
                tokens=5000,
                risk="none",
                flags=_UNIVERSAL_FLAGS,
                why="Daily briefing: health → status → priorities → improvements → next",
            )
        )
        self.register(
            _cmd(
                "hunt",
                ["/ht"],
                "smart",
                "Full hunt cycle",
                PermissionLevel.OPERATOR,
                time="15min",
                money="$0.20",
                risk="high",
                flags=_UNIVERSAL_FLAGS,
                why="Complete bug bounty cycle: recon → attack → validate → evidence → report",
            )
        )
        self.register(
            _cmd(
                "quick_test",
                ["/qt"],
                "smart",
                "Quick test pass",
                PermissionLevel.OPERATOR,
                time="30s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Quick lint + test on a path",
            )
        )
        self.register(
            _cmd(
                "changelog",
                ["/cl"],
                "smart",
                "Generate changelog",
                PermissionLevel.ADMIN,
                time="10s",
                risk="low",
                flags=_UNIVERSAL_FLAGS,
                why="Generate changelog since last release",
            )
        )

        logger.info("Registered %d commands in %d categories", self.count(), len(self.categories()))


# ── Singleton ────────────────────────────────────────

_registry: CommandRegistry | None = None


def get_command_registry() -> CommandRegistry:
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
    return _registry


def reset_command_registry() -> None:
    global _registry
    _registry = None
