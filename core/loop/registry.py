"""OWNEX Loop Pattern Registry — YAML-backed pattern definitions.

Stores loop-engineering patterns that map to OWNEX Work Cycles.

Usage:
    from core.loop.registry import registry

    for p in registry.get_patterns():
        engine = LoopEngine(p, scheduler, event_bus)

    # Register OWNEX patterns
    registry.register(mi_pattern)
"""

from __future__ import annotations

import logging
from typing import Any

from core.loop.models import (
    LoopPattern,
    PatternRisk,
    Phase,
    Skill,
    ownex_pattern,
)

logger = logging.getLogger("orion.core.loop.registry")

_DEFAULT_PATTERNS: list[LoopPattern] = []
_REGISTRY: dict[str, LoopPattern] = {}


def _build_defaults() -> None:
    """Build the default set of OWNEX-specific loop patterns.

    Each pattern maps to an OWNEX Work Cycle and follows the
    loop-engineering pattern format from registry.yaml.
    """
    global _DEFAULT_PATTERNS

    if _DEFAULT_PATTERNS:
        return

    _DEFAULT_PATTERNS = [
        # ── Security Cycle (CATEYE) ──────────────────────────────
        ownex_pattern(
            pattern_id="ownex:security",
            name="Security Triage Cycle",
            goal="Daily vulnerability triage: scan findings, validate, prioritize, escalate",
            cadence="1d",
            app_id="cateye",
            risk="high",
            skills=[
                Skill("finding-triage", "Scan and classify new security findings"),
                Skill("evidence-quality", "Score evidence quality for each finding"),
                Skill("report-draft", "Draft validation reports for confirmed findings"),
                Skill("priority-score", "Compute priority based on CVSS + context"),
            ],
            phases=["report", "discover", "triage", "classify", "act", "notify"],
            human_gates=[
                "critical-findings",
                "payout-decisions",
                "program-boundary-decisions",
            ],
        ),
        # ── Forge Cycle (bounty PR management) ───────────────────
        ownex_pattern(
            pattern_id="ownex:forge",
            name="Bounty Forge Cycle",
            goal="Process incoming bounty reports: triage, validate, reward track",
            cadence="2h",
            app_id="forge",
            risk="medium",
            skills=[
                Skill("bounty-triage", "Triage incoming bounty submissions"),
                Skill("scope-check", "Validate target scope and program rules"),
                Skill("evidence-verify", "Verify reproducibility and evidence quality"),
                Skill("reward-calc", "Calculate reward based on severity + program"),
            ],
            phases=["discover", "triage", "classify", "verify", "act", "notify"],
            human_gates=[
                "high-reward",
                "out-of-scope-decisions",
                "dispute-resolution",
            ],
        ),
        # ── Pulse Cycle (monitoring + alerts) ────────────────────
        ownex_pattern(
            pattern_id="ownex:pulse",
            name="System Pulse Cycle",
            goal="Monitor system health, detect anomalies, trigger alerts",
            cadence="5m",
            app_id="pulse",
            risk="medium",
            skills=[
                Skill("health-check", "Run health checks on all subsystems"),
                Skill("anomaly-detect", "Detect anomalous patterns in metrics"),
                Skill("alert-routing", "Route alerts to appropriate channels"),
            ],
            phases=["discover", "triage", "classify", "notify"],
            human_gates=["critical-alerts", "infra-failures"],
        ),
        # ── Vault Cycle (data persistence + backup) ──────────────
        ownex_pattern(
            pattern_id="ownex:vault",
            name="Data Vault Cycle",
            goal="Verify data integrity, run backups, rotate credentials",
            cadence="6h",
            app_id="vault",
            risk="low",
            skills=[
                Skill("integrity-check", "Verify database integrity and consistency"),
                Skill("backup-verify", "Verify recent backup completeness"),
                Skill("credential-rotate", "Rotate expiring credentials"),
            ],
            phases=["discover", "triage", "act", "verify", "notify"],
            human_gates=["credential-rotation", "data-restoration"],
        ),
        # ── Atlas Cycle (portfolio + targets) ────────────────────
        ownex_pattern(
            pattern_id="ownex:atlas",
            name="Target Intelligence Cycle",
            goal="Discover new targets, update intelligence, expand coverage",
            cadence="1d",
            app_id="atlas",
            risk="low",
            skills=[
                Skill("target-discover", "Discover new potential targets"),
                Skill("intel-update", "Update target intelligence profiles"),
                Skill("coverage-scan", "Scan for coverage gaps"),
            ],
            phases=["discover", "triage", "classify", "report"],
            human_gates=["new-target-approval", "program-changes"],
        ),
        # ── Oddysey Cycle (long-running campaigns) ───────────────
        ownex_pattern(
            pattern_id="ownex:odyssey",
            name="Campaign Execution Cycle",
            goal="Execute long-running focused campaigns on specific targets",
            cadence="1d",
            app_id="odyssey",
            risk="medium",
            skills=[
                Skill("campaign-plan", "Plan the campaign execution steps"),
                Skill("recon-run", "Run reconnaissance against target"),
                Skill("finding-collect", "Collect and organize findings"),
                Skill("progress-track", "Track campaign progress and metrics"),
            ],
            phases=["report", "discover", "triage", "act", "verify", "review"],
            human_gates=["campaign-scope", "critical-discoveries", "resource-allocation"],
        ),
    ]


class PatternRegistry:
    """Registry of loop patterns for the OWNEX ecosystem.

    Thread-safe by design: patterns are loaded once at startup
    and are read-only after that.
    """

    def __init__(self, patterns: list[LoopPattern] | None = None) -> None:
        self._patterns: dict[str, LoopPattern] = {}
        if patterns:
            for p in patterns:
                self._patterns[p.id] = p

    # ── Read ─────────────────────────────────────────────────────

    def get(self, pattern_id: str) -> LoopPattern | None:
        """Get a pattern by ID."""
        return self._patterns.get(pattern_id)

    def get_all(self) -> list[LoopPattern]:
        """Get all registered patterns."""
        return list(self._patterns.values())

    def get_by_app(self, app_id: str) -> list[LoopPattern]:
        """Get all patterns for a given app."""
        return [p for p in self._patterns.values() if p.app_id == app_id]

    def count(self) -> int:
        return len(self._patterns)

    def ids(self) -> list[str]:
        return list(self._patterns.keys())

    # ── Write ────────────────────────────────────────────────────

    def register(self, pattern: LoopPattern) -> None:
        """Register a pattern."""
        self._patterns[pattern.id] = pattern
        logger.info("Registered loop pattern: %s (%s)", pattern.id, pattern.name)

    def unregister(self, pattern_id: str) -> bool:
        """Remove a pattern. Returns True if existed."""
        return self._patterns.pop(pattern_id, None) is not None

    # ── Serialization ────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise all patterns for the health API."""
        return {
            "count": self.count(),
            "patterns": {pid: p.to_dict() for pid, p in self._patterns.items()},
        }


# ── Module-level singleton ────────────────────────────────────────

_registry_instance: PatternRegistry | None = None


def get_registry() -> PatternRegistry:
    """Get the global pattern registry (initialises on first call)."""
    global _registry_instance
    if _registry_instance is None:
        _build_defaults()
        _registry_instance = PatternRegistry(_DEFAULT_PATTERNS)
        for p in _DEFAULT_PATTERNS:
            _REGISTRY[p.id] = p
        logger.info(
            "Initialised loop registry with %d OWNEX patterns",
            len(_DEFAULT_PATTERNS),
        )
    return _registry_instance


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry_instance
    _registry_instance = None
    _DEFAULT_PATTERNS.clear()


def get_ownex_patterns() -> list[LoopPattern]:
    """Convenience: get all OWNEX default patterns."""
    _build_defaults()
    return list(_DEFAULT_PATTERNS)


def register_ownex_patterns(registry: PatternRegistry) -> None:
    """Register all default OWNEX patterns into an existing registry."""
    for p in get_ownex_patterns():
        registry.register(p)


# ── YAML import helper ────────────────────────────────────────────


def load_from_yaml(path: str) -> list[LoopPattern]:
    """Load patterns from a YAML registry file (matches loop-engineering format).

    The YAML format matches patterns/registry.yaml from loop-engineering:
    ```yaml
    patterns:
      - id: daily-triage
        name: Daily Triage
        goal: ...
        cadence: 1d
        ...
    ```
    """
    import yaml  # lazy import — not a core dependency

    with open(path) as f:
        data = yaml.safe_load(f)

    patterns: list[LoopPattern] = []
    for entry in data.get("patterns", []):
        pattern = LoopPattern(
            id=entry["id"],
            name=entry["name"],
            goal=entry["goal"],
            cadence=entry.get("cadence", "1d"),
            risk=PatternRisk(entry.get("risk", "low")),
            skills=[Skill(name=s, description="") for s in entry.get("skills", [])],
            phases=[Phase(p) for p in entry.get("phases", ["report"])],
            human_gates=entry.get("human_gates", []),
            week_one_mode=entry.get("week_one_mode", "L1"),
        )
        patterns.append(pattern)

    return patterns
