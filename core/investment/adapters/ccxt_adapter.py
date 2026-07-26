from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("orion.investment.ccxt")


class CCXTAdapter:
    """Unified exchange adapter via CCXT library.

    Provides a simplified interface for common trading operations across
    100+ exchanges. Follows the pattern established by core/trading/executor.py
    but generalized for multi-exchange use.
    """

    def __init__(self, exchange_id: str = "binance", config: dict[str, Any] | None = None) -> None:
        self._exchange_id = exchange_id
        self._config = config or {}
        self._exchange: Any = None
        self._connected = False

    @property
    def name(self) -> str:
        return f"ccxt:{self._exchange_id}"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        try:
            import ccxt.async_support as ccxt

            exchange_class = getattr(ccxt, self._exchange_id, None)
            if not exchange_class:
                logger.error("Unknown exchange: %s", self._exchange_id)
                return False

            creds: dict[str, Any] = {
                "apiKey": self._config.get("api_key", ""),
                "secret": self._config.get("api_secret", ""),
            }
            if password := self._config.get("password"):
                creds["password"] = password

            self._exchange = exchange_class(creds)
            if self._config.get("testnet"):
                self._exchange.set_sandbox_mode(True)

            await self._exchange.load_markets()
            self._connected = True
            logger.info("Connected to %s (%d markets)", self._exchange_id, len(self._exchange.markets))
            return True
        except ImportError:
            logger.error("ccxt not installed. Run: pip install ccxt")
            return False
        except Exception as e:
            logger.error("Failed to connect to %s: %s", self._exchange_id, e)
            return False

    async def disconnect(self) -> None:
        if self._exchange and self._connected:
            from contextlib import suppress

            with suppress(Exception):
                await self._exchange.close()
            self._connected = False

    async def get_balance(self) -> dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        try:
            balance = await self._exchange.fetch_balance()
            total: dict[str, float] = {}
            for currency, data in (balance.get("total", {}) or {}).items():
                if float(data or 0) > 0:
                    total[currency] = float(data)
            return {"total": total, "free": balance.get("free", {}), "used": balance.get("used", {})}
        except Exception as e:
            logger.error("Balance fetch failed: %s", e)
            return {"error": str(e)}

    async def get_ticker(self, symbol: str) -> dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        try:
            ticker = await self._exchange.fetch_ticker(symbol)
            return {
                "symbol": ticker.get("symbol", symbol),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "last": ticker.get("last"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "change_pct": ticker.get("percentage"),
            }
        except Exception as e:
            logger.error("Ticker fetch failed for %s: %s", symbol, e)
            return {"error": str(e)}

    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[list]:
        if not self._connected:
            return []
        try:
            return await self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except Exception as e:
            logger.error("OHLCV fetch failed: %s", e)
            return []

    async def get_order_book(self, symbol: str, limit: int = 10) -> dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        try:
            ob = await self._exchange.fetch_order_book(symbol, limit=limit)
            return {"bids": ob.get("bids", [])[:limit], "asks": ob.get("asks", [])[:limit]}
        except Exception as e:
            logger.error("Orderbook fetch failed: %s", e)
            return {"error": str(e)}

    async def create_market_order(self, symbol: str, side: str, amount: float) -> dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        try:
            order = await self._exchange.create_order(symbol, "market", side, amount)
            return {
                "id": order.get("id", ""),
                "symbol": order.get("symbol", symbol),
                "side": order.get("side", side),
                "amount": order.get("amount"),
                "price": order.get("price"),
                "cost": order.get("cost"),
                "fee": order.get("fee"),
                "status": order.get("status"),
                "filled": order.get("filled"),
                "remaining": order.get("remaining"),
            }
        except Exception as e:
            logger.error("Order failed: %s", e)
            return {"error": str(e)}

    async def create_limit_order(self, symbol: str, side: str, amount: float, price: float) -> dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        try:
            order = await self._exchange.create_order(symbol, "limit", side, amount, price)
            return {
                "id": order.get("id", ""),
                "symbol": order.get("symbol", symbol),
                "side": order.get("side", side),
                "amount": order.get("amount"),
                "price": order.get("price"),
                "cost": order.get("cost"),
                "status": order.get("status"),
                "filled": order.get("filled"),
                "remaining": order.get("remaining"),
            }
        except Exception as e:
            logger.error("Limit order failed: %s", e)
            return {"error": str(e)}

    async def get_open_orders(self, symbol: str | None = None) -> list[dict]:
        if not self._connected:
            return []
        try:
            orders = await self._exchange.fetch_open_orders(symbol)
            return [
                {
                    "id": o.get("id"),
                    "symbol": o.get("symbol"),
                    "side": o.get("side"),
                    "type": o.get("type"),
                    "price": o.get("price"),
                    "amount": o.get("amount"),
                    "filled": o.get("filled"),
                    "remaining": o.get("remaining"),
                    "status": o.get("status"),
                    "timestamp": o.get("timestamp"),
                }
                for o in orders
            ]
        except Exception as e:
            logger.error("Open orders fetch failed: %s", e)
            return []

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        if not self._connected:
            return False
        try:
            await self._exchange.cancel_order(order_id, symbol)
            return True
        except Exception as e:
            logger.error("Cancel order failed: %s", e)
            return False

    async def get_my_trades(self, symbol: str, limit: int = 50) -> list[dict]:
        if not self._connected:
            return []
        try:
            trades = await self._exchange.fetch_my_trades(symbol, limit=limit)
            return [
                {
                    "id": t.get("id"),
                    "order": t.get("order"),
                    "symbol": t.get("symbol"),
                    "side": t.get("side"),
                    "price": t.get("price"),
                    "amount": t.get("amount"),
                    "cost": t.get("cost"),
                    "fee": t.get("fee"),
                    "timestamp": t.get("timestamp"),
                }
                for t in trades
            ]
        except Exception as e:
            logger.error("Trades fetch failed: %s", e)
            return []

    async def get_exchange_info(self) -> dict[str, Any]:
        """Get exchange info without connecting (public endpoints only)."""
        try:
            import ccxt.async_support as ccxt

            exchange_class = getattr(ccxt, self._exchange_id, None)
            if not exchange_class:
                return {"error": f"Unknown exchange: {self._exchange_id}"}
            ex = exchange_class()
            await ex.load_markets()
            info = {
                "id": self._exchange_id,
                "name": ex.name if hasattr(ex, "name") else self._exchange_id,
                "markets_count": len(ex.markets) if ex.markets else 0,
                "has": {k: v for k, v in (ex.has or {}).items() if v},
                "timeframes": list((ex.timeframes or {}).keys()) if hasattr(ex, "timeframes") else [],
            }
            await ex.close()
            return info
        except ImportError:
            return {"error": "ccxt not installed"}
        except Exception as e:
            return {"error": str(e)}
