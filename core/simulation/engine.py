"""Simulation Engine — runs what-if scenarios for any app.

Simulates outcomes of decisions without touching real money.
All simulations are logged in the Decision Journal for later review.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from core.decision_journal import journal

logger = logging.getLogger("orion.core.simulation")


@dataclass
class SimulationResult:
    id: str
    app_id: str
    scenario_name: str
    initial_value: float
    final_value: float
    pnl: float
    pnl_percent: float
    metrics: dict[str, Any] = field(default_factory=dict)
    details: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SimulationEngine:
    """Runs Monte Carlo and what-if simulations for any app."""

    def __init__(self) -> None:
        self._rng = np.random.default_rng()

    async def run_monte_carlo(
        self,
        app_id: str,
        initial_value: float,
        scenarios: list[dict],
        n_simulations: int = 1000,
        horizon_days: int = 365,
    ) -> SimulationResult:
        """Run Monte Carlo simulation.

        Args:
            app_id: Which app owns this simulation.
            initial_value: Starting portfolio/bankroll value.
            scenarios: List of {probability, return_pct, label} dicts.
            n_simulations: Number of Monte Carlo runs.
            horizon_days: Simulation horizon in days.

        Returns:
            SimulationResult with aggregated metrics.
        """
        final_values = []
        all_paths = []
        for _ in range(n_simulations):
            value = initial_value
            path = [value]
            for _ in range(min(horizon_days, 252)):  # ~252 trading days/year
                r = self._rng.choice(
                    [s["return_pct"] for s in scenarios],
                    p=[s["probability"] for s in scenarios],
                )
                value *= 1 + r
                path.append(value)
            final_values.append(value)
            all_paths.append(path)

        sorted(final_values)
        median = float(np.median(final_values))
        worst = float(np.percentile(final_values, 5))
        best = float(np.percentile(final_values, 95))

        result = SimulationResult(
            id=f"sim-{uuid.uuid4().hex[:8]}",
            app_id=app_id,
            scenario_name=f"MC-{n_simulations}-{horizon_days}d",
            initial_value=initial_value,
            final_value=median,
            pnl=median - initial_value,
            pnl_percent=((median - initial_value) / initial_value * 100) if initial_value else 0.0,
            metrics={
                "median": median,
                "mean": float(np.mean(final_values)),
                "worst_5pct": worst,
                "best_5pct": best,
                "std_dev": float(np.std(final_values)),
                "ruin_probability": sum(1 for v in final_values if v <= 0) / n_simulations * 100,
                "sharpe_ratio": self._sharpe_ratio(all_paths),
                "max_drawdown": self._max_drawdown(all_paths),
                "simulations": n_simulations,
            },
        )

        journal.log_decision(
            app_id=app_id,
            agent_id="simulation_engine",
            action="monte_carlo",
            reason=f"MC simulation: {n_simulations}x{horizon_days}d",
            data_snapshot={
                "scenarios": scenarios,
                "result": result.metrics,
            },
        )

        return result

    async def run_what_if(
        self,
        app_id: str,
        title: str,
        current_value: float,
        proposed_changes: list[dict],
    ) -> SimulationResult:
        """Run a what-if scenario.

        Args:
            app_id: App owning this simulation.
            title: Human-readable name.
            current_value: Current portfolio/bankroll value.
            proposed_changes: List of {field, old_value, new_value} dicts.

        Returns:
            SimulationResult comparing current vs proposed.
        """
        new_value = current_value
        for change in proposed_changes:
            delta = change.get("new_value", 0) - change.get("old_value", 0)
            new_value += delta

        result = SimulationResult(
            id=f"wi-{uuid.uuid4().hex[:8]}",
            app_id=app_id,
            scenario_name=title,
            initial_value=current_value,
            final_value=new_value,
            pnl=new_value - current_value,
            pnl_percent=((new_value - current_value) / current_value * 100) if current_value else 0.0,
            details=proposed_changes,
        )

        journal.log_decision(
            app_id=app_id,
            agent_id="simulation_engine",
            action=title,
            reason=f"What-if simulation: {title}",
            data_snapshot={"current": current_value, "proposed": new_value, "changes": proposed_changes},
        )

        return result

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _sharpe_ratio(paths: list[list[float]], risk_free: float = 0.02) -> float:
        """Calculate average Sharpe ratio across simulation paths."""
        ratios = []
        for path in paths:
            if len(path) < 2:
                continue
            returns = [(path[i] - path[i - 1]) / path[i - 1] for i in range(1, len(path))]
            avg_ret = np.mean(returns)
            std_ret = np.std(returns)
            if std_ret > 0:
                ratios.append((avg_ret * 252 - risk_free) / (std_ret * np.sqrt(252)))
        return float(np.mean(ratios)) if ratios else 0.0

    @staticmethod
    def _max_drawdown(paths: list[list[float]]) -> float:
        """Calculate max drawdown across simulation paths."""
        drawdowns = []
        for path in paths:
            peak = path[0]
            dd = 0.0
            for v in path:
                if v > peak:
                    peak = v
                current_dd = (peak - v) / peak
                if current_dd > dd:
                    dd = current_dd
            drawdowns.append(dd)
        return float(np.mean(drawdowns)) * 100 if drawdowns else 0.0


# ── Singleton ────────────────────────────────────────

_engine: SimulationEngine | None = None


def get_simulation_engine() -> SimulationEngine:
    global _engine
    if _engine is None:
        _engine = SimulationEngine()
    return _engine
