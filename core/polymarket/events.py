"""Polymarket EventBus Integration — publish/subscribe for trading signals.

Integrates Polymarket strategies with the system EventBus for:
- Real-time signal notifications
- Position updates
- Trade executions
- Risk alerts
"""

from __future__ import annotations

import logging
import time
from typing import Any

from cores.events.event_bus import get_event_bus

logger = logging.getLogger("orion.polymarket.events")


class PolymarketEventBus:
    """Polymarket event publisher/subscriber.

    Publishes events:
    - polymarket:signal — New trading signal detected
    - polymarket:position:opened — Position opened
    - polymarket:position:closed — Position closed
    - polymarket:trade:executed — Trade executed
    - polymarket:risk:alert — Risk limit warning
    - polymarket:scan:completed — Market scan completed
    """

    def __init__(self) -> None:
        self._bus = get_event_bus()

    def publish_signal(
        self,
        strategy: str,
        market_id: str,
        outcome: str,
        price: float,
        size_usd: float,
        signal_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publish a trading signal event."""
        self._bus.publish(
            "polymarket:signal",
            strategy=strategy,
            market_id=market_id,
            outcome=outcome,
            price=price,
            size_usd=size_usd,
            signal_type=signal_type,
            metadata=metadata or {},
            message=f"Signal: {outcome} @ ${price:.4f} (size: ${size_usd:.2f})",
        )
        logger.info(
            "Published signal: %s %s @ $%.4f ($%.2f)",
            strategy,
            outcome,
            price,
            size_usd,
        )

    def publish_position_opened(
        self,
        market_id: str,
        outcome: str,
        entry_price: float,
        size_usd: float,
        strategy: str,
    ) -> None:
        """Publish position opened event."""
        self._bus.publish(
            "polymarket:position:opened",
            market_id=market_id,
            outcome=outcome,
            entry_price=entry_price,
            size_usd=size_usd,
            strategy=strategy,
            message=f"Position opened: {outcome} @ ${entry_price:.4f}",
        )
        logger.info(
            "Position opened: %s @ $%.4f ($%.2f)",
            outcome,
            entry_price,
            size_usd,
        )

    def publish_position_closed(
        self,
        market_id: str,
        outcome: str,
        entry_price: float,
        exit_price: float,
        size_usd: float,
        pnl: float,
        reason: str,
    ) -> None:
        """Publish position closed event."""
        emoji = "✅" if pnl > 0 else "❌"
        self._bus.publish(
            "polymarket:position:closed",
            market_id=market_id,
            outcome=outcome,
            entry_price=entry_price,
            exit_price=exit_price,
            size_usd=size_usd,
            pnl=pnl,
            reason=reason,
            message=f"{emoji} Position closed: PnL ${pnl:+.2f} ({reason})",
        )
        logger.info(
            "Position closed: %s PnL $%.2f (%s)",
            outcome,
            pnl,
            reason,
        )

    def publish_trade_executed(
        self,
        market_id: str,
        outcome: str,
        side: str,
        price: float,
        size_usd: float,
        fees: float,
        strategy: str,
    ) -> None:
        """Publish trade executed event."""
        self._bus.publish(
            "polymarket:trade:executed",
            market_id=market_id,
            outcome=outcome,
            side=side,
            price=price,
            size_usd=size_usd,
            fees=fees,
            strategy=strategy,
            message=f"Trade executed: {side} {outcome} @ ${price:.4f}",
        )
        logger.info(
            "Trade executed: %s %s @ $%.4f ($%.2f, fees: $%.4f)",
            side,
            outcome,
            price,
            size_usd,
            fees,
        )

    def publish_risk_alert(
        self,
        alert_type: str,
        message: str,
        current_value: float,
        limit_value: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publish risk alert event."""
        self._bus.publish(
            "polymarket:risk:alert",
            alert_type=alert_type,
            current_value=current_value,
            limit_value=limit_value,
            metadata=metadata or {},
            message=f"Risk alert: {message}",
        )
        logger.warning("Risk alert: %s (current: %.2f, limit: %.2f)", message, current_value, limit_value)

    def publish_scan_completed(
        self,
        markets_scanned: int,
        signals_found: int,
        opportunities: int,
        duration_ms: float,
    ) -> None:
        """Publish market scan completed event."""
        self._bus.publish(
            "polymarket:scan:completed",
            markets_scanned=markets_scanned,
            signals_found=signals_found,
            opportunities=opportunities,
            duration_ms=duration_ms,
            message=f"Scan completed: {markets_scanned} markets, {signals_found} signals",
        )
        logger.info(
            "Scan completed: %d markets, %d signals (%.0fms)",
            markets_scanned,
            signals_found,
            duration_ms,
        )

    def subscribe_signals(self, handler: Any) -> None:
        """Subscribe to trading signals."""
        self._bus.subscribe("polymarket:signal", handler)

    def subscribe_positions(self, handler: Any) -> None:
        """Subscribe to position updates."""
        self._bus.subscribe("polymarket:position:opened", handler)
        self._bus.subscribe("polymarket:position:closed", handler)

    def subscribe_trades(self, handler: Any) -> None:
        """Subscribe to trade executions."""
        self._bus.subscribe("polymarket:trade:executed", handler)

    def subscribe_risk(self, handler: Any) -> None:
        """Subscribe to risk alerts."""
        self._bus.subscribe("polymarket:risk:alert", handler)

    def subscribe_all(self, handler: Any) -> None:
        """Subscribe to all Polymarket events."""
        self._bus.subscribe("polymarket:*", handler)


# Singleton
_polymarket_bus: PolymarketEventBus | None = None


def get_polymarket_event_bus() -> PolymarketEventBus:
    """Get or create the Polymarket event bus singleton."""
    global _polymarket_bus
    if _polymarket_bus is None:
        _polymarket_bus = PolymarketEventBus()
    return _polymarket_bus
