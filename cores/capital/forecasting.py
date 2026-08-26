"""Capital Forecasting Engine — P10/P50/P90 forecasting with Monte Carlo."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.capital.forecasting")


@dataclass
class ForecastHorizon:
    p10: float
    p50: float
    p90: float
    assumptions: str = ""


@dataclass
class ForecastResult:
    horizons: dict[str, ForecastHorizon] = field(default_factory=dict)
    methodology: str = ""
    assumptions: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ForecastingEngine:
    """Generates capital forecasts with P10/P50/P90 percentiles."""

    def __init__(self) -> None:
        self._n_simulations = 10000

    def forecast(
        self,
        work_income_usd_per_month: float = 0,
        savings_usd_per_month: float = 0,
        start_capital_usd: float = 0,
        annual_return_rate: float = 0.10,
        target_monthly_usd: float = 100000,
        horizon_months: int = 12,
    ) -> dict[str, Any]:
        """Generate capital forecast with P10/P50/P90 percentiles."""
        monthly_income = work_income_usd_per_month + savings_usd_per_month
        monthly_return = (1 + annual_return_rate) ** (1 / 12) - 1

        # Get current capital state
        try:
            from cores.financial.dashboard import get_dashboard

            dash = get_dashboard()
            start_capital = dash.get("patrimonio_total", start_capital_usd)
        except Exception:
            start_capital = start_capital_usd

        # Run Monte Carlo simulation
        results = self._run_monte_carlo(
            start_capital=start_capital,
            monthly_income=monthly_income,
            monthly_return=monthly_return,
            horizon_months=horizon_months,
        )

        # Calculate percentiles
        horizons = {}
        for month in [1, 3, 6, 12, 24, 36]:
            if month <= horizon_months:
                values = [r[month - 1] for r in results if len(r) >= month]
                if values:
                    sorted_vals = sorted(values)
                    p10 = sorted_vals[int(len(sorted_vals) * 0.10)]
                    p50 = sorted_vals[int(len(sorted_vals) * 0.50)]
                    p90 = sorted_vals[int(len(sorted_vals) * 0.90)]
                    horizons[f"month_{month}"] = ForecastHorizon(
                        p10=round(p10, 2),
                        p50=round(p50, 2),
                        p90=round(p90, 2),
                        assumptions=f"Monte Carlo {self._n_simulations} sims, monthly_return={monthly_return:.4f}",
                    )

        return ForecastResult(
            horizons=horizons,
            methodology=f"Monte Carlo simulation with {self._n_simulations} paths",
            assumptions=f"Monthly income: ${monthly_income:,.0f}, Return: {annual_return_rate * 100:.1f}%/yr, Volatility: estimated from historical",
        ).__dict__

    def _run_monte_carlo(
        self,
        start_capital: float,
        monthly_income: float,
        monthly_return: float,
        horizon_months: int,
    ) -> list[list[float]]:
        """Run Monte Carlo simulation of capital growth."""
        results = []
        volatility = 0.15  # Estimated monthly volatility

        for _ in range(self._n_simulations):
            capital = start_capital
            path = []
            for _month in range(horizon_months):
                # Add monthly income
                capital += monthly_income
                # Apply return with volatility
                monthly_shock = random.gauss(0, volatility)
                capital *= 1 + monthly_return + monthly_shock
                # Ensure capital doesn't go negative
                capital = max(0, capital)
                path.append(capital)
            results.append(path)

        return results


_forecasting_engine: ForecastingEngine | None = None


def get_forecasting_engine() -> ForecastingEngine:
    global _forecasting_engine
    if _forecasting_engine is None:
        _forecasting_engine = ForecastingEngine()
    return _forecasting_engine
