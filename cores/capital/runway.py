"""Runway Engine — calculates financial runway based on capital, income, and expenses."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.capital.runway")


@dataclass
class RunwaySnapshot:
    """Snapshot of runway analysis."""

    monthly_burn: float
    essential_burn: float
    discretionary_burn: float
    available_cash: float
    invested_capital: float
    expected_monthly_income: float
    runway_months: float
    runway_days: int
    status: str  # healthy, warning, critical
    breakdown: dict[str, float] = field(default_factory=dict)
    projection: dict[str, dict[str, Any]] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class RunwayEngine:
    """Calculates financial runway based on capital, income, and expenses."""

    def __init__(self) -> None:
        self._essential_categories = {"housing", "food", "transport", "healthcare", "utilities", "insurance"}
        self._discretionary_categories = {"entertainment", "dining", "shopping", "travel", "subscriptions", "hobbies"}

    def calculate_runway(
        self,
        work_income_usd_per_month: float = 0,
        savings_usd_per_month: float = 0,
        start_capital_usd: float = 0,
        annual_return_rate: float = 0.10,
        target_monthly_usd: float = 100000,
    ) -> dict[str, Any]:
        """Calculate runway with given parameters."""
        # Get current capital state
        available_cash = self._get_available_cash()
        invested_capital = self._get_invested_capital()
        monthly_burn = self._calculate_monthly_burn()
        essential_burn = self._calculate_essential_burn()
        discretionary_burn = monthly_burn - essential_burn

        # Expected monthly income
        expected_income = work_income_usd_per_month + savings_usd_per_month

        # Net monthly cash flow
        net_monthly = expected_income - monthly_burn

        # Runway calculation
        if net_monthly >= 0:
            runway_months = float("inf")
            status = "healthy"
        else:
            total_capital = available_cash + invested_capital
            runway_months = total_capital / abs(net_monthly) if net_monthly != 0 else float("inf")
            if runway_months < 1:
                status = "critical"
            elif runway_months < 3:
                status = "warning"
            else:
                status = "healthy"

        # Build breakdown
        breakdown = {
            "available_cash": round(available_cash, 2),
            "invested_capital": round(invested_capital, 2),
            "monthly_burn": round(monthly_burn, 2),
            "essential_burn": round(essential_burn, 2),
            "discretionary_burn": round(discretionary_burn, 2),
            "expected_income": round(expected_income, 2),
            "net_monthly": round(net_monthly, 2),
        }

        # Projection for different scenarios
        projection = {
            "conservative": self._project_scenario(
                available_cash, invested_capital, net_monthly * 0.5, annual_return_rate
            ),
            "base": self._project_scenario(available_cash, invested_capital, net_monthly, annual_return_rate),
            "optimistic": self._project_scenario(
                available_cash, invested_capital, net_monthly * 1.5, annual_return_rate
            ),
        }

        snapshot = RunwaySnapshot(
            monthly_burn=round(monthly_burn, 2),
            essential_burn=round(essential_burn, 2),
            discretionary_burn=round(discretionary_burn, 2),
            available_cash=round(available_cash, 2),
            invested_capital=round(invested_capital, 2),
            expected_monthly_income=round(expected_income, 2),
            runway_months=round(runway_months, 1) if runway_months != float("inf") else float("inf"),
            runway_days=int(runway_months * 30) if runway_months != float("inf") else -1,
            status=status,
            breakdown=breakdown,
            projection={k: {"months": v["months"], "amount": v["amount"]} for k, v in projection.items()},
        )

        return snapshot.__dict__

    def _get_available_cash(self) -> float:
        """Get available cash from truth layer."""
        try:
            from cores.financial.dashboard import get_dashboard

            dash = get_dashboard()
            return dash.get("liquidez", {}).get("disponible", 0.0)
        except Exception:
            return 0.0

    def _get_invested_capital(self) -> float:
        """Get invested capital from investment manager."""
        try:
            from core.investment.manager import get_investment_manager

            im = get_investment_manager()
            if hasattr(im, "get_snapshot"):
                snap = im.get_snapshot()
                return snap.get("total_value", 0.0)
            return 0.0
        except Exception:
            return 0.0

    def _calculate_monthly_burn(self) -> float:
        """Calculate total monthly burn from ledger."""
        try:
            from cores.ledger import get_history

            entries = get_history(limit=1000)
            thirty_days_ago = datetime.now(UTC).timestamp() - 30 * 86400
            total = 0.0
            for e in entries:
                ts = e.get("timestamp", "")
                try:
                    if isinstance(ts, (int, float)):
                        if ts < thirty_days_ago:
                            continue
                    elif isinstance(ts, str):
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if dt.timestamp() < thirty_days_ago:
                            continue
                except Exception:
                    continue
                amount = float(e.get("amount", 0))
                if amount < 0:
                    total += abs(amount)
            return total
        except Exception:
            return 0.0

    def _calculate_essential_burn(self) -> float:
        """Calculate essential monthly burn from ledger."""
        try:
            from cores.ledger import get_history

            entries = get_history(limit=1000)
            thirty_days_ago = datetime.now(UTC).timestamp() - 30 * 86400
            total = 0.0
            for e in entries:
                ts = e.get("timestamp", "")
                try:
                    if isinstance(ts, (int, float)):
                        if ts < thirty_days_ago:
                            continue
                    elif isinstance(ts, str):
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if dt.timestamp() < thirty_days_ago:
                            continue
                except Exception:
                    continue
                amount = float(e.get("amount", 0))
                if amount < 0:
                    category = e.get("category", "").lower()
                    if any(cat in category for cat in self._essential_categories):
                        total += abs(amount)
            return total
        except Exception:
            return 0.0

    def _project_scenario(
        self,
        available_cash: float,
        invested_capital: float,
        net_monthly: float,
        annual_return_rate: float,
    ) -> dict[str, Any]:
        """Project runway for a scenario."""
        if net_monthly >= 0:
            return {"months": float("inf"), "amount": float("inf")}
        total = available_cash + invested_capital
        monthly_return = (1 + annual_return_rate) ** (1 / 12) - 1
        # Simple projection: capital * (1 + monthly_return)^months + net_monthly * months >= 0
        # Simplified: runway = total / abs(net_monthly) adjusted for returns
        if net_monthly >= 0:
            months = float("inf")
        else:
            months = total / abs(net_monthly)
        return {
            "months": round(months, 1) if months != float("inf") else float("inf"),
            "amount": round(available_cash + invested_capital + net_monthly * months, 2)
            if months != float("inf")
            else float("inf"),
        }


_runway_engine: RunwayEngine | None = None


def get_runway_engine() -> RunwayEngine:
    global _runway_engine
    if _runway_engine is None:
        _runway_engine = RunwayEngine()
    return _runway_engine
