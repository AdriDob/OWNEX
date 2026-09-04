"""Mode Engine — Makes LITE/FULL/CAPITAL actually behave differently.

Each mode changes:
- What data is shown
- What actions are recommended
- What notifications are sent
- What the scheduler prioritizes
- What the UI focuses on
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.modes.engine")


class OwnexMode(StrEnum):
    """The three operational modes."""

    LITE = "lite"
    FULL = "full"
    CAPITAL = "capital"


@dataclass
class ModeConfig:
    """Configuration for a specific mode."""

    mode: OwnexMode
    name: str
    tagline: str
    question: str  # The main question this mode answers

    # What to show
    show_opportunities: bool = True
    show_agents: bool = False
    show_finance: bool = False
    show_goals: bool = False
    show_scheduler: bool = False
    show_notifications: bool = True
    show_next_action: bool = True
    show_capital: bool = False
    show_income: bool = False
    show_findings: bool = False
    show_reports: bool = False
    show_settings: bool = False

    # What to prioritize
    prioritize_ev: bool = True
    prioritize_revenue: bool = False
    prioritize_capital: bool = False
    prioritize_system: bool = False

    # Notification level
    notify_level: str = "high"  # critical, high, medium, low

    # Scheduler focus
    scheduler_focus: str = "opportunity"  # opportunity, system, capital

    # UI density
    ui_density: str = "minimal"  # minimal, standard, detailed

    # Navigation
    nav_items: list[str] = field(default_factory=list)


# Mode configurations
MODE_CONFIGS: dict[OwnexMode, ModeConfig] = {
    OwnexMode.LITE: ModeConfig(
        mode=OwnexMode.LITE,
        name="LITE",
        tagline="EARN MORE",
        question="¿Cuál es la mejor acción económica que puedo realizar ahora?",
        show_opportunities=True,
        show_agents=False,
        show_finance=False,
        show_goals=False,
        show_scheduler=False,
        show_notifications=True,
        show_next_action=True,
        show_capital=False,
        show_income=True,
        show_findings=True,
        show_reports=False,
        show_settings=False,
        prioritize_ev=True,
        prioritize_revenue=True,
        prioritize_capital=False,
        prioritize_system=False,
        notify_level="high",
        scheduler_focus="opportunity",
        ui_density="minimal",
        nav_items=["today", "opportunities", "findings", "settings"],
    ),
    OwnexMode.FULL: ModeConfig(
        mode=OwnexMode.FULL,
        name="FULL",
        tagline="OPERATE EVERYTHING",
        question="¿Qué está pasando con todo mi sistema y qué debería hacer?",
        show_opportunities=True,
        show_agents=True,
        show_finance=True,
        show_goals=True,
        show_scheduler=True,
        show_notifications=True,
        show_next_action=True,
        show_capital=True,
        show_income=True,
        show_findings=True,
        show_reports=True,
        show_settings=True,
        prioritize_ev=True,
        prioritize_revenue=True,
        prioritize_capital=True,
        prioritize_system=True,
        notify_level="medium",
        scheduler_focus="system",
        ui_density="detailed",
        nav_items=["today", "opportunities", "agents", "finance", "goals", "scheduler", "settings"],
    ),
    OwnexMode.CAPITAL: ModeConfig(
        mode=OwnexMode.CAPITAL,
        name="CAPITAL",
        tagline="KEEP & COMPOUND",
        question="¿Cómo convierto lo que genero en patrimonio?",
        show_opportunities=False,
        show_agents=False,
        show_finance=True,
        show_goals=True,
        show_scheduler=False,
        show_notifications=True,
        show_next_action=False,
        show_capital=True,
        show_income=True,
        show_findings=False,
        show_reports=False,
        show_settings=False,
        prioritize_ev=False,
        prioritize_revenue=False,
        prioritize_capital=True,
        prioritize_system=False,
        notify_level="low",
        scheduler_focus="capital",
        ui_density="standard",
        nav_items=["today", "capital", "goals", "investments", "settings"],
    ),
}


@dataclass
class AdaptiveRecommendation:
    """Adaptive mode recommendation."""

    recommended_mode: OwnexMode
    reason: str
    confidence: float  # 0-1
    income_gap: float  # How far below income target
    capital_gap: float  # How far below capital target
    operational_load: float  # How busy the system is


class ModeEngine:
    """Engine that makes modes actually behave differently."""

    def __init__(self) -> None:
        self.current_mode: OwnexMode = OwnexMode.LITE
        self.configs = MODE_CONFIGS

    def get_config(self, mode: OwnexMode | None = None) -> ModeConfig:
        """Get config for a mode."""
        m = mode or self.current_mode
        return self.configs.get(m, self.configs[OwnexMode.LITE])

    def set_mode(self, mode: OwnexMode) -> ModeConfig:
        """Switch to a new mode."""
        old = self.current_mode
        self.current_mode = mode
        config = self.get_config(mode)
        logger.info("[MODE] Switched from %s to %s: %s", old, mode, config.tagline)
        return config

    def recommend_mode(
        self,
        monthly_income: float = 0,
        monthly_target: float = 5000,
        capital: float = 0,
        capital_target: float = 1_000_000,
        pending_findings: int = 0,
        active_agents: int = 0,
        pending_approvals: int = 0,
    ) -> AdaptiveRecommendation:
        """Recommend the best mode based on current state."""
        income_gap = max(monthly_target - monthly_income, 0)
        capital_gap = max(capital_target - capital, 0)
        operational_load = min((pending_findings + active_agents + pending_approvals) / 10, 1.0)

        # Decision logic
        if income_gap > monthly_target * 0.5:
            # Income is very low → LITE
            return AdaptiveRecommendation(
                recommended_mode=OwnexMode.LITE,
                reason=f"Monthly income (${monthly_income:,.0f}) is below target by ${income_gap:,.0f}. Focus on highest-EV opportunities.",
                confidence=0.9,
                income_gap=income_gap,
                capital_gap=capital_gap,
                operational_load=operational_load,
            )
        elif capital_gap > capital_target * 0.9 and monthly_income > monthly_target * 0.5:
            # Income is OK but capital is low → CAPITAL
            return AdaptiveRecommendation(
                recommended_mode=OwnexMode.CAPITAL,
                reason=f"Capital (${capital:,.0f}) is far from $1M. Focus on savings and investment.",
                confidence=0.8,
                income_gap=income_gap,
                capital_gap=capital_gap,
                operational_load=operational_load,
            )
        elif operational_load > 0.7 or pending_approvals > 5:
            # High operational load → FULL
            return AdaptiveRecommendation(
                recommended_mode=OwnexMode.FULL,
                reason=f"System has {pending_findings} findings, {active_agents} agents, {pending_approvals} approvals pending. Needs attention.",
                confidence=0.85,
                income_gap=income_gap,
                capital_gap=capital_gap,
                operational_load=operational_load,
            )
        else:
            # Default → LITE (simplest)
            return AdaptiveRecommendation(
                recommended_mode=OwnexMode.LITE,
                reason="System healthy. Focus on next best action.",
                confidence=0.7,
                income_gap=income_gap,
                capital_gap=capital_gap,
                operational_load=operational_load,
            )

    def filter_data(self, data: dict[str, Any], mode: OwnexMode | None = None) -> dict[str, Any]:
        """Filter data based on mode configuration."""
        config = self.get_config(mode)
        filtered = {}

        if config.show_opportunities and "opportunities" in data:
            filtered["opportunities"] = data["opportunities"]

        if config.show_agents and "agents" in data:
            filtered["agents"] = data["agents"]

        if config.show_finance and "finance" in data:
            filtered["finance"] = data["finance"]

        if config.show_goals and "goals" in data:
            filtered["goals"] = data["goals"]

        if config.show_capital and "capital" in data:
            filtered["capital"] = data["capital"]

        if config.show_income and "income" in data:
            filtered["income"] = data["income"]

        if config.show_findings and "findings" in data:
            filtered["findings"] = data["findings"]

        if config.show_reports and "reports" in data:
            filtered["reports"] = data["reports"]

        if config.show_next_action and "next_action" in data:
            filtered["next_action"] = data["next_action"]

        # Always include
        filtered["mode"] = config.name
        filtered["tagline"] = config.tagline
        filtered["question"] = config.question

        return filtered

    def get_nav_items(self, mode: OwnexMode | None = None) -> list[str]:
        """Get navigation items for a mode."""
        config = self.get_config(mode)
        return config.nav_items

    def to_dict(self) -> dict[str, Any]:
        """Serialize mode engine state."""
        config = self.get_config()
        return {
            "current_mode": self.current_mode.value,
            "config": {
                "name": config.name,
                "tagline": config.tagline,
                "question": config.question,
                "nav_items": config.nav_items,
                "ui_density": config.ui_density,
            },
            "available_modes": [
                {
                    "mode": m.value,
                    "name": c.name,
                    "tagline": c.tagline,
                    "question": c.question,
                }
                for m, c in self.configs.items()
            ],
        }


# Singleton
_mode_engine: ModeEngine | None = None


def get_mode_engine() -> ModeEngine:
    """Get or create the global mode engine."""
    global _mode_engine
    if _mode_engine is None:
        _mode_engine = ModeEngine()
    return _mode_engine
