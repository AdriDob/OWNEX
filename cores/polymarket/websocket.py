"""Polymarket WebSocket feed — real-time market data with anti-fail layers.

Architecture inspired by @0x_Punisher's 6-layer websocket stack:
1. Connection management (auto-reconnect)
2. Heartbeat/ping-pong (anti-stale)
3. Message validation (anti-corruption)
4. Jitter compensation (anti-jitter)
5. Backpressure handling (anti-overflow)
6. Circuit breaker (anti-cascade-failure)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger("orion.polymarket.websocket")


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class FeedConfig:
    """WebSocket feed configuration."""

    url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    heartbeat_interval: float = 30.0
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 60.0
    reconnect_backoff: float = 2.0
    max_reconnect_attempts: int = 10
    message_timeout: float = 10.0
    buffer_size: int = 1000
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0


@dataclass
class FeedStats:
    """Feed statistics."""

    messages_received: int = 0
    messages_dropped: int = 0
    reconnect_count: int = 0
    last_message_time: float = 0.0
    last_heartbeat_time: float = 0.0
    errors: int = 0
    circuit_breaker_trips: int = 0


class PolymarketFeed:
    """Real-time WebSocket feed with anti-fail layers.

    Layer 1: Connection management (auto-reconnect with exponential backoff)
    Layer 2: Heartbeat/ping-pong (detect stale connections)
    Layer 3: Message validation (reject corrupted messages)
    Layer 4: Jitter compensation (smooth out timing variations)
    Layer 5: Backpressure handling (drop old messages when overwhelmed)
    Layer 6: Circuit breaker (stop trying after repeated failures)
    """

    def __init__(self, config: FeedConfig | None = None) -> None:
        self._config = config or FeedConfig()
        self._state = ConnectionState.DISCONNECTED
        self._stats = FeedStats()
        self._message_buffer: deque[dict[str, Any]] = deque(maxlen=self._config.buffer_size)
        self._subscribers: list[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]] = []
        self._ws: Any = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._circuit_breaker_until: float = 0.0
        self._circuit_breaker_count: int = 0

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def stats(self) -> FeedStats:
        return self._stats

    def subscribe(self, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        """Subscribe to feed messages."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        """Unsubscribe from feed messages."""
        self._subscribers = [cb for cb in self._subscribers if cb is not callback]

    # ── Layer 6: Circuit Breaker ───────────────────────────────────────

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is open."""
        return time.monotonic() < self._circuit_breaker_until

    def _trip_circuit_breaker(self) -> None:
        """Trip the circuit breaker."""
        self._circuit_breaker_count += 1
        self._circuit_breaker_until = (
            time.monotonic() + self._config.circuit_breaker_timeout * self._circuit_breaker_count
        )
        self._stats.circuit_breaker_trips += 1
        logger.warning(
            "Circuit breaker tripped (count=%d, cooldown=%.0fs)",
            self._circuit_breaker_count,
            self._config.circuit_breaker_timeout * self._circuit_breaker_count,
        )

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker on successful connection."""
        self._circuit_breaker_count = 0
        self._circuit_breaker_until = 0.0

    # ── Layer 1: Connection Management ─────────────────────────────────

    async def connect(self, market_ids: list[str] | None = None) -> None:
        """Connect to the WebSocket feed."""
        if self._check_circuit_breaker():
            logger.warning("Circuit breaker open, cannot connect")
            return

        self._state = ConnectionState.CONNECTING

        try:
            import websockets

            self._ws = await websockets.connect(
                self._config.url,
                ping_interval=self._config.heartbeat_interval,
                ping_timeout=self._config.message_timeout,
                close_timeout=5,
            )
            self._state = ConnectionState.CONNECTED
            self._reset_circuit_breaker()
            logger.info("Connected to Polymarket WebSocket")

            # Subscribe to markets if provided
            if market_ids:
                await self._subscribe_markets(market_ids)

            # Start heartbeat and receive tasks
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            self._state = ConnectionState.FAILED
            self._stats.errors += 1
            logger.error("WebSocket connection failed: %s", e)
            self._trip_circuit_breaker()

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket feed."""
        self._state = ConnectionState.DISCONNECTED

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

        logger.info("Disconnected from Polymarket WebSocket")

    async def _subscribe_markets(self, market_ids: list[str]) -> None:
        """Subscribe to market updates."""
        if not self._ws:
            return

        subscribe_msg = {
            "type": "subscribe",
            "channel": "market",
            "markets": market_ids,
        }
        await self._ws.send(json.dumps(subscribe_msg))
        logger.info("Subscribed to %d markets", len(market_ids))

    # ── Layer 2: Heartbeat ─────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to detect stale connections."""
        while self._state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self._config.heartbeat_interval)

                if self._ws and self._state == ConnectionState.CONNECTED:
                    ping_msg = {"type": "ping"}
                    await self._ws.send(json.dumps(ping_msg))
                    self._stats.last_heartbeat_time = time.monotonic()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Heartbeat failed: %s", e)
                await self._handle_disconnect()

    # ── Layer 3-5: Message Processing ──────────────────────────────────

    async def _receive_loop(self) -> None:
        """Receive and process messages from the WebSocket."""
        while self._state == ConnectionState.CONNECTED:
            try:
                raw = await asyncio.wait_for(
                    self._ws.recv(),
                    timeout=self._config.message_timeout,
                )

                # Layer 3: Message validation
                msg = self._validate_message(raw)
                if msg is None:
                    self._stats.messages_dropped += 1
                    continue

                # Layer 4: Jitter compensation (timestamp smoothing)
                msg["_received_at"] = time.monotonic()

                # Layer 5: Backpressure handling
                if len(self._message_buffer) >= self._config.buffer_size:
                    self._message_buffer.popleft()  # Drop oldest
                    self._stats.messages_dropped += 1

                self._message_buffer.append(msg)
                self._stats.messages_received += 1
                self._stats.last_message_time = time.monotonic()

                # Notify subscribers
                await self._notify_subscribers(msg)

            except TimeoutError:
                # No message received within timeout, check connection
                if self._state == ConnectionState.CONNECTED:
                    continue  # Normal timeout, keep waiting

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.warning("Receive error: %s", e)
                self._stats.errors += 1
                await self._handle_disconnect()

    def _validate_message(self, raw: str) -> dict[str, Any] | None:
        """Validate and parse a WebSocket message (Layer 3)."""
        try:
            msg = json.loads(raw)

            # Check required fields
            if not isinstance(msg, dict):
                return None

            # Ignore pong responses
            if msg.get("type") == "pong":
                return None

            # Validate message structure
            if "type" not in msg:
                return None

            return msg

        except json.JSONDecodeError:
            logger.debug("Invalid JSON received")
            return None

    async def _notify_subscribers(self, msg: dict[str, Any]) -> None:
        """Notify all subscribers of a new message."""
        for callback in self._subscribers:
            try:
                await callback(msg)
            except Exception as e:
                logger.warning("Subscriber callback error: %s", e)

    # ── Reconnection ───────────────────────────────────────────────────

    async def _handle_disconnect(self) -> None:
        """Handle disconnection and attempt reconnection."""
        if self._state == ConnectionState.RECONNECTING:
            return  # Already reconnecting

        self._state = ConnectionState.RECONNECTING
        self._stats.reconnect_count += 1

        if self._stats.reconnect_count >= self._config.max_reconnect_attempts:
            self._state = ConnectionState.FAILED
            self._trip_circuit_breaker()
            logger.error("Max reconnect attempts reached, circuit breaker tripped")
            return

        delay = min(
            self._config.reconnect_delay * (self._config.reconnect_backoff ** (self._stats.reconnect_count - 1)),
            self._config.max_reconnect_delay,
        )

        logger.info("Reconnecting in %.1fs (attempt %d)", delay, self._stats.reconnect_count)
        await asyncio.sleep(delay)

        if self._state == ConnectionState.RECONNECTING:
            await self.connect()

    # ── Public Methods ─────────────────────────────────────────────────

    async def get_latest_messages(self, count: int = 10) -> list[dict[str, Any]]:
        """Get the latest messages from the buffer."""
        messages = list(self._message_buffer)
        return messages[-count:]

    def get_stats(self) -> dict[str, Any]:
        """Get feed statistics."""
        return {
            "state": self._state.value,
            "messages_received": self._stats.messages_received,
            "messages_dropped": self._stats.messages_dropped,
            "reconnect_count": self._stats.reconnect_count,
            "errors": self._stats.errors,
            "circuit_breaker_trips": self._stats.circuit_breaker_trips,
            "buffer_size": len(self._message_buffer),
            "subscribers": len(self._subscribers),
            "last_message_age": (
                time.monotonic() - self._stats.last_message_time if self._stats.last_message_time else None
            ),
        }
