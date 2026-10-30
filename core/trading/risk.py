"""Risk Engine — Centralized risk management with kill switches.

Centralized risk management with global, strategy, exchange, and asset-level kill switches.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from core.trading.contracts import (
    KillSwitchEvent,
    KillSwitchLevel,
    Order,
    Position,
)

logger = logging.getLogger("ownex.trading.risk")


class RiskLimitType(StrEnum):
    """Types of risk limits."""

    MAX_TOTAL_EXPOSURE = "max_total_exposure"
    MAX_STRATEGY_EXPOSURE = "max_strategy_exposure"
    MAX_ASSET_EXPOSURE = "max_asset_exposure"
    MAX_EXCHANGE_EXPOSURE = "max_exchange_exposure"
    MAX_DAILY_LOSS = "max_daily_loss"
    MAX_WEEKLY_LOSS = "max_weekly_loss"
    MAX_DRAWDOWN = "max_drawdown"
    MAX_LEVERAGE = "max_leverage"
    MAX_POSITION_SIZE = "max_position_size"
    MAX_CORRELATED_EXPOSURE = "max_correlated_exposure"
    MIN_LIQUIDITY = "min_liquidity"
    MAX_SLIPPAGE = "max_slippage"
    MAX_SPREAD = "max_spread"
    STALE_DATA_TIMEOUT = "stale_data_timeout"
    API_HEALTH = "api_health"
    EXCHANGE_HEALTH = "exchange_health"
    MARKET_HALT = "market_halt"
    STRATEGY_HEALTH = "strategy_health"


@dataclass
class RiskLimit:
    """A single risk limit."""

    limit_type: RiskLimitType
    value: Decimal
    current: Decimal = Decimal("0")
    breached: bool = False
    last_check: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class RiskMetrics:
    """Current risk metrics."""

    total_exposure: Decimal = Decimal("0")
    strategy_exposures: dict[str, Decimal] = field(default_factory=dict)
    asset_exposures: dict[str, Decimal] = field(default_factory=dict)
    exchange_exposures: dict[str, Decimal] = field(default_factory=dict)
    daily_pnl: Decimal = Decimal("0")
    weekly_pnl: Decimal = Decimal("0")
    current_drawdown: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    leverage: Decimal = Decimal("0")
    max_position_size: Decimal = Decimal("0")
    correlated_exposure: Decimal = Decimal("0")
    liquidity: Decimal = Decimal("0")
    max_slippage: Decimal = Decimal("0")
    max_spread: Decimal = Decimal("0")
    last_update: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class KillSwitchManager:
    """Manages kill switches at multiple levels."""

    def __init__(self):
        self.kill_switches: dict[KillSwitchLevel, bool] = {
            KillSwitchLevel.GLOBAL: False,
            KillSwitchLevel.STRATEGY: False,
            KillSwitchLevel.EXCHANGE: False,
            KillSwitchLevel.ASSET: False,
        }
        self._strategy_kill_switches: dict[str, bool] = {}
        self._exchange_kill_switches: dict[str, bool] = {}
        self._asset_kill_switches: dict[str, bool] = {}
        self._events: list[KillSwitchEvent] = []

    def activate(
        self,
        level: KillSwitchLevel,
        reason: str,
        trigger: str = "system",
        affected: list[str] | None = None,
        triggered_by: str = "system",
    ) -> KillSwitchEvent:
        """Activate a kill switch."""
        affected = affected or []

        if level == KillSwitchLevel.GLOBAL:
            self.kill_switches[KillSwitchLevel.GLOBAL] = True
        elif level == KillSwitchLevel.STRATEGY:
            for sid in affected:
                self._strategy_kill_switches[sid] = True
        elif level == KillSwitchLevel.EXCHANGE:
            for ex in affected:
                self._exchange_kill_switches[ex] = True
        elif level == KillSwitchLevel.ASSET:
            for asset in affected:
                self._asset_kill_switches[asset] = True

        event = KillSwitchEvent(
            level=level,
            trigger=trigger,
            reason=reason,
            affected=affected,
            triggered_by=triggered_by,
        )
        self._events.append(event)
        logger.critical(f"KILL SWITCH ACTIVATED: {level.value} - {reason}")
        return event

    def deactivate(
        self,
        level: KillSwitchLevel,
        affected: list[str] | None = None,
        triggered_by: str = "human",
    ) -> bool:
        """Deactivate a kill switch (requires human approval)."""
        if triggered_by != "human":
            logger.warning("Kill switch deactivation requires human approval")
            return False

        affected = affected or []

        if level == KillSwitchLevel.GLOBAL:
            self.kill_switches[KillSwitchLevel.GLOBAL] = False
        elif level == KillSwitchLevel.STRATEGY:
            for sid in affected:
                self._strategy_kill_switches[sid] = False
        elif level == KillSwitchLevel.EXCHANGE:
            for ex in affected:
                self._exchange_kill_switches[ex] = False
        elif level == KillSwitchLevel.ASSET:
            for asset in affected:
                self._asset_kill_switches[asset] = False

        logger.info(f"KILL SWITCH DEACTIVATED: {level.value} by {triggered_by}")
        return True

    def is_active(self, level: KillSwitchLevel, identifier: str | None = None) -> bool:
        """Check if a kill switch is active."""
        if level == KillSwitchLevel.GLOBAL:
            return self.kill_switches[KillSwitchLevel.GLOBAL]
        elif level == KillSwitchLevel.STRATEGY and identifier:
            return self.kill_switches[KillSwitchLevel.STRATEGY] or self._strategy_kill_switches.get(identifier, False)
        elif level == KillSwitchLevel.EXCHANGE and identifier:
            return self.kill_switches[KillSwitchLevel.EXCHANGE] or self._exchange_kill_switches.get(identifier, False)
        elif level == KillSwitchLevel.ASSET and identifier:
            return self.kill_switches[KillSwitchLevel.ASSET] or self._asset_kill_switches.get(identifier, False)
        return False

    def get_status(self) -> dict[str, Any]:
        return {
            "global": self.kill_switches[KillSwitchLevel.GLOBAL],
            "strategies": self._strategy_kill_switches,
            "exchanges": self._exchange_kill_switches,
            "assets": self._asset_kill_switches,
            "recent_events": [e.__dict__ for e in self._events[-10:]],
        }


class RiskEngine:
    """Centralized risk management engine."""

    def __init__(self):
        self.limits: dict[RiskLimitType, RiskLimit] = self._default_limits()
        self.metrics = RiskMetrics()
        self.kill_switch = KillSwitchManager()
        self._breach_callbacks: list[callable] = []

    def _default_limits(self) -> dict[RiskLimitType, RiskLimit]:
        return {
            RiskLimitType.MAX_TOTAL_EXPOSURE: RiskLimit(RiskLimitType.MAX_TOTAL_EXPOSURE, Decimal("100000")),
            RiskLimitType.MAX_STRATEGY_EXPOSURE: RiskLimit(RiskLimitType.MAX_STRATEGY_EXPOSURE, Decimal("20000")),
            RiskLimitType.MAX_ASSET_EXPOSURE: RiskLimit(RiskLimitType.MAX_ASSET_EXPOSURE, Decimal("50000")),
            RiskLimitType.MAX_EXCHANGE_EXPOSURE: RiskLimit(RiskLimitType.MAX_EXCHANGE_EXPOSURE, Decimal("100000")),
            RiskLimitType.MAX_DAILY_LOSS: RiskLimit(RiskLimitType.MAX_DAILY_LOSS, Decimal("2000")),
            RiskLimitType.MAX_WEEKLY_LOSS: RiskLimit(RiskLimitType.MAX_WEEKLY_LOSS, Decimal("5000")),
            RiskLimitType.MAX_DRAWDOWN: RiskLimit(RiskLimitType.MAX_DRAWDOWN, Decimal("0.15")),
            RiskLimitType.MAX_LEVERAGE: RiskLimit(RiskLimitType.MAX_LEVERAGE, Decimal("3.0")),
            RiskLimitType.MAX_POSITION_SIZE: RiskLimit(RiskLimitType.MAX_POSITION_SIZE, Decimal("10000")),
            RiskLimitType.MAX_CORRELATED_EXPOSURE: RiskLimit(RiskLimitType.MAX_CORRELATED_EXPOSURE, Decimal("30000")),
            RiskLimitType.MIN_LIQUIDITY: RiskLimit(RiskLimitType.MIN_LIQUIDITY, Decimal("10000")),
            RiskLimitType.MAX_SLIPPAGE: RiskLimit(RiskLimitType.MAX_SLIPPAGE, Decimal("0.005")),
            RiskLimitType.MAX_SPREAD: RiskLimit(RiskLimitType.MAX_SPREAD, Decimal("0.01")),
            RiskLimitType.STALE_DATA_TIMEOUT: RiskLimit(RiskLimitType.STALE_DATA_TIMEOUT, Decimal("30")),  # seconds
        }

    def set_limit(self, limit_type: RiskLimitType, value: Decimal) -> None:
        """Set a risk limit."""
        if limit_type in self.limits:
            self.limits[limit_type].value = value
            logger.info(f"Risk limit updated: {limit_type.value} = {value}")

    def get_limit(self, limit_type: RiskLimitType) -> Decimal:
        return self.limits[limit_type].value

    def update_metrics(self, metrics: RiskMetrics) -> None:
        """Update risk metrics and check limits."""
        self.metrics = metrics
        self._check_limits()

    def _check_limits(self) -> list[KillSwitchEvent]:
        """Check all risk limits and trigger kill switches if breached."""
        triggered = []

        for limit_type, limit in self.limits.items():
            current = getattr(
                self.metrics, limit_type.value.replace("max_", "").replace("min_", "").replace("_", "_"), Decimal("0")
            )
            limit.current = current

            if limit_type == RiskLimitType.MAX_DRAWDOWN:
                breached = current > limit.value
            elif limit_type == RiskLimitType.MIN_LIQUIDITY:
                breached = current < limit.value
            else:
                breached = current > limit.value

            if breached and not limit.breached:
                limit.breached = True
                logger.critical(f"RISK LIMIT BREACHED: {limit_type.value} = {current} > {limit.value}")

                # Trigger appropriate kill switch
                if limit_type in (
                    RiskLimitType.MAX_DRAWDOWN,
                    RiskLimitType.MAX_DAILY_LOSS,
                    RiskLimitType.MAX_WEEKLY_LOSS,
                ):
                    event = self.kill_switch.activate(
                        KillSwitchLevel.GLOBAL,
                        f"Risk limit breached: {limit_type.value}",
                        trigger="risk_engine",
                        triggered_by="system",
                    )
                    triggered.append(event)
                elif limit_type == RiskLimitType.MAX_STRATEGY_EXPOSURE:
                    # Would need to identify which strategy - simplified for now
                    pass

            elif not breached and limit.breached:
                limit.breached = False

        return triggered

    def check_order(self, order: Order, capital_engine: Any) -> tuple[bool, str]:
        """Validate an order against risk limits."""
        # Check global kill switch
        if self.kill_switch.is_active(KillSwitchLevel.GLOBAL):
            return False, "Global kill switch active"

        # Check strategy kill switch
        if self.kill_switch.is_active(KillSwitchLevel.STRATEGY, order.strategy_id):
            return False, f"Strategy {order.strategy_id} kill switch active"

        # Check exchange kill switch
        if self.kill_switch.is_active(KillSwitchLevel.EXCHANGE, order.exchange):
            return False, f"Exchange {order.exchange} kill switch active"

        # Check asset kill switch
        if self.kill_switch.is_active(KillSwitchLevel.ASSET, order.symbol):
            return False, f"Asset {order.symbol} kill switch active"

        # Check position size limit
        if order.quantity * (order.price or Decimal("0")) > self.limits[RiskLimitType.MAX_POSITION_SIZE].value:
            return False, "Order size exceeds max position size"

        # Check total exposure
        if capital_engine:
            total_exposure = capital_engine.get_total_exposure() + (order.quantity * (order.price or Decimal("0")))
            if total_exposure > self.limits[RiskLimitType.MAX_TOTAL_EXPOSURE].value:
                return False, "Total exposure would exceed limit"

        # Check daily loss limit
        if self.metrics.daily_pnl < -self.limits[RiskLimitType.MAX_DAILY_LOSS].value:
            return False, "Daily loss limit exceeded"

        # Check drawdown
        if self.metrics.current_drawdown > self.limits[RiskLimitType.MAX_DRAWDOWN].value:
            return False, "Max drawdown exceeded"

        return True, "OK"

    def check_position(self, position: Position, capital_engine: Any) -> tuple[bool, str]:
        """Validate a position against risk limits."""
        if position.current_exposure > self.limits[RiskLimitType.MAX_STRATEGY_EXPOSURE].value:
            return False, "Position exposure exceeds strategy limit"

        if position.leverage > self.limits[RiskLimitType.MAX_LEVERAGE].value:
            return False, f"Leverage exceeds maximum: {position.leverage}"

        return True, "OK"

    def register_breach_callback(self, callback: callable) -> None:
        """Register a callback for risk limit breaches."""
        self._breach_callbacks.append(callback)

    def get_risk_summary(self) -> dict[str, Any]:
        return {
            "limits": {
                lt.value: {"value": str(limit.value), "current": str(limit.current), "breached": limit.breached}
                for lt, limit in self.limits.items()
            },
            "metrics": {
                "total_exposure": str(self.metrics.total_exposure),
                "daily_pnl": str(self.metrics.daily_pnl),
                "weekly_pnl": str(self.metrics.weekly_pnl),
                "current_drawdown": str(self.metrics.current_drawdown),
                "max_drawdown": str(self.metrics.max_drawdown),
                "leverage": str(self.metrics.leverage),
                "liquidity": str(self.metrics.liquidity),
            },
            "kill_switches": self.kill_switch.get_status(),
        }


# ══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═════════════════════════════════════════════════════════════════════════

_risk_engine: RiskEngine | None = None


def get_risk_engine() -> RiskEngine:
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine
