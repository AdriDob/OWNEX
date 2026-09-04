"""Mode Manager — Centralized intelligent mode management.

This system manages all OWNEX modes with conflict detection and compatibility rules:
- IncomeMode (revenue): ULTRA_FAST, BALANCED, SCALING
- OWNEXMode (general): MANUAL, AUTOMATIC
- TradingMode (trading): REAL, DRY_RUN, PAPER_TRADING
- AssistanceMode (assistance): GUIDED, ASSISTED, AUTONOMOUS, EXPERT
- WorkMode (work): BUG_BOUNTY, INVESTMENT, TRADING, etc.

Features:
- Centralized mode storage
- Compatibility rules between modes
- Conflict detection before activation
- Auto-resolution of conflicts
- History of mode changes
- Validation rules
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.mode_manager")


class ModeType(StrEnum):
    """Categories of modes."""

    INCOME = "income"
    GENERAL = "general"
    TRADING = "trading"
    ASSISTANCE = "assistance"
    WORK = "work"
    VOICE = "voice"
    DECISION = "decision"
    RUNTIME = "runtime"
    PRIMARY = "primary"


class ModeValue(StrEnum):
    """All possible mode values."""

    # Income Mode
    INCOME_ULTRA_FAST = "ultra_fast"
    INCOME_BALANCED = "balanced"
    INCOME_SCALING = "scaling"

    # General Mode
    GENERAL_MANUAL = "manual"
    GENERAL_AUTOMATIC = "automatic"

    # Trading Mode
    TRADING_REAL = "real"
    TRADING_DRY_RUN = "dry_run"
    TRADING_PAPER_TRADING = "paper_trading"

    # Assistance Mode
    ASSISTANCE_GUIDED = "guided"
    ASSISTANCE_ASSISTED = "assisted"
    ASSISTANCE_AUTONOMOUS = "autonomous"
    ASSISTANCE_EXPERT = "expert"

    # Work Mode
    WORK_BUG_BOUNTY = "bug_bounty"
    WORK_INVESTMENT = "investment"
    WORK_TRADING = "trading"

    # Voice Mode
    VOICE_NORMAL = "normal"
    VOICE_VOICE_ONLY = "voice_only"
    VOICE_TEXT_ONLY = "text_only"
    VOICE_HYBRID = "hybrid"

    # Decision Mode
    DECISION_EXPLANATORY = "explanatory"
    DECISION_AUTOMATIC = "automatic"
    DECISION_EXPERT = "expert"

    # Primary Mode (3 operational modes)
    PRIMARY_LITE = "lite"
    PRIMARY_FULL = "full"
    PRIMARY_CAPITAL = "capital"


@dataclass
class ModeConfig:
    """Configuration for a single mode."""

    mode_type: ModeType
    mode_value: ModeValue
    name: str
    description: str
    category: str
    priority: int = 0  # Higher priority overrides lower
    mutually_exclusive_with: list[str] = field(default_factory=list)
    compatible_with: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)  # Other modes that must be active
    excludes: list[str] = field(default_factory=list)  # Other modes that must be inactive


# Mode configurations
MODE_CONFIGS: dict[str, ModeConfig] = {
    # Income Mode
    "income_ultra_fast": ModeConfig(
        mode_type=ModeType.INCOME,
        mode_value=ModeValue.INCOME_ULTRA_FAST,
        name="Ultra Fast",
        description="Phase 0 - Survival mode, solo categorías que pagan en días",
        category="Revenue",
        priority=1,
        mutually_exclusive_with=["income_balanced", "income_scaling"],
        compatible_with=["general_manual", "trading_dry_run", "trading_paper_trading"],
        excludes=["trading_real"],
    ),
    "income_balanced": ModeConfig(
        mode_type=ModeType.INCOME,
        mode_value=ModeValue.INCOME_BALANCED,
        name="Balanced",
        description="Phase 1-2 - Mix de velocidades de cobro",
        category="Revenue",
        priority=2,
        mutually_exclusive_with=["income_ultra_fast", "income_scaling"],
        compatible_with=["general_automatic", "trading_dry_run"],
        excludes=[],
    ),
    "income_scaling": ModeConfig(
        mode_type=ModeType.INCOME,
        mode_value=ModeValue.INCOME_SCALING,
        name="Scaling",
        description="Phase 3-4 - Alto valor, largo plazo",
        category="Revenue",
        priority=3,
        mutually_exclusive_with=["income_ultra_fast", "income_balanced"],
        compatible_with=["general_automatic", "trading_real"],
        requires=["general_automatic"],
        excludes=[],
    ),
    # General Mode
    "general_manual": ModeConfig(
        mode_type=ModeType.GENERAL,
        mode_value=ModeValue.GENERAL_MANUAL,
        name="Manual",
        description="Usuario controla todo manualmente",
        category="General",
        priority=10,
        mutually_exclusive_with=["general_automatic"],
        compatible_with=["income_ultra_fast", "income_balanced", "trading_dry_run"],
        excludes=["income_scaling"],
    ),
    "general_automatic": ModeConfig(
        mode_type=ModeType.GENERAL,
        mode_value=ModeValue.GENERAL_AUTOMATIC,
        name="Automatic",
        description="Sistema opera automáticamente",
        category="General",
        priority=10,
        mutually_exclusive_with=["general_manual"],
        compatible_with=["income_balanced", "income_scaling", "trading_real"],
        excludes=["income_ultra_fast"],
    ),
    # Trading Mode
    "trading_real": ModeConfig(
        mode_type=ModeType.TRADING,
        mode_value=ModeValue.TRADING_REAL,
        name="Real Trading",
        description="Trading real con dinero real",
        category="Trading",
        priority=20,
        mutually_exclusive_with=["trading_dry_run", "trading_paper_trading"],
        compatible_with=["income_scaling", "general_automatic"],
        requires=["general_automatic"],
        excludes=["income_ultra_fast"],
    ),
    "trading_dry_run": ModeConfig(
        mode_type=ModeType.TRADING,
        mode_value=ModeValue.TRADING_DRY_RUN,
        name="Dry Run",
        description="Simulación sin ejecución",
        category="Trading",
        priority=20,
        mutually_exclusive_with=["trading_real", "trading_paper_trading"],
        compatible_with=["income_ultra_fast", "income_balanced", "general_manual", "general_automatic"],
        excludes=[],
    ),
    "trading_paper_trading": ModeConfig(
        mode_type=ModeType.TRADING,
        mode_value=ModeValue.TRADING_PAPER_TRADING,
        name="Paper Trading",
        description="Trading de papel (simulación completa)",
        category="Trading",
        priority=20,
        mutually_exclusive_with=["trading_real", "trading_dry_run"],
        compatible_with=["income_ultra_fast", "income_balanced", "general_manual"],
        excludes=[],
    ),
    # Assistance Mode
    "assistance_guided": ModeConfig(
        mode_type=ModeType.ASSISTANCE,
        mode_value=ModeValue.ASSISTANCE_GUIDED,
        name="Guided",
        description="Sistema guía cada paso",
        category="Assistance",
        priority=30,
        mutually_exclusive_with=["assistance_assisted", "assistance_autonomous", "assistance_expert"],
        compatible_with=["general_manual"],
        excludes=["general_automatic"],
    ),
    "assistance_assisted": ModeConfig(
        mode_type=ModeType.ASSISTANCE,
        mode_value=ModeValue.ASSISTANCE_ASSISTED,
        name="Assisted",
        description="Sistema asiste cuando solicitado",
        category="Assistance",
        priority=30,
        mutually_exclusive_with=["assistance_guided", "assistance_autonomous", "assistance_expert"],
        compatible_with=["general_manual", "general_automatic"],
        excludes=[],
    ),
    "assistance_autonomous": ModeConfig(
        mode_type=ModeType.ASSISTANCE,
        mode_value=ModeValue.ASSISTANCE_AUTONOMOUS,
        name="Autonomous",
        description="Sistema opera solo",
        category="Assistance",
        priority=30,
        mutually_exclusive_with=["assistance_guided", "assistance_assisted", "assistance_expert"],
        compatible_with=["general_automatic"],
        requires=["general_automatic"],
        excludes=["general_manual"],
    ),
    "assistance_expert": ModeConfig(
        mode_type=ModeType.ASSISTANCE,
        mode_value=ModeValue.ASSISTANCE_EXPERT,
        name="Expert",
        description="Sistema como experto",
        category="Assistance",
        priority=30,
        mutually_exclusive_with=["assistance_guided", "assistance_assisted", "assistance_autonomous"],
        compatible_with=["general_automatic"],
        requires=["general_automatic"],
        excludes=["general_manual"],
    ),
    # Primary Mode (3 operational modes)
    "primary_lite": ModeConfig(
        mode_type=ModeType.PRIMARY,
        mode_value=ModeValue.PRIMARY_LITE,
        name="LITE",
        description="Earn More - Minimalista, next best action, maximizar EV/hora",
        category="Operational",
        priority=100,
        mutually_exclusive_with=["primary_full", "primary_capital"],
        compatible_with=["general_manual", "assistance_guided", "assistance_assisted"],
        excludes=["general_automatic"],
    ),
    "primary_full": ModeConfig(
        mode_type=ModeType.PRIMARY,
        mode_value=ModeValue.PRIMARY_FULL,
        name="FULL",
        description="Operate Everything - Completo, toda la complejidad visible",
        category="Operational",
        priority=100,
        mutually_exclusive_with=["primary_lite", "primary_capital"],
        compatible_with=["general_automatic", "assistance_autonomous", "assistance_expert"],
        requires=["general_automatic"],
        excludes=["general_manual"],
    ),
    "primary_capital": ModeConfig(
        mode_type=ModeType.PRIMARY,
        mode_value=ModeValue.PRIMARY_CAPITAL,
        name="CAPITAL",
        description="Keep & Compound - Patrimonio, asignación, proyección $1M",
        category="Operational",
        priority=100,
        mutually_exclusive_with=["primary_lite", "primary_full"],
        compatible_with=["general_automatic", "assistance_autonomous"],
        requires=["general_automatic"],
        excludes=["general_manual"],
    ),
}


@dataclass
class ModeChange:
    """Record of a mode change."""

    id: str
    mode_key: str
    old_value: str | None
    new_value: str
    timestamp: str
    auto_resolved: list[str] = field(default_factory=list)
    conflicts_detected: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mode_key": self.mode_key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp,
            "auto_resolved": self.auto_resolved,
            "conflicts_detected": self.conflicts_detected,
            "metadata": self.metadata,
        }


class ModeManager:
    """Centralized mode manager with conflict detection."""

    def __init__(self, state_file: Path = Path("data/mode_manager_state.json")):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._active_modes: dict[str, str] = {}  # mode_type -> mode_value
        self._history: list[ModeChange] = []
        self._load_state()

    def _load_state(self) -> None:
        """Load mode state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self._active_modes = data.get("active_modes", {})
                    history_data = data.get("history", [])
                    self._history = [
                        ModeChange(
                            id=h["id"],
                            mode_key=h["mode_key"],
                            old_value=h.get("old_value"),
                            new_value=h["new_value"],
                            timestamp=h["timestamp"],
                            auto_resolved=h.get("auto_resolved", []),
                            conflicts_detected=h.get("conflicts_detected", []),
                            metadata=h.get("metadata", {}),
                        )
                        for h in history_data
                    ]
                logger.info(f"Loaded mode manager state: {len(self._active_modes)} active modes")
            except Exception as e:
                logger.warning(f"Failed to load mode manager state: {e}")

    def _save_state(self) -> None:
        """Save mode state to disk."""
        try:
            data = {
                "active_modes": self._active_modes,
                "history": [h.to_dict() for h in self._history],
                "last_updated": datetime.now(UTC).isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved mode manager state")
        except Exception as e:
            logger.error(f"Failed to save mode manager state: {e}")

    def get_active_modes(self) -> dict[str, str]:
        """Get all currently active modes."""
        return self._active_modes.copy()

    def get_mode(self, mode_type: ModeType) -> str | None:
        """Get active mode for a type."""
        return self._active_modes.get(mode_type.value)

    def set_mode(self, mode_key: str, force: bool = False) -> dict[str, Any]:
        """Set a mode with conflict detection and auto-resolution.

        Args:
            mode_key: The mode key (e.g., "income_ultra_fast")
            force: If True, override conflicts (use with caution)

        Returns:
            Result with status, conflicts, auto-resolutions, and applied changes
        """
        if mode_key not in MODE_CONFIGS:
            return {
                "status": "error",
                "error": f"Unknown mode key: {mode_key}",
                "available_modes": list(MODE_CONFIGS.keys()),
            }

        config = MODE_CONFIGS[mode_key]
        mode_type = config.mode_type.value
        old_value = self._active_modes.get(mode_type)

        # Same mode, no change
        if old_value == config.mode_value.value:
            return {
                "status": "no_change",
                "message": f"Mode {mode_key} is already active",
                "active_modes": self._active_modes.copy(),
            }

        # Detect conflicts
        conflicts = self._detect_conflicts(mode_key, config)
        auto_resolved = []

        if conflicts and not force:
            return {
                "status": "conflict",
                "message": f"Cannot activate {mode_key} due to conflicts",
                "conflicts": conflicts,
                "suggested_resolution": self._suggest_resolution(mode_key, conflicts),
                "active_modes": self._active_modes.copy(),
            }

        # Auto-resolve conflicts if force=True
        if conflicts and force:
            auto_resolved = self._auto_resolve_conflicts(mode_key, conflicts)

        # Check requirements
        missing_requirements = self._check_requirements(mode_key, config)
        if missing_requirements:
            return {
                "status": "missing_requirements",
                "message": f"Cannot activate {mode_key} - missing requirements",
                "missing_requirements": missing_requirements,
                "active_modes": self._active_modes.copy(),
            }

        # Auto-activate requirements
        for req_mode_key in config.requires:
            req_config = MODE_CONFIGS[req_mode_key]
            self._active_modes[req_config.mode_type.value] = req_config.mode_value.value
            logger.info(f"Auto-activated requirement: {req_mode_key}")

        # Apply the mode
        self._active_modes[mode_type] = config.mode_value.value

        # Deactivate mutually exclusive modes
        for exclusive_key in config.mutually_exclusive_with:
            if exclusive_key in MODE_CONFIGS:
                excl_config = MODE_CONFIGS[exclusive_key]
                excl_type = excl_config.mode_type.value
                if excl_type in self._active_modes and self._active_modes[excl_type] == excl_config.mode_value.value:
                    del self._active_modes[excl_type]
                    logger.info(f"Deactivated mutually exclusive mode: {exclusive_key}")

        # Record change
        change = ModeChange(
            id=f"change-{int(datetime.now(UTC).timestamp() * 1000)}",
            mode_key=mode_key,
            old_value=old_value,
            new_value=config.mode_value.value,
            timestamp=datetime.now(UTC).isoformat(),
            auto_resolved=auto_resolved,
            conflicts_detected=conflicts,
        )
        self._history.append(change)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        self._save_state()

        return {
            "status": "success",
            "message": f"Activated {mode_key}",
            "active_modes": self._active_modes.copy(),
            "auto_resolved": auto_resolved,
            "conflicts_resolved": conflicts,
        }

    def _detect_conflicts(self, mode_key: str, config: ModeConfig) -> list[str]:
        """Detect conflicts with current active modes."""
        conflicts = []

        # Check mutually exclusive modes
        for exclusive_key in config.mutually_exclusive_with:
            if exclusive_key in MODE_CONFIGS:
                excl_config = MODE_CONFIGS[exclusive_key]
                excl_type = excl_config.mode_type.value
                if excl_type in self._active_modes and self._active_modes[excl_type] == excl_config.mode_value.value:
                    conflicts.append(exclusive_key)

        # Check excludes
        for exclude_key in config.excludes:
            if exclude_key in MODE_CONFIGS:
                excl_config = MODE_CONFIGS[exclude_key]
                excl_type = excl_config.mode_type.value
                if excl_type in self._active_modes and self._active_modes[excl_type] == excl_config.mode_value.value:
                    conflicts.append(exclude_key)

        return conflicts

    def _auto_resolve_conflicts(self, mode_key: str, conflicts: list[str]) -> list[str]:
        """Auto-resolve conflicts by deactivating conflicting modes."""
        resolved = []

        for conflict_key in conflicts:
            if conflict_key in MODE_CONFIGS:
                conflict_config = MODE_CONFIGS[conflict_key]
                conflict_type = conflict_config.mode_type.value
                if conflict_type in self._active_modes:
                    del self._active_modes[conflict_type]
                    resolved.append(conflict_key)
                    logger.info(f"Auto-resolved conflict: deactivated {conflict_key}")

        return resolved

    def _check_requirements(self, mode_key: str, config: ModeConfig) -> list[str]:
        """Check if required modes are active."""
        missing = []

        for req_mode_key in config.requires:
            if req_mode_key in MODE_CONFIGS:
                req_config = MODE_CONFIGS[req_mode_key]
                req_type = req_config.mode_type.value
                if req_type not in self._active_modes or self._active_modes[req_type] != req_config.mode_value.value:
                    missing.append(req_mode_key)

        return missing

    def _suggest_resolution(self, mode_key: str, conflicts: list[str]) -> dict[str, Any]:
        """Suggest how to resolve conflicts."""
        suggestions = []

        for conflict_key in conflicts:
            conflict_config = MODE_CONFIGS[conflict_key]
            suggestions.append(
                {
                    "conflict": conflict_key,
                    "conflict_name": conflict_config.name,
                    "action": "deactivate",
                    "reason": f"{mode_key} is mutually exclusive with {conflict_key}",
                }
            )

        return {
            "mode_key": mode_key,
            "total_conflicts": len(conflicts),
            "suggestions": suggestions,
        }

    def get_available_modes(self) -> dict[str, Any]:
        """Get all available modes with their status."""
        return {
            mode_key: {
                "name": config.name,
                "description": config.description,
                "category": config.category,
                "mode_type": config.mode_type.value,
                "mode_value": config.mode_value.value,
                "active": self._active_modes.get(config.mode_type.value) == config.mode_value.value,
                "mutually_exclusive_with": config.mutually_exclusive_with,
                "compatible_with": config.compatible_with,
                "requires": config.requires,
                "excludes": config.excludes,
            }
            for mode_key, config in MODE_CONFIGS.items()
        }

    def get_compatibility_matrix(self) -> dict[str, Any]:
        """Get compatibility matrix for all modes."""
        matrix = {}

        for mode_key, config in MODE_CONFIGS.items():
            matrix[mode_key] = {
                "compatible_with": config.compatible_with,
                "mutually_exclusive_with": config.mutually_exclusive_with,
                "requires": config.requires,
                "excludes": config.excludes,
            }

        return matrix

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get mode change history."""
        return [h.to_dict() for h in self._history[-limit:]]

    def get_status(self) -> dict[str, Any]:
        """Get current mode manager status."""
        return {
            "active_modes": self._active_modes.copy(),
            "total_active": len(self._active_modes),
            "available_modes": len(MODE_CONFIGS),
            "history_count": len(self._history),
            "last_updated": datetime.now(UTC).isoformat(),
        }


# Singleton instance
_global_mode_manager: ModeManager | None = None


def get_mode_manager() -> ModeManager:
    """Get or create the global mode manager."""
    global _global_mode_manager
    if _global_mode_manager is None:
        _global_mode_manager = ModeManager()
    return _global_mode_manager
