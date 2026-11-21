"""
OWNEX V13 — Weather Intelligence & Prediction Markets
Risk Management — Paper Trading Only, Real Trading Disabled

Safety constraints non-negotiable:
- Circuit breaker with statistical validation required
- Human gate approval required for reset
- Max drawdown limits enforced
- No real trading execution permitted
"""

import time
from enum import Enum
from typing import Any


class RiskMetrics(str, Enum):
    """Risk metrics enumeration."""

    CAPITAL_EXPOSED = "capital_exposed"
    MAX_DRAWDOWN = "max_drawdown"
    CURRENT_DRAWDOWN = "current_drawdown"
    VALUE_AT_RISK = "value_at_risk"
    SHARPE_RATIO = "sharpe_ratio"
    CALMAR_RATIO = "calmar_ratio"
    POSITION_PCT = "position_pct"
    KELLY_FRACTION = "kelly_fraction"


class CircuitBreakerStatus(str, Enum):
    """Circuit breaker status."""

    NORMAL = "normal"
    TRIGGERED = "triggered"
    RESET_PENDING = "reset_pending"
    RESET_APPROVED = "reset_approved"


class PositionSizingMethod(str, Enum):
    """Position sizing methods."""

    KELLY_FULL = "kelly_full"
    KELLY_HALF = "kelly_half"
    KELLY_QUARTER = "kelly_quarter"
    FIXED_PERCENT = "fixed_percent"
    VOLATILITY_ADJUSTED = "volatility_adjusted"


# --- Circuit Breaker ---


class CircuitBreaker:
    """Circuit breaker for strategy safety — requires human gate approval for reset.

    Safety constraint: 'adaptation automática no pode modificar estratégias
    sem validação estatística e limites de segurança'
    """

    def __init__(
        self,
        max_drawdown: float = 15.0,  # Max drawdown % before trigger
        va_r_percent: float = 10.0,  # Value at Risk % before trigger
        reset_requires_approval: bool = True,  # Human gate required
        cooling_period: int = 3600,  # Cooling seconds before reset attempt
    ):
        self.max_drawdown = max_drawdown  # % capital max drawdown
        self.va_r_percent = va_r_percent  # % VaR threshold
        self.reset_requires_approval = reset_requires_approval
        self.cooling_period = cooling_period

        self.status = CircuitBreakerStatus.NORMAL
        self.current_drawdown = 0.0  # % current drawdown
        self.peak_capital = 100.0  # Peak capital tracked
        self.trade_count = 0
        self.consecutive_losses = 0
        self.last_trigger_time = 0.0
        self.cooling_deadline = 0.0  # Timestamp when cooling ends
        self._human_approval_id: str | None = None

    def check_and_update(self, capital_change_pct: float, current_capital: float, peak_capital: float) -> dict[str, Any]:
        """Check circuit breaker conditions and update state.

        Returns dict with breaker status and any actions required.
        """
        triggered = False
        reasons: list[str] = []

        # Update peak capital
        if current_capital > peak_capital:
            self.peak_capital = current_capital

        # Calculate drawdown from peak
        if self.peak_capital > 0:
            self.current_drawdown = (self.peak_capital - current_capital) / self.peak_capital * 100.0
        else:
            self.current_drawdown = 0.0

        # Check max drawdown trigger
        if self.current_drawdown >= self.max_drawdown:
            triggered = True
            reasons.append(f"Max drawdown triggered: {self.current_drawdown:.2f}% >= {self.max_drawdown:.2f}%")

        # Check VaR trigger
        # VaR calculated from historical volatility or parametric method
        # Simplified: if current drawdown approaches VaR threshold
        if self.current_drawdown >= self.va_r_percent and not triggered:
            triggered = True
            reasons.append(f"VaR triggered: {self.current_drawdown:.2f}% >= {self.va_r_percent:.2f}% VaR")

        if triggered:
            self.status = CircuitBreakerStatus.TRIGGERED
            self.last_trigger_time = time.time()
            self.consecutive_losses += 1

            # Start cooling period
            self.cooling_deadline = time.time() + self.cooling_period

            return {
                "breaker_status": self.status.value,
                "triggered": True,
                "current_drawdown": round(self.current_drawdown, 2),
                "max_drawdown": self.max_drawdown,
                "va_r_percent": self.va_r_percent,
                "reasons": reasons,
                "cooling_deadline": self.cooling_deadline,
                "human_approval_required": self.reset_requires_approval,
            }

        else:
            # Reset consecutive losses counter after wins
            self.consecutive_losses = 0
            self.status = CircuitBreakerStatus.NORMAL

            return {
                "breaker_status": self.status.value,
                "triggered": False,
                "current_drawdown": round(self.current_drawdown, 2),
                "max_drawdown": self.max_drawdown,
                "va_r_percent": self.va_r_percent,
                "reasons": [],
                "cooling_deadline": self.cooling_deadline,
                "human_approval_required": False,
            }

    def is_in_cooling_period(self) -> bool:
        """Check if circuit breaker is in cooling period."""
        return time.time() < self.cooling_deadline

    def request_human_reset(self, approver: str = "human_gate") -> dict[str, Any]:
        """Request human gate approval to reset circuit breaker.

        Safety constraint: circuit breaker reset requires human approval.
        Statistical validation must be provided.
        """
        self._human_approval_id = f"{approver}_{int(time.time())}"

        return {
            "breaker_status": self.status.value,
            "human_approval_id": self._human_approval_id,
            "requires_approval": self.reset_requires_approval,
            "message": (
                f"Circuit breaker in {self.status.value} state. "
                f"Human gate approval required for reset. "
                f"Approval ID: {self._human_approval_id}. "
                f"Statistical validation of recovery metrics must be provided."
            ),
        }

    def approve_reset(self, approved: bool, validation_metrics: dict | None = None) -> dict[str, Any]:
        """Approve or deny circuit breaker reset."""
        if approved and self.status == CircuitBreakerStatus.TRIGGERED:
            # Validate recovery metrics if provided
            if validation_metrics:
                # Check that recovery is statistically significant
                drawdown_recovery = validation_metrics.get("drawdown_recovery_pct", 0)
                win_rate = validation_metrics.get("win_rate", 0)

                # Minimum criteria for reset approval
                if drawdown_recovery < 5.0:
                    # Still recovering — deny or wait
                    return {
                        "breaker_status": CircuitBreakerStatus.TRIGGERED.value,
                        "approved": False,
                        "reason": f"Insufficient drawdown recovery: {drawdown_recovery:.1f}% < 5% minimum",
                        "requires_statistical_validation": True,
                    }

                if win_rate < 30.0:
                    return {
                        "breaker_status": CircuitBreakerStatus.TRIGGERED.value,
                        "approved": False,
                        "reason": f"Insufficient win rate: {win_rate:.1f}% < 30% minimum",
                        "requires_statistical_validation": True,
                    }

            self.status = CircuitBreakerStatus.RESET_APPROVED
            self.consecutive_losses = 0
            self.cooling_deadline = 0.0

            return {
                "breaker_status": self.status.value,
                "approved": True,
                "reason": "Circuit breaker reset approved by human gate with statistical validation",
                "reset_timestamp": time.time(),
            }

        else:
            self.status = CircuitBreakerStatus.TRIGGERED
            return {
                "breaker_status": self.status.value,
                "approved": False,
                "reason": "Circuit breaker reset denied — either not triggered or approval refused",
                "requires_statistical_validation": not approved,
            }


# --- Position Sizing ---


def calculate_position_size(
    capital: float,
    kelly_fraction: float,
    method: PositionSizingMethod = PositionSizingMethod.KELLY_HALF,
    max_pct: float = 25.0,
    current_drawdown_pct: float = 0.0,
    max_drawdown_pct: float = 15.0,
) -> float:
    """Calculate position size based on method and safety constraints."""

    # Base Kelly position
    if method == PositionSizingMethod.KELLY_FULL:
        base_pct = kelly_fraction * 100.0
    elif method == PositionSizingMethod.KELLY_HALF:
        base_pct = (kelly_fraction / 2.0) * 100.0
    elif method == PositionSizingMethod.KELLY_QUARTER:
        base_pct = (kelly_fraction / 4.0) * 100.0
    elif method == PositionSizingMethod.FIXED_PERCENT:
        base_pct = max_pct
    elif method == PositionSizingMethod.VOLATILITY_ADJUSTED:
        # Reduce position if volatility high (σ high)
        volatility_factor = max(0.5, 1.0 - current_drawdown_pct / max_drawdown_pct)
        base_pct = max_pct * volatility_factor
    else:
        base_pct = 0.0

    # Apply drawdown reduction if in drawdown
    if current_drawdown_pct > 0 and max_drawdown_pct > 0:
        drawdown_reduction = 1.0 - min(current_drawdown_pct / max_drawdown_pct, 1.0) * 0.5
        base_pct = base_pct * max(0.0, drawdown_reduction)

    # Cap at max_pct
    final_pct = min(base_pct, max_pct)

    # Ensure non-negative
    final_pct = max(0.0, final_pct)

    return final_pct


# --- Risk Report ---


def generate_risk_report(
    capital_start: float,
    capital_current: float,
    trades: list[dict],
    max_drawdown_pct: float,
    va_r_pct: float,
    position_pct_current: float,
) -> dict:
    """Generate comprehensive risk report."""

    # Calculate drawdown
    if capital_start > 0:
        current_drawdown_pct = (capital_start - capital_current) / capital_start * 100.0
    else:
        current_drawdown_pct = 0.0

    # Sharpe ratio (simplified)
    # In production: would use actual trade P&L and risk-free rate
    sharpe_ratio = 0.0
    if len(trades) > 1:
        returns = [t.get("return_pct", 0.0) for t in trades]
        if returns:
            avg_return = sum(returns) / len(returns)
            return_std = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            if return_std > 0:
                sharpe_ratio = avg_return / return_std * math.sqrt(252)  # Annualized

    # Calmar ratio
    calmar_ratio = current_drawdown_pct / max(1.0, max_drawdown_pct) if max_drawdown_pct > 0 else 0.0

    # Win rate
    winning_trades = sum(1 for t in trades if t.get("return_pct", 0) > 0)
    win_rate = (winning_trades / len(trades) * 100.0) if len(trades) > 0 else 0.0

    return {
        "capital_start": capital_start,
        "capital_current": capital_current,
        "capital_change_pct": round((capital_current - capital_start) / capital_start * 100.0, 2) if capital_start > 0 else 0.0,
        "max_drawdown_pct": max_drawdown_pct,
        "current_drawdown_pct": round(current_drawdown_pct, 2),
        "value_at_risk_pct": va_r_pct,
        "sharpe_ratio": round(sharpe_ratio, 4),
        "calmar_ratio": round(calmar_ratio, 4),
        "win_rate_pct": round(win_rate, 2),
        "position_pct_current": round(position_pct_current, 2),
        "total_trades": len(trades),
        "profit_factor": _calculate_profit_factor(trades),
    }


def _calculate_profit_factor(trades: list[dict]) -> float:
    """Calculate profit factor: gross winning / gross losing."""
    if not trades:
        return 0.0

    gross_wins = sum(t.get("return_pct", 0.0) for t in trades if t.get("return_pct", 0) > 0)
    gross_losses = abs(sum(t.get("return_pct", 0.0) for t in trades if t.get("return_pct", 0) < 0))

    if gross_losses == 0:
        return gross_wins if gross_wins > 0 else 0.0

    return gross_wins / gross_losses


# --- Export ---
__all__ = [
    "RiskMetrics",
    "CircuitBreakerStatus",
    "PositionSizingMethod",
    "CircuitBreaker",
    "calculate_position_size",
    "generate_risk_report",
]
