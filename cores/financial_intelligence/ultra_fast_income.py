"""Ultra Fast Income Mode — Survival-focused immediate cashflow generation.

This mode prioritizes only categories that pay in days (cash_speed >= 0.85):
- Data Annotation, AI Training, AI Evaluation, Synthetic Data (instant)
- Fiverr (1-2 days)
- Web Scraping, Prompt Engineering, QA Automation, Browser Automation (2-3 days)

Purpose: Generate immediate cashflow for survival before scaling to Phase 1+.
This is "Phase 0" in the progressive scaling system — survival mode.

Integration with Infinite Source Discovery and Auto-Apply for maximum automation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.financial_intelligence.auto_apply import get_auto_apply_system
from cores.financial_intelligence.infinite_source_discovery import (
    get_infinite_source_discovery,
)

logger = logging.getLogger("ownex.ultra_fast_income")


class IncomeMode(StrEnum):
    """Income generation modes."""

    ULTRA_FAST = "ultra_fast"  # Phase 0: Survival (cash_speed >= 0.85)
    BALANCED = "balanced"  # Phase 1-2: Mix of speeds
    SCALING = "scaling"  # Phase 3-4: High value, long-term


@dataclass
class UltraFastConfig:
    """Configuration for ultra fast income mode."""

    # Cash speed threshold for ultra fast mode
    min_cash_speed: float = 0.85

    # Prioritized categories (highest priority first)
    priority_categories: list[str] = field(
        default_factory=lambda: [
            "data_annotation",
            "ai_training",
            "ai_evaluation",
            "synthetic_data",
            "fiverr",
            "web_scraping",
            "prompt_engineering",
            "qa_automation",
            "browser_automation",
        ]
    )

    # Maximum daily target for ultra fast mode
    max_daily_target_usd: float = 500.0

    # Maximum weekly target for ultra fast mode
    max_weekly_target_usd: float = 2500.0

    # Minimum acceptance probability to include
    min_acceptance_probability: float = 0.60

    # Maximum hours per day for ultra fast mode
    max_hours_per_day: float = 8.0


@dataclass
class UltraFastPlan:
    """Ultra fast income plan."""

    generated_at: str
    mode: IncomeMode
    daily_target_usd: float
    weekly_target_usd: float
    daily_expected_value: float
    weekly_expected_value: float
    daily_hours: float
    items: list[dict[str, Any]] = field(default_factory=list)
    total_items: int = 0
    blocked_items: int = 0
    recommended_actions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "mode": self.mode.value,
            "daily_target_usd": self.daily_target_usd,
            "weekly_target_usd": self.weekly_target_usd,
            "daily_expected_value": self.daily_expected_value,
            "weekly_expected_value": self.weekly_expected_value,
            "daily_hours": self.daily_hours,
            "items": self.items,
            "total_items": self.total_items,
            "blocked_items": self.blocked_items,
            "recommended_actions": self.recommended_actions,
            "notes": self.notes,
        }


class UltraFastIncomeEngine:
    """Engine for ultra fast income generation (Phase 0 — survival mode).

    Filters and prioritizes only categories that pay in days.
    Focuses on immediate cashflow generation.
    """

    def __init__(self, config: UltraFastConfig | None = None, state_file: Path = Path("data/ultra_fast_state.json")):
        self.config = config or UltraFastConfig()
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_mode = IncomeMode.BALANCED
        self._infinite_discovery = get_infinite_source_discovery()
        self._auto_apply = get_auto_apply_system()
        self._load_state()

    def _load_state(self) -> None:
        """Load ultra fast mode state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self._current_mode = IncomeMode(data.get("current_mode", "balanced"))
                logger.info(f"Loaded ultra fast mode state: {self._current_mode}")
            except Exception as e:
                logger.warning(f"Failed to load ultra fast mode state: {e}")

    def _save_state(self) -> None:
        """Save ultra fast mode state to disk."""
        try:
            data = {
                "current_mode": self._current_mode.value,
                "last_updated": datetime.now(UTC).isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved ultra fast mode state: {self._current_mode}")
        except Exception as e:
            logger.error(f"Failed to save ultra fast mode state: {e}")

    def set_mode(self, mode: IncomeMode) -> None:
        """Set the current income generation mode."""
        self._current_mode = mode
        self._save_state()
        logger.info(f"Set income mode to: {mode}")

    def get_mode(self) -> IncomeMode:
        """Get the current income generation mode."""
        return self._current_mode

    def is_ultra_fast_mode(self) -> bool:
        """Check if currently in ultra fast mode."""
        return self._current_mode == IncomeMode.ULTRA_FAST

    def generate_plan(self, opportunities: list[dict[str, Any]] | None = None) -> UltraFastPlan:
        """Generate ultra fast income plan with infinite source discovery.

        Uses infinite source discovery to find opportunities.
        Auto-apply where possible via APIs.
        """
        from cores.direct_work_engine.cashflow_radar import _estimate_hours, _to_float
        from cores.direct_work_engine.execution_planner import plan_execution
        from cores.direct_work_engine.success_engine import plan_opportunity_success

        # Use infinite source discovery if no opportunities provided
        if opportunities is None:
            logger.info("Using infinite source discovery to find opportunities")
            discovered = self._infinite_discovery.discover_sources(limit=20)
            opportunities = [opp.to_dict() for opp in discovered]
            logger.info(f"Discovered {len(opportunities)} opportunities from infinite sources")

        # Filter for ultra fast categories
        ultra_fast_items = []
        for opp in opportunities:
            cash_speed = self._get_cash_speed(opp)
            if cash_speed >= self.config.min_cash_speed:
                ultra_fast_items.append(opp)

        # Score and rank items
        scored_items = []
        for opp in ultra_fast_items:
            score = self._score_ultra_fast_item(
                opp, plan_opportunity_success, plan_execution, _estimate_hours, _to_float
            )
            if score and score["acceptance_probability"] >= self.config.min_acceptance_probability:
                scored_items.append(score)

        # Sort by priority (category order, then expected value)
        scored_items.sort(key=lambda x: (self._get_priority_rank(x["category"]), -x["expected_value_usd"]))

        # Auto-apply to items with API support
        auto_applied = []
        for item in scored_items:
            if item.get("auto_apply_available", False):
                try:
                    app_record = self._auto_apply.auto_apply(item)
                    auto_applied.append(app_record)
                    logger.info(f"Auto-applied to: {item['title']}")
                except Exception as e:
                    logger.error(f"Auto-apply failed for {item['title']}: {e}")

        # Calculate daily expected value (top items up to hours limit)
        daily_items = []
        daily_hours = 0.0
        daily_ev = 0.0

        for item in scored_items:
            if daily_hours + item["hours_estimate"] <= self.config.max_hours_per_day:
                daily_items.append(item)
                daily_hours += item["hours_estimate"]
                daily_ev += item["expected_value_usd"]
            else:
                break

        # Calculate weekly expected value (7x daily)
        weekly_ev = daily_ev * 7

        # Generate recommendations
        actions = []
        notes = []

        if daily_ev < self.config.max_daily_target_usd:
            gap = self.config.max_daily_target_usd - daily_ev
            actions.append(f"Añadir ${gap:.0f} más en trabajos de alta velocidad")
            notes.append(f"Gap al target diario: ${gap:.0f}")

        if len(daily_items) == 0:
            actions.append("Sin items suficientes de alta velocidad disponible")
            notes.append("Infinite source discovery escaneando más fuentes")

        if len(auto_applied) > 0:
            actions.append(f"Auto-aplicado a {len(auto_applied)} trabajos vía API")
            notes.append("Plataformas con auto-apply: Indeed, Upwork, Fiverr")

        if daily_hours < self.config.max_hours_per_day * 0.5:
            actions.append("Aumentar disponibilidad de tiempo para trabajos ultra rápidos")
            notes.append(f"Horas disponibles: {daily_hours:.1f}/{self.config.max_hours_per_day}")

        return UltraFastPlan(
            generated_at=datetime.now(UTC).isoformat(),
            mode=self._current_mode,
            daily_target_usd=self.config.max_daily_target_usd,
            weekly_target_usd=self.config.max_weekly_target_usd,
            daily_expected_value=daily_ev,
            weekly_expected_value=weekly_ev,
            daily_hours=daily_hours,
            items=daily_items,
            total_items=len(scored_items),
            blocked_items=len(ultra_fast_items) - len(scored_items),
            recommended_actions=actions,
            notes=notes,
        )

    def _get_workbank_items(self) -> list[dict[str, Any]]:
        """Get items from work bank."""
        try:
            from cores.direct_work_engine.workbank import WorkBank

            bank = WorkBank()
            items = bank.get_ready_items()
            return [item.to_dict() for item in items]
        except Exception as e:
            logger.error(f"Failed to get workbank items: {e}")
            return []

    def _get_cash_speed(self, opp: dict[str, Any]) -> float:
        """Get cash speed factor for an opportunity."""
        from cores.direct_work_engine.max_daily_income import CASH_SPEED_FACTORS, DEFAULT_CASH_SPEED

        category = opp.get("category", "general")
        return CASH_SPEED_FACTORS.get(category, DEFAULT_CASH_SPEED)

    def _get_priority_rank(self, category: str) -> int:
        """Get priority rank for a category (lower = higher priority)."""
        try:
            return self.config.priority_categories.index(category)
        except ValueError:
            return len(self.config.priority_categories)  # Lowest priority

    def _score_ultra_fast_item(
        self,
        opp: dict[str, Any],
        success_fn,
        execution_fn,
        hours_fn,
        to_float_fn,
    ) -> dict[str, Any] | None:
        """Score an ultra fast item."""
        try:
            platform = opp.get("platform", "")
            title = opp.get("title", "")
            category = opp.get("category", "general")
            reward = to_float_fn(opp.get("reward", 0))

            # Get success probability
            success_result = success_fn(opp)
            acceptance_prob = success_result.get("probability_after_full_plan", 0.5)

            # Get hours estimate
            human_minutes = float(opp.get("human_work_minutes", 0.0) or 0.0)
            hours = hours_fn(opp, human_minutes, category)

            # Get cash speed
            cash_speed = self._get_cash_speed(opp)

            # Calculate expected value: reward × acceptance × cash_speed
            expected_value = reward * acceptance_prob * cash_speed

            return {
                "platform": platform,
                "title": title,
                "category": category,
                "reward": reward,
                "acceptance_probability": acceptance_prob,
                "cash_speed": cash_speed,
                "expected_value_usd": expected_value,
                "hours_estimate": hours,
                "blocked": opp.get("blocked", False),
                "direct_link": opp.get("direct_link", ""),
            }
        except Exception as e:
            logger.error(f"Failed to score item: {e}")
            return None

    def get_status(self) -> dict[str, Any]:
        """Get current status of ultra fast mode."""
        plan = self.generate_plan()

        return {
            "current_mode": self._current_mode.value,
            "is_ultra_fast": self.is_ultra_fast_mode(),
            "config": {
                "min_cash_speed": self.config.min_cash_speed,
                "priority_categories": self.config.priority_categories,
                "max_daily_target_usd": self.config.max_daily_target_usd,
                "max_weekly_target_usd": self.config.max_weekly_target_usd,
                "min_acceptance_probability": self.config.min_acceptance_probability,
                "max_hours_per_day": self.config.max_hours_per_day,
            },
            "current_plan": plan.to_dict(),
        }


# Singleton instance
_global_engine: UltraFastIncomeEngine | None = None


def get_ultra_fast_income_engine() -> UltraFastIncomeEngine:
    """Get or create the global ultra fast income engine."""
    global _global_engine
    if _global_engine is None:
        _global_engine = UltraFastIncomeEngine()
    return _global_engine
