"""Binance WebSocket Feed for BTC/USDT real-time data."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import websockets
from core.polymarket.btc_latency_arb.feeds.base import (
    KlineData,
    PriceFeed,
    TickData,
)

logger = logging.getLogger("orion.polymarket.btc_latency_arb.feeds.binance")


class BinanceWSFeed(PriceFeed):
    """Binance WebSocket feed for BTC/USDT ticks and klines.

    Streams:
    - btcusdt@trade: Real-time trade ticks
    - btcusdt@kline_1s: 1-second klines
    """

    def __init__(
        self,
        ws_url: str = "wss://stream.binance.com:9443/ws",
        symbol: str = "btcusdt",
    ) -> None:
        super().__init__("binance")
        self._ws_url = ws_url
        self._symbol = symbol.lower()
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._tasks: list[asyncio.Task] = []
        self._last_ping = 0.0
        self._ping_interval = 20.0  # seconds
        self._last_kline: KlineData | None = None

    async def connect(self) -> bool:
        """Connect to Binance WebSocket."""
        try:
            self._ws = await websockets.connect(
                self._ws_url,
                ping_interval=None,  # We handle pings manually
                close_timeout=5,
                max_size=2**20,
            )
            self._running = True
            self._reset_reconnect()

            # Start message handler
            task = asyncio.create_task(self._message_handler())
            self._tasks.append(task)

            # Start ping task
            ping_task = asyncio.create_task(self._ping_loop())
            self._tasks.append(ping_task)

            # Subscribe to streams
            await self._subscribe_streams()

            self._emit("connected", {"symbol": self._symbol})
            logger.info("Binance WS connected: %s", self._symbol)
            return True

        except Exception as e:
            logger.error("Binance WS connection failed: %s", e)
            self._running = False
            self._emit("error", e)
            return False

    async def disconnect(self) -> None:
        """Disconnect from Binance WebSocket."""
        self._running = False

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        self._emit("disconnected", {"symbol": self._symbol})
        logger.info("Binance WS disconnected: %s", self._symbol)

    async def _subscribe_streams(self) -> None:
        """Subscribe to trade and kline streams."""
        if not self._ws:
            return

        streams = [
            f"{self._symbol}@trade",
            f"{self._symbol}@kline_1s",
        ]

        msg = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000),
        }

        try:
            await self._ws.send(json.dumps(msg))
            logger.debug("Binance subscribed to: %s", streams)
        except Exception as e:
            logger.error("Binance subscribe failed: %s", e)
            raise

    async def _message_handler(self) -> None:
        """Handle incoming WebSocket messages."""
        if not self._ws:
            return

        try:
            async for message in self._ws:
                if not self._running:
                    break

                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError:
                    logger.warning("Binance: Invalid JSON received")
                except Exception as e:
                    logger.exception("Binance message processing error: %s", e)
                    self._emit("error", e)

        except websockets.ConnectionClosed as e:
            logger.warning("Binance WS connection closed: %s", e)
            if self._running:
                self._emit("disconnected", {"reason": str(e)})
                await self._reconnect()
        except Exception as e:
            logger.exception("Binance message handler error: %s", e)
            self._emit("error", e)
            if self._running:
                await self._reconnect()

    async def _process_message(self, data: dict[str, Any]) -> None:
        """Process incoming message based on stream type."""
        # Handle subscription confirmation
        if "result" in data and data["result"] is None:
            return

        # Handle combined stream format: {"stream": "...", "data": {...}}
        if "stream" in data and "data" in data:
            stream = data["stream"]
            payload = data["data"]

            if stream.endswith("@trade"):
                self._process_trade(payload)
            elif stream.endswith("@kline_1s"):
                self._process_kline(payload)
            return

        # Handle direct stream format (single stream connection)
        if "e" in data:
            event_type = data["e"]
            if event_type == "trade":
                self._process_trade(data)
            elif event_type == "kline":
                self._process_kline(data)

    def _process_trade(self, data: dict[str, Any]) -> None:
        """Process trade tick data."""
        try:
            tick = TickData(
                symbol=self._symbol.upper(),
                price=float(data["p"]),
                quantity=float(data["q"]),
                timestamp=int(data["T"]),
                is_buyer_maker=data.get("m", False),
            )
            self._emit("tick", tick)
        except Exception as e:
            logger.warning("Binance trade parse error: %s", e)

    def _process_kline(self, data: dict[str, Any]) -> None:
        """Process kline data."""
        try:
            k = data.get("k", data)  # Handle both formats
            if not k:
                return

            kline = KlineData(
                symbol=self._symbol.upper(),
                open_price=float(k["o"]),
                high_price=float(k["h"]),
                low_price=float(k["l"]),
                close_price=float(k["c"]),
                volume=float(k["v"]),
                start_time=int(k["t"]),
                close_time=int(k["T"]),
                is_closed=k.get("x", False),
            )

            # Only emit on kline close for 1s klines, or every update
            if kline.is_closed or self._last_kline is None:
                self._emit("kline", kline)
                self._last_kline = kline

        except Exception as e:
            logger.warning("Binance kline parse error: %s", e)

    async def _ping_loop(self) -> None:
        """Send periodic pings to keep connection alive."""
        while self._running and self._ws:
            try:
                await asyncio.sleep(self._ping_interval)
                if self._ws and self._running:
                    await self._ws.ping()
                    self._last_ping = time.time()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Binance ping error: %s", e)
                break

    async def subscribe_ticker(self, symbol: str) -> None:
        """Subscribe to ticker (trade stream)."""
        self._symbol = symbol.lower()
        if self._running and self._ws:
            await self._subscribe_streams()

    async def subscribe_kline(self, symbol: str, interval: str = "1s") -> None:
        """Subscribe to kline stream."""
        self._symbol = symbol.lower()
        if self._running and self._ws:
            await self._subscribe_streams()

    async def subscribe_orderbook(self, market_id: str) -> None:
        """Not applicable for Binance feed."""
        logger.debug("Binance feed: subscribe_orderbook not supported")

    def get_current_price(self) -> float | None:
        """Get last known price from kline."""
        if self._last_kline:
            return self._last_kline.close_price
        return None

    def get_last_kline(self) -> KlineData | None:
        """Get last completed kline."""
        return self._last_kline
