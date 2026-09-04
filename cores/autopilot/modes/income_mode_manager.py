"""Income Mode Manager - Switch between MAX_INCOME, BEST_INCOME, FAST_INCOME modes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cores.autopilot.config.autopilot_config import IncomeMode


@dataclass
class IncomeModePreset:
    mode: IncomeMode
    name: str
    description: str
    recommender: dict[str, Any] = field(default_factory=dict)
    workbank_daily_target: int = 10
    security_scanning: str = "high_value"
    dev_bounty_scope: str = "top3"
    ai_eval_scope: str = "generalist"
    capital_allocation: str = "balanced"
    quant_trading: str = "paper+small_live"
    target_daily_ev: float = 1500.0
    human_gates_per_day: tuple[int, int] = (8, 12)
    use_case: str = "Objetivo $15k-30k/mes"


INCOME_MODE_PRESETS: dict[IncomeMode, IncomeModePreset] = {
    IncomeMode.MAX_INCOME: IncomeModePreset(
        mode=IncomeMode.MAX_INCOME,
        name="MAX INCOME",
        description="Maximizar $EV/hora humana semanal. Agresivo en high-value.",
        recommender={
            "weights": {
                "expected_value": 0.35,
                "acceptance_probability": 0.25,
                "speed_to_cash": 0.15,
                "barrier_level": 0.15,
                "platform_compatibility": 0.05,
                "reputation": 0.05,
            },
            "thresholds": {
                "min_zero_barrier_score": 40.0,
                "min_expected_value": 100.0,
                "min_acceptance_probability": 0.15,
                "enforce_acceptance_floor": False,
            },
            "diversity": {"max_per_platform": 5, "max_per_category": 8},
            "penalty_risk": 0.3,
        },
        workbank_daily_target=20,
        security_scanning="full",
        dev_bounty_scope="all",
        ai_eval_scope="specialist+generalist",
        capital_allocation="aggressive",
        quant_trading="full",
        target_daily_ev=3000.0,
        human_gates_per_day=(15, 20),
        use_case="Objetivo $50k-100k/mes",
    ),
    IncomeMode.BEST_INCOME: IncomeModePreset(
        mode=IncomeMode.BEST_INCOME,
        name="BEST INCOME",
        description="Balance óptimo: EV alto + aceptación realista + velocidad buena.",
        recommender={
            "weights": {
                "expected_value": 0.30,
                "acceptance_probability": 0.30,
                "speed_to_cash": 0.20,
                "barrier_level": 0.10,
                "platform_compatibility": 0.05,
                "reputation": 0.05,
            },
            "thresholds": {
                "min_zero_barrier_score": 55.0,
                "min_expected_value": 200.0,
                "min_acceptance_probability": 0.25,
                "enforce_acceptance_floor": True,
            },
            "diversity": {"max_per_platform": 3, "max_per_category": 5},
            "penalty_risk": 0.2,
        },
        workbank_daily_target=10,
        security_scanning="high_value",
        dev_bounty_scope="top3",
        ai_eval_scope="generalist",
        capital_allocation="balanced",
        quant_trading="paper+small_live",
        target_daily_ev=1500.0,
        human_gates_per_day=(8, 12),
        use_case="Objetivo $15k-30k/mes",
    ),
    IncomeMode.FAST_INCOME: IncomeModePreset(
        mode=IncomeMode.FAST_INCOME,
        name="FAST INCOME",
        description="Cobro rápido. Prioriza velocidad y aceptación sobre EV nominal.",
        recommender={
            "weights": {
                "expected_value": 0.20,
                "acceptance_probability": 0.35,
                "speed_to_cash": 0.30,
                "barrier_level": 0.10,
                "platform_compatibility": 0.03,
                "reputation": 0.02,
            },
            "thresholds": {
                "min_zero_barrier_score": 60.0,
                "min_expected_value": 50.0,
                "min_acceptance_probability": 0.40,
                "enforce_acceptance_floor": True,
            },
            "diversity": {"max_per_platform": 2, "max_per_category": 3},
            "penalty_risk": 0.1,
        },
        workbank_daily_target=5,
        security_scanning="skip",
        dev_bounty_scope="opire_only",
        ai_eval_scope="available_now",
        capital_allocation="conservative",
        quant_trading="off",
        target_daily_ev=500.0,
        human_gates_per_day=(3, 5),
        use_case="Objetivo $3k-8k/mes / arranque",
    ),
}


class IncomeModeManager:
    """Manages income mode switching and preset application."""

    def __init__(self, config: Any):
        self.config = config
        self.current_mode = getattr(config, "automation", None) and config.automation.mode or "best_income"
        self._presets = INCOME_MODE_PRESETS

    @property
    def current_preset(self) -> IncomeModePreset:
        mode = getattr(IncomeMode, self.current_mode.upper(), IncomeMode.BEST_INCOME)
        return self._presets.get(mode, self._presets[IncomeMode.BEST_INCOME])

    async def set_mode(self, mode: str | Any) -> bool:
        """Switch income mode instantly."""
        if isinstance(mode, str):
            try:
                mode = IncomeMode[mode.upper()]
            except (KeyError, AttributeError):
                return False

        if mode not in self._presets:
            return False

        self.current_mode = mode
        return True

    def get_recommender_config(self) -> dict[str, Any]:
        """Get the recommender config for current mode."""
        return self.current_preset.recommender

    def get_workbank_target(self) -> int:
        return self.current_preset.workbank_daily_target

    def get_security_scanning_mode(self) -> str:
        return self.current_preset.security_scanning

    def get_dev_bounty_scope(self) -> str:
        return self.current_preset.dev_bounty_scope

    def get_ai_eval_scope(self) -> str:
        return self.current_preset.ai_eval_scope

    def get_capital_allocation_mode(self) -> str:
        return self.current_preset.capital_allocation

    def get_quant_trading_mode(self) -> str:
        return self.current_preset.quant_trading

    def get_target_daily_ev(self) -> float:
        return self.current_preset.target_daily_ev

    def get_human_gates_range(self) -> tuple[int, int]:
        return self.current_preset.human_gates_per_day

    def get_all_presets(self) -> dict[str, dict[str, Any]]:
        return {
            mode.name.lower(): {
                "name": preset.name,
                "description": preset.description,
                "workbank_daily_target": preset.workbank_daily_target,
                "security_scanning": preset.security_scanning,
                "dev_bounty_scope": preset.dev_bounty_scope,
                "ai_eval_scope": preset.ai_eval_scope,
                "capital_allocation": preset.capital_allocation,
                "quant_trading": preset.quant_trading,
                "target_daily_ev": preset.target_daily_ev,
                "human_gates_per_day": preset.human_gates_per_day,
                "use_case": preset.use_case,
            }
            for mode, preset in INCOME_MODE_PRESETS.items()
        }

    def apply_to_config(self, config: Any) -> None:
        """Apply current preset to autopilot config."""
        if hasattr(config, "automation"):
            config.automation.mode = (
                self.current_mode.lower() if isinstance(self.current_mode, str) else self.current_mode.name.lower()
            )
