from __future__ import annotations

from cores.autopilot.achievements.achievement_engine import AchievementEngine
from cores.autopilot.autopilot_engine import AutopilotEngine, get_autopilot, start_autopilot, stop_autopilot
from cores.autopilot.checks.daily_checks import CheckResult, DailyChecks
from cores.autopilot.config.autopilot_config import AutopilotConfig, load_autopilot_config
from cores.autopilot.dashboard.autopilot_dashboard import AutopilotDashboard
from cores.autopilot.gates.human_gate import GateDecision, GateRequest, GateType, HumanGate
from cores.autopilot.goals.goal_hierarchy import Goal, GoalHierarchy, GoalPeriod
from cores.autopilot.modes.income_mode_manager import IncomeMode, IncomeModeManager
from cores.autopilot.quant.quant_engine import QuantEngine
from cores.autopilot.velocity.capital_velocity import CapitalVelocity

"""OWNEX Autopilot - Autonomous operation orchestration layer."""

__all__ = [
    "AutopilotConfig",
    "load_autopilot_config",
    "AutopilotEngine",
    "get_autopilot",
    "start_autopilot",
    "stop_autopilot",
    "HumanGate",
    "GateType",
    "GateRequest",
    "GateDecision",
    "IncomeModeManager",
    "IncomeMode",
    "AchievementEngine",
    "DailyChecks",
    "CheckResult",
    "GoalHierarchy",
    "Goal",
    "GoalPeriod",
    "AutopilotDashboard",
    "CapitalVelocity",
    "QuantEngine",
]
