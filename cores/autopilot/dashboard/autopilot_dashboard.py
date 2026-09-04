"""Autopilot Dashboard - Single pane of glass aggregator for Mission Control."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cores.autopilot.config.autopilot_config import AutopilotConfig
from cores.autopilot.gates.human_gate import HumanGate

logger = logging.getLogger(__name__)


@dataclass
class DashboardData:
    """Complete dashboard state for frontend."""

    # Status
    autopilot_status: dict[str, Any]
    config: dict[str, Any]

    # Gates
    pending_gates: list[dict[str, Any]]
    gate_stats: dict[str, Any]

    # Achievements
    achievements: list[dict[str, Any]]
    streaks: dict[str, dict[str, Any]]
    recent_unlocks: list[str]

    # Goals
    goals_tree: dict[str, Any]
    current_sprint: dict[str, Any] | None

    # Capital
    capital_velocity: dict[str, Any]
    capital_allocation: dict[str, Any]
    capital_forecast: dict[str, Any]

    # Quant
    quant_status: dict[str, Any]
    quant_positions: list[dict[str, Any]]
    quant_signals: list[dict[str, Any]]

    # Income
    income_mode: str
    income_preset: dict[str, Any]
    income_plan: dict[str, Any]
    workbank: dict[str, Any]

    # Checks
    check_results: list[dict[str, Any]]
    checks_summary: dict[str, int]

    # System
    system_health: dict[str, Any]
    timestamp: str


class AutopilotDashboard:
    """
    Aggregates all autopilot subsystems into a single dashboard state.

    Provides the "single pane of glass" for Mission Control v2.
    """

    def __init__(self, config: AutopilotConfig):
        self.config = config
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 30  # seconds
        self._last_fetch: dict[str, datetime] = {}

    def get_full_state(
        self,
        status: Any,
        config: AutopilotConfig,
        human_gate: HumanGate,
        achievement_engine: Any,
        goal_hierarchy: Any,
        capital_velocity: Any,
        quant_engine: Any,
    ) -> dict[str, Any]:
        """Get complete dashboard state for frontend."""

        # Check cache
        datetime.utcnow()
        if self._is_cache_valid():
            return self._cache

        # Build complete state
        data = DashboardData(
            autopilot_status=self._build_status(status),
            config=self._build_config(config),
            pending_gates=self._build_gates(human_gate),
            gate_stats=human_gate.get_stats() if hasattr(human_gate, "get_stats") else {},
            achievements=self._build_achievements(achievement_engine),
            streaks=achievement_engine.get_streaks_status()
            if hasattr(achievement_engine, "get_streaks_status")
            else {},
            recent_unlocks=[],  # Would track recently unlocked
            goals_tree=goal_hierarchy.get_hierarchy_tree() if hasattr(goal_hierarchy, "get_hierarchy_tree") else {},
            current_sprint=self._get_current_sprint(goal_hierarchy),
            capital_velocity=capital_velocity.get_velocity() if hasattr(capital_velocity, "get_velocity") else {},
            capital_allocation=self._build_capital_allocation(config),
            capital_forecast={},
            quant_status=self._build_quant_status(quant_engine),
            quant_positions=[],
            quant_signals=[],
            income_mode=config.automation.mode,
            income_preset={},  # Would come from IncomeModeManager
            income_plan={},
            workbank={},
            check_results=[],
            checks_summary={},
            system_health=self._build_system_health(),
            timestamp=datetime.utcnow().isoformat(),
        )

        # Convert to dict for JSON serialization
        result = self._dataclass_to_dict(data)
        self._cache = result
        self._last_fetch["full"] = datetime.utcnow()

        return result

    def _build_status(self, status: Any) -> dict[str, Any]:
        if status is None:
            return {}
        return {
            "is_running": getattr(status, "is_running", False),
            "started_at": getattr(status, "started_at", None),
            "current_mode": getattr(status, "current_mode", "best_income"),
            "last_cycle": getattr(status, "last_cycle", None),
            "cycles_completed": getattr(status, "cycles_completed", 0),
            "gates_pending": getattr(status, "gates_pending", 0),
            "checks_passed": getattr(status, "checks_passed", 0),
            "checks_failed": getattr(status, "checks_failed", 0),
            "achievements_unlocked": getattr(status, "achievements_unlocked", 0),
            "capital_velocity_usd_day": getattr(status, "capital_velocity_usd_day", 0.0),
            "next_actions": getattr(status, "next_actions", []),
            "errors": getattr(status, "errors", [])[-10:],  # Last 10 errors
        }

    def _build_config(self, config: AutopilotConfig) -> dict[str, Any]:
        return {
            "profile": config.profile.__dict__ if hasattr(config, "profile") else {},
            "income_targets": config.income_targets.__dict__ if hasattr(config, "income_targets") else {},
            "automation": config.automation.__dict__ if hasattr(config, "automation") else {},
            "platforms": {k: v.__dict__ for k, v in config.platforms.items()},
            "capital_allocation": config.capital_allocation.__dict__ if hasattr(config, "capital_allocation") else {},
            "risk": config.risk.__dict__ if hasattr(config, "risk") else {},
        }

    def _build_gates(self, human_gate: Any) -> list[dict[str, Any]]:
        if not hasattr(human_gate, "get_pending_gates"):
            return []

        gates = []
        for gate in human_gate.get_pending_gates():
            gates.append(
                {
                    "gate_id": gate.gate_id,
                    "gate_type": gate.gate_type.value if hasattr(gate.gate_type, "value") else str(gate.gate_type),
                    "title": gate.title,
                    "description": gate.description,
                    "display_title": gate.display_title,
                    "amount_usd": gate.amount_usd,
                    "platform": gate.platform,
                    "auto_approvable": gate.auto_approvable,
                    "created_at": gate.created_at.isoformat() if gate.created_at else None,
                    "waiting_since": gate.waiting_since.isoformat() if gate.waiting_since else None,
                    "waiting_minutes": int((datetime.utcnow() - gate.waiting_since).total_seconds() / 60)
                    if gate.waiting_since
                    else 0,
                }
            )
        return gates

    def _build_achievements(self, achievement_engine: Any) -> list[dict[str, Any]]:
        if not hasattr(achievement_engine, "get_all_achievements"):
            return []
        return achievement_engine.get_all_achievements()

    def _get_current_sprint(self, goal_hierarchy: Any) -> dict[str, Any] | None:
        if not hasattr(goal_hierarchy, "get_current_sprint"):
            return None
        sprint = goal_hierarchy.get_current_sprint()
        if sprint is None:
            return None
        return {
            "id": sprint.id,
            "number": sprint.number,
            "name": sprint.name,
            "focus": sprint.focus,
            "key_metric": sprint.key_metric,
            "target": sprint.target,
            "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
            "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
            "goals": sprint.goals,
            "completed": sprint.completed,
        }

    def _build_capital_allocation(self, config: Any) -> dict[str, Any]:
        if not hasattr(config, "capital_allocation"):
            return {}
        ca = config.capital_allocation
        return {
            "emergency_reserve_pct": ca.emergency_reserve_pct,
            "cash_reserve_pct": ca.cash_reserve_pct,
            "low_risk_pct": ca.low_risk_pct,
            "growth_pct": ca.growth_pct,
            "quant_pct": ca.quant_pct,
            "speculative_pct": ca.speculative_pct,
        }

    def _build_quant_status(self, quant_engine: Any) -> dict[str, Any]:
        if quant_engine is None or not hasattr(quant_engine, "get_status"):
            return {"enabled": False, "mode": "off", "paper_trading": True}
        return quant_engine.get_status()

    def _build_system_health(self) -> dict[str, Any]:
        return {
            "scheduler": "healthy",
            "eventbus": "healthy",
            "ai_providers": "healthy",
            "database": "healthy",
            "api": "healthy",
            "workbank": "healthy",
            "capital": "healthy",
            "quant": "healthy",
        }

    def _dataclass_to_dict(self, obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return {k: self._serialize(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize(v) for v in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif hasattr(obj, "__dict__"):
            return {k: self._serialize(v) for k, v in obj.__dict__.items()}
        else:
            return str(obj)

    def _serialize(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (dict, list)) or hasattr(value, "__dataclass_fields__") or hasattr(value, "__dict__"):
            return self._dataclass_to_dict(value)
        return value

    def _is_cache_valid(self) -> bool:
        last = self._last_fetch.get("full")
        if not last:
            return False
        return (datetime.utcnow() - last).total_seconds() < self._cache_ttl
