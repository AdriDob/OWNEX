"""Base WebSocket Feed Interface for Polymarket BTC Latency Arb."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("orion.polymarket.btc_latency_arb.feeds")


@dataclass(slots=True)
class TickData:
    """Real-time tick data from exchange."""

    symbol: str
    price: float
    quantity: float
    timestamp: int  # ms since epoch
    is_buyer_maker: bool = False


@dataclass(slots=True)
class KlineData:
    """Kline/candlestick data."""

    symbol: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    start_time: int  # ms since epoch
    close_time: int  # ms since epoch
    is_closed: bool = False


@dataclass(slots=True)
class OrderBookUpdate:
    """Order book update from Polymarket CLOB."""

    market_id: str
    bids: list[tuple[float, float]]  # (price, size)
    asks: list[tuple[float, float]]  # (price, size)
    timestamp: int


FeedCallback = Callable[[Any], None]


class PriceFeed(ABC):
    """Abstract base class for price feeds."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._running = False
        self._callbacks: dict[str, list[FeedCallback]] = {
            "tick": [],
            "kline": [],
            "orderbook": [],
            "error": [],
            "connected": [],
            "disconnected": [],
        }
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 1.0  # seconds, exponential backoff

    @property
    def is_running(self) -> bool:
        return self._running

    @abstractmethod
    async def connect(self) -> bool:
        """Establish WebSocket connection. Returns True on success."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        ...

    @abstractmethod
    async def subscribe_ticker(self, symbol: str) -> None:
        """Subscribe to real-time ticker updates."""
        ...

    @abstractmethod
    async def subscribe_kline(self, symbol: str, interval: str = "1s") -> None:
        """Subscribe to kline/candlestick updates."""
        ...

    @abstractmethod
    async def subscribe_orderbook(self, market_id: str) -> None:
        """Subscribe to order book updates (Polymarket)."""
        ...

    def on_tick(self, callback: FeedCallback) -> Callable[[], None]:
        """Register callback for tick updates. Returns unsubscribe function."""
        self._callbacks["tick"].append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks["tick"]:
                self._callbacks["tick"].remove(callback)

        return unsubscribe

    def on_kline(self, callback: FeedCallback) -> Callable[[], None]:
        """Register callback for kline updates. Returns unsubscribe function."""
        self._callbacks["kline"].append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks["kline"]:
                self._callbacks["kline"].remove(callback)

        return unsubscribe

    def on_orderbook(self, callback: FeedCallback) -> Callable[[], None]:
        """Register callback for orderbook updates. Returns unsubscribe function."""
        self._callbacks["orderbook"].append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks["orderbook"]:
                self._callbacks["orderbook"].remove(callback)

        return unsubscribe

    def on_error(self, callback: FeedCallback) -> Callable[[], None]:
        """Register callback for errors. Returns unsubscribe function."""
        self._callbacks["error"].append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks["error"]:
                self._callbacks["error"].remove(callback)

        return unsubscribe

    def on_connected(self, callback: FeedCallback) -> Callable[[], None]:
        """Register callback for connection events. Returns unsubscribe function."""
        self._callbacks["connected"].append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks["connected"]:
                self._callbacks["connected"].remove(callback)

        return unsubscribe

    def on_disconnected(self, callback: FeedCallback) -> Callable[[], None]:
        """Register callback for disconnection events. Returns unsubscribe function."""
        self._callbacks["disconnected"].append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks["disconnected"]:
                self._callbacks["disconnected"].remove(callback)

        return unsubscribe

    def _emit(self, event_type: str, data: Any) -> None:
        """Emit event to all registered callbacks."""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                logger.exception("Callback error for %s.%s: %s", self.name, event_type, e)

    async def _reconnect(self) -> None:
        """Handle reconnection with exponential backoff."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("%s: Max reconnection attempts reached", self.name)
            self._emit("error", Exception("Max reconnection attempts reached"))
            return

        self._reconnect_attempts += 1
        delay = min(self._reconnect_delay * (2 ** (self._reconnect_attempts - 1)), 60)
        logger.warning(
            "%s: Reconnecting in %.1fs (attempt %d/%d)",
            self.name,
            delay,
            self._reconnect_attempts,
            self._max_reconnect_attempts,
        )

        import asyncio

        await asyncio.sleep(delay)

        if not self._running:
            return

        try:
            await self.connect()
        except Exception as e:
            logger.error("%s: Reconnection failed: %s", self.name, e)
            await self._reconnect()

    def _reset_reconnect(self) -> None:
        """Reset reconnection counter on successful connection."""
        self._reconnect_attempts = 0

    def get_stats(self) -> dict[str, Any]:
        """Get feed statistics."""
        return {
            "name": self.name,
            "running": self._running,
            "reconnect_attempts": self._reconnect_attempts,
            "callbacks": {k: len(v) for k, v in self._callbacks.items()},
        }
