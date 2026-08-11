from __future__ import annotations

import logging
from typing import Any

from core.financial_intelligence.models import Opportunity, RiskPolicy

logger = logging.getLogger("orion.financial_intelligence.risk_engine")


class RiskEngine:
    """Evaluates opportunities against risk policies.

    Enforces position sizing, maximum allocation, drawdown protection,
    diversification, and circuit breakers.
    """

    def __init__(self, policy: RiskPolicy | None = None):
        self.policy = policy or RiskPolicy()
        self._active_positions: dict[str, float] = {}
        self._daily_pnl: list[float] = []
        self._monthly_pnl: list[float] = []
        self._peak_value: float = 10000.0
        self._current_value: float = 10000.0

    def check_opportunity(self, opp: Opportunity, current_portfolio_value: float = 10000.0) -> dict[str, Any]:
        violations: list[str] = []

        if self.policy.emergency_stop:
            violations.append("Emergency stop is active — no operations allowed")

        if self.policy.circuit_breaker_active:
            violations.append("Circuit breaker is active — trading halted")

        drawdown = self._compute_drawdown(current_portfolio_value)
        if drawdown > self.policy.drawdown_protection_pct:
            violations.append(
                f"Drawdown {drawdown:.1%} exceeds protection limit {self.policy.drawdown_protection_pct:.0%}"
            )

        if self._daily_loss() > self.policy.max_daily_loss_pct:
            violations.append(f"Daily loss exceeds maximum {self.policy.max_daily_loss_pct:.0%}")

        if self._monthly_loss() > self.policy.max_monthly_loss_pct:
            violations.append(f"Monthly loss exceeds maximum {self.policy.max_monthly_loss_pct:.0%}")

        current_alloc = sum(self._active_positions.values())
        suggested_allocation = current_portfolio_value * self.policy.position_size_pct
        if current_alloc + suggested_allocation > current_portfolio_value * self.policy.max_allocation_pct:
            violations.append(f"Total allocation would exceed {self.policy.max_allocation_pct:.0%} limit")

        if len(self._active_positions) < self.policy.min_diversification and len(self._active_positions) > 0:
            violations.append(
                f"Minimum diversification not met — need at least {self.policy.min_diversification} positions"
            )

        correlation = opp.correlation
        if correlation > self.policy.correlation_limit:
            violations.append(f"Correlation {correlation:.2f} exceeds limit {self.policy.correlation_limit:.2f}")

        passed = len(violations) == 0
        max_position = current_portfolio_value * self.policy.position_size_pct
        safe_amount = min(opp.expected_value, max_position) if passed else 0.0

        return {
            "approved": passed,
            "violations": violations,
            "max_position_size": round(max_position, 2),
            "safe_allocation": round(safe_amount, 2),
            "drawdown": round(drawdown, 4),
            "daily_loss": round(self._daily_loss(), 4),
            "monthly_loss": round(self._monthly_loss(), 4),
        }

    def record_trade(self, amount: float, pnl: float) -> None:
        self._daily_pnl.append(pnl)
        self._monthly_pnl.append(pnl)
        if pnl < 0:
            self._current_value -= abs(pnl)
        else:
            self._current_value += pnl

    def activate_emergency_stop(self) -> None:
        self.policy.emergency_stop = True
        logger.warning("[RISK] Emergency stop activated")

    def deactivate_emergency_stop(self) -> None:
        self.policy.emergency_stop = False
        logger.info("[RISK] Emergency stop deactivated")

    def activate_circuit_breaker(self) -> None:
        self.policy.circuit_breaker_active = True
        logger.warning("[RISK] Circuit breaker activated")

    def deactivate_circuit_breaker(self) -> None:
        self.policy.circuit_breaker_active = False
        logger.info("[RISK] Circuit breaker deactivated")

    def get_status(self) -> dict[str, Any]:
        return {
            "emergency_stop": self.policy.emergency_stop,
            "circuit_breaker_active": self.policy.circuit_breaker_active,
            "active_positions": len(self._active_positions),
            "drawdown": round(self._compute_drawdown(self._current_value), 4),
            "daily_loss": round(self._daily_loss(), 4),
            "monthly_loss": round(self._monthly_loss(), 4),
            "peak_value": round(self._peak_value, 2),
            "current_value": round(self._current_value, 2),
        }

    def _compute_drawdown(self, current_value: float) -> float:
        if current_value > self._peak_value:
            self._peak_value = current_value
        if self._peak_value == 0:
            return 0.0
        return (self._peak_value - current_value) / self._peak_value

    def _daily_loss(self) -> float:
        daily = self._daily_pnl[-100:] if self._daily_pnl else [0.0]
        losses = [abs(p) for p in daily if p < 0]
        return sum(losses) / len(losses) if losses else 0.0

    def _monthly_loss(self) -> float:
        monthly = self._monthly_pnl[-500:] if self._monthly_pnl else [0.0]
        losses = [abs(p) for p in monthly if p < 0]
        return sum(losses) / len(losses) if losses else 0.0
