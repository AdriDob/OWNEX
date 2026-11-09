"""IOL WebSocket market-data client (official docs: developers.iolinversiones.com/docs/websocket).

Read-only streaming: quotes (Q), order book (B), trades (T). Up to 50 titles per
connection, identifiers formatted as SYMBOL|MARKET|TERM. Auth via OAuth token
(action=auth_token) right after connect; heartbeat {"action":"ping"} every 15s.

No order/trade endpoints exist here — this is market data only.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import websockets

logger = logging.getLogger(__name__)

WS_URL = "wss://stream-marketdata.invertironline.com"
MAX_TITLES_PER_CONNECTION = 50
HEARTBEAT_INTERVAL_SECONDS = 15.0
CHANNEL_KEYS = ("trades", "quotes", "order_book")


class IOLStreamError(Exception):
    """Server-sent WS error (400/401/403/404/429/500)."""

    def __init__(self, code: int, msg: str):
        super().__init__(f"IOL WS error {code}: {msg}")
        self.code = code
        self.msg = msg


def title(symbol: str, market: str = "BCBA", term: str = "T0") -> str:
    return f"{symbol}|{market}|{term}"


def build_subscribe(titles_quotes: list[str], titles_trades: list[str] | None = None, titles_book: list[str] | None = None) -> dict[str, Any]:
    """All three channel keys are mandatory; unused ones go as []."""
    total = len(titles_quotes) + len(titles_trades or []) + len(titles_book or [])
    if total > MAX_TITLES_PER_CONNECTION:
        raise ValueError(f"IOL WS supports max {MAX_TITLES_PER_CONNECTION} titles per connection")
    return {
        "action": "subscribe",
        "trades": list(titles_trades or []),
        "quotes": list(titles_quotes),
        "order_book": list(titles_book or []),
    }


def parse_message(raw: str | bytes) -> dict[str, Any] | None:
    """Parse a raw WS frame into a normalized dict, or None for heartbeats/acks."""
    data = json.loads(raw)
    if data.get("type") == "Error":
        raise IOLStreamError(int(data.get("code") or 0), str(data.get("msg") or ""))
    if data.get("type") not in ("Q", "B", "T"):
        return None
    msg = data.get("msg") or {}
    out: dict[str, Any] = {
        "type": data["type"],
        "symbol": msg.get("S"),
        "market": msg.get("M"),
        "term": msg.get("T"),
        "ts": msg.get("D"),
        "code": data.get("code"),
    }
    if data["type"] == "Q":
        levels = msg.get("V") or []
        bid = next((v for v in levels if v.get("T") == "BID"), None)
        offer = next((v for v in levels if v.get("T") == "OFFER"), None)
        out["bid"] = bid.get("P") if bid else None
        out["bid_size"] = bid.get("X") if bid else None
        out["ask"] = offer.get("P") if offer else None
        out["ask_size"] = offer.get("X") if offer else None
    elif data["type"] == "B":
        levels = msg.get("V") or []
        out["bids"] = sorted((v for v in levels if v.get("T") == "BID"), key=lambda v: v.get("N") or 0)
        out["offers"] = sorted((v for v in levels if v.get("T") == "OFFER"), key=lambda v: v.get("N") or 0)
    else:  # T — trades
        out.update({"last": msg.get("P"), "variation_pct": msg.get("V"), "day_volume": msg.get("TS"), "day_amount": msg.get("TP")})
    return out


class IOLStreamClient:
    """Async WS client. One connection = one subscription batch."""

    def __init__(self, url: str = WS_URL, heartbeat: float = HEARTBEAT_INTERVAL_SECONDS):
        self.url = url
        self.heartbeat = heartbeat
        self._ws: Any = None
        self._hb_task: asyncio.Task | None = None

    async def __aenter__(self) -> IOLStreamClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def connect(self, *, token: str | None = None, username: str | None = None, password: str | None = None) -> None:
        self._ws = await websockets.connect(self.url)
        if token:
            await self._send({"action": "auth_token", "token": token})
        elif username and password:
            await self._send({"action": "auth", "username": username, "password": password})
        else:
            await self.close()
            raise ValueError("IOL WS requires token or username+password")

    async def _send(self, payload: dict[str, Any]) -> None:
        assert self._ws is not None
        await self._ws.send(json.dumps(payload))

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat)
            try:
                await self._send({"action": "ping"})
            except Exception:
                return

    async def subscribe(self, symbols: list[str], *, market: str = "BCBA", term: str = "T0", channels: tuple[str, ...] = ("quotes",)) -> None:
        """Subscribe symbols to channels. channels ⊆ {quotes, order_book, trades}."""
        titles = [title(s, market, term) for s in symbols]
        if len(titles) > MAX_TITLES_PER_CONNECTION:
            raise ValueError(f"max {MAX_TITLES_PER_CONNECTION} titles per connection")
        payload = {"action": "subscribe", "trades": [], "quotes": [], "order_book": []}
        for ch in channels:
            if ch not in CHANNEL_KEYS:
                raise ValueError(f"unknown channel {ch!r}")
            payload[ch] = titles
        await self._send(payload)
        if self._hb_task is None or self._hb_task.done():
            self._hb_task = asyncio.create_task(self._heartbeat_loop())

    async def messages(self) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed market messages until the socket closes."""
        assert self._ws is not None
        async for raw in self._ws:
            try:
                parsed = parse_message(raw)
            except IOLStreamError:
                raise
            except Exception as exc:
                logger.warning("IOL WS unparseable frame: %s", exc)
                continue
            if parsed is not None:
                yield parsed

    async def close(self) -> None:
        if self._hb_task:
            self._hb_task.cancel()
            self._hb_task = None
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.send(json.dumps({"action": "disconnect"}))
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None


async def fetch_quotes_once(token: str, symbols: list[str], *, market: str = "BCBA", term: str = "T0", timeout: float = 10.0) -> dict[str, dict[str, Any]]:
    """Connect, subscribe quotes, collect first Q per symbol, disconnect.

    Returns {title: parsed_quote}. Used for one-shot valuation without keeping
    a persistent connection. Read-only: never sends order messages.
    """
    got: dict[str, dict[str, Any]] = {}
    want = {title(s, market, term) for s in symbols}
    async with IOLStreamClient() as client:
        await client.connect(token=token)
        await client.subscribe(symbols, market=market, term=term, channels=("quotes",))
        try:
            async with asyncio.timeout(timeout):
                async for msg in client.messages():
                    key = title(str(msg.get("symbol") or ""), str(msg.get("market") or ""), str(msg.get("term") or ""))
                    if key in want:
                        got[key] = msg
                        if len(got) >= len(want):
                            break
        except TimeoutError:
            logger.info("IOL WS quote fetch timed out after %.1fs (%d/%d received)", timeout, len(got), len(want))
    return got
