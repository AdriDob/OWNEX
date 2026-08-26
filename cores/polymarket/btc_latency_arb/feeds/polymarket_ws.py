"""Polymarket CLOB WebSocket Feed for real-time order book data."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from typing import Any

import websockets
from core.polymarket.btc_latency_arb.feeds.base import (
    OrderBookUpdate,
    PriceFeed,
)

logger = logging.getLogger("orion.polymarket.btc_latency_arb.feeds.polymarket")


class PolymarketWSFeed(PriceFeed):
    """Polymarket CLOB WebSocket feed for order book updates.

    Connects to: wss://clob.polymarket.com/ws
    Subscribes to market orderbook for UP/DOWN BTC markets.
    """

    def __init__(
        self,
        ws_url: str = "wss://clob.polymarket.com/ws",
        market_id: str = "",
    ) -> None:
        super().__init__("polymarket")
        self._ws_url = ws_url
        self._market_id = market_id
        self._ws: websockets.ClientConnection | None = None
        self._tasks: list[asyncio.Task] = []
        self._last_orderbook: OrderBookUpdate | None = None
        self._ping_interval = 30.0

    async def connect(self) -> bool:
        """Connect to Polymarket CLOB WebSocket."""
        try:
            self._ws = await websockets.connect(
                self._ws_url,
                ping_interval=None,
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

            # Subscribe to market if ID provided
            if self._market_id:
                await self.subscribe_orderbook(self._market_id)

            self._emit("connected", {"market_id": self._market_id})
            logger.info("Polymarket WS connected: %s", self._market_id)
            return True

        except Exception as e:
            logger.error("Polymarket WS connection failed: %s", e)
            self._running = False
            self._emit("error", e)
            return False

    async def disconnect(self) -> None:
        """Disconnect from Polymarket WebSocket."""
        self._running = False

        for task in self._tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()

        if self._ws:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None

        self._emit("disconnected", {"market_id": self._market_id})
        logger.info("Polymarket WS disconnected: %s", self._market_id)

    async def _message_handler(self) -> None:
        """Handle incoming WebSocket messages from Polymarket CLOB."""
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
                    logger.warning("Polymarket: Invalid JSON received")
                except Exception as e:
                    logger.exception("Polymarket message processing error: %s", e)
                    self._emit("error", e)

        except websockets.ConnectionClosed as e:
            logger.warning("Polymarket WS connection closed: %s", e)
            if self._running:
                self._emit("disconnected", {"reason": str(e)})
                await self._reconnect()
        except Exception as e:
            logger.exception("Polymarket message handler error: %s", e)
            self._emit("error", e)
            if self._running:
                await self._reconnect()

    async def _process_message(self, data: dict[str, Any]) -> None:
        """Process Polymarket CLOB message."""
        msg_type = data.get("type", "")

        if msg_type == "orderbook" or msg_type == "book":
            self._process_orderbook(data)
        elif msg_type == "price_change":
            self._process_price_change(data)
        elif msg_type == "subscribed":
            logger.debug("Polymarket subscribed: %s", data)
        elif msg_type == "error":
            logger.error("Polymarket error: %s", data)
            self._emit("error", Exception(data.get("message", "Unknown error")))
        else:
            logger.debug("Polymarket unknown message type: %s", msg_type)

    def _process_orderbook(self, data: dict[str, Any]) -> None:
        """Process orderbook snapshot/update."""
        try:
            market_id = data.get("market", data.get("market_id", self._market_id))
            bids = [(float(b[0]), float(b[1])) for b in data.get("bids", [])]
            asks = [(float(a[0]), float(a[1])) for a in data.get("asks", [])]
            timestamp = int(data.get("timestamp", time.time() * 1000))

            ob_update = OrderBookUpdate(
                market_id=market_id,
                bids=bids,
                asks=asks,
                timestamp=timestamp,
            )

            self._last_orderbook = ob_update
            self._emit("orderbook", ob_update)

        except Exception as e:
            logger.warning("Polymarket orderbook parse error: %s", e)

    def _process_price_change(self, data: dict[str, Any]) -> None:
        """Process price change notification."""
        # Could emit a tick-like event for price changes
        try:
            market_id = data.get("market", self._market_id)
            price = float(data.get("price", 0))
            side = data.get("side", "")  # "buy" or "sell"

            # Emit as a synthetic tick
            from core.polymarket.btc_latency_arb.feeds.base import TickData

            tick = TickData(
                symbol=market_id,
                price=price,
                quantity=0.0,
                timestamp=int(data.get("timestamp", time.time() * 1000)),
                is_buyer_maker=(side == "sell"),
            )
            self._emit("tick", tick)

        except Exception as e:
            logger.warning("Polymarket price_change parse error: %s", e)

    async def _ping_loop(self) -> None:
        """Send periodic pings."""
        while self._running and self._ws:
            try:
                await asyncio.sleep(self._ping_interval)
                if self._ws and self._running:
                    await self._ws.ping()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Polymarket ping error: %s", e)
                break

    async def subscribe_ticker(self, symbol: str) -> None:
        """Not directly applicable - use subscribe_orderbook."""
        self._market_id = symbol
        if self._running:
            await self.subscribe_orderbook(symbol)

    async def subscribe_kline(self, symbol: str, interval: str = "1s") -> None:
        """Not supported by Polymarket CLOB WS."""
        logger.debug("Polymarket feed: subscribe_kline not supported")

    async def subscribe_orderbook(self, market_id: str) -> None:
        """Subscribe to orderbook for a market."""
        self._market_id = market_id
        if not self._ws or not self._running:
            return

        msg = {
            "type": "subscribe",
            "market": market_id,
            "channels": ["orderbook"],
        }

        try:
            await self._ws.send(json.dumps(msg))
            logger.debug("Polymarket subscribed to orderbook: %s", market_id)
        except Exception as e:
            logger.error("Polymarket subscribe failed: %s", e)
            raise

    def get_last_orderbook(self) -> OrderBookUpdate | None:
        """Get last orderbook snapshot."""
        return self._last_orderbook

    def get_best_bid_ask(self) -> tuple[float | None, float | None]:
        """Get best bid and ask from last orderbook."""
        if not self._last_orderbook:
            return None, None
        best_bid = self._last_orderbook.bids[0][0] if self._last_orderbook.bids else None
        best_ask = self._last_orderbook.asks[0][0] if self._last_orderbook.asks else None
        return best_bid, best_ask

    def get_mid_price(self) -> float | None:
        """Calculate mid price from best bid/ask."""
        bid, ask = self.get_best_bid_ask()
        if bid is not None and ask is not None:
            return (bid + ask) / 2
        return None
