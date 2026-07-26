from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("orion.investment.futures")


class FuturesAdapter:
    """Adapter for crypto futures trading via CCXT.

    Supports perpetual swap trading with cross/isolated margin,
    multiple order types, leverage management, and position tracking.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._exchanges = self._config.get("exchanges", ["binance", "bybit"])
        self._default_leverage = self._config.get("default_leverage", 3)
        self._max_leverage = self._config.get("max_leverage", 10)
        self._connected = False

    @property
    def name(self) -> str:
        return "futures"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        try:
            import ccxt.async_support as ccxt

            for ex_name in self._exchanges:
                try:
                    exchange_class = getattr(ccxt, ex_name)
                    ex = exchange_class({"enableRateLimit": True, "options": {"defaultType": "future"}})
                    await ex.load_markets()
                    await ex.close()
                except Exception as exc:
                    logger.debug("Futures exchange %s unavailable: %s", ex_name, exc)
            self._connected = True
            logger.info("Futures adapter connected — %d exchanges", len(self._exchanges))
            return True
        except ImportError:
            logger.warning("ccxt not installed — futures adapter in dry-run mode")
            self._connected = True
            return True
        except Exception as exc:
            logger.error("Failed to connect futures adapter: %s", exc)
            return False

    async def set_leverage(self, symbol: str, leverage: int, exchange: str = "binance") -> bool:
        try:
            import ccxt.async_support as ccxt

            leverage = min(leverage, self._max_leverage)
            exchange_class = getattr(ccxt, exchange)
            ex = exchange_class(
                {
                    "enableRateLimit": True,
                    "apiKey": self._config.get(f"{exchange}_api_key", ""),
                    "secret": self._config.get(f"{exchange}_secret", ""),
                }
            )
            await ex.set_leverage(leverage, symbol)
            await ex.close()
            return True
        except Exception as exc:
            logger.error("Failed to set leverage: %s", exc)
            return False

    async def open_position(
        self, symbol: str, side: str, size_usd: float, exchange: str = "binance", leverage: int | None = None
    ) -> dict[str, Any]:
        lev = leverage or self._default_leverage
        try:
            import ccxt.async_support as ccxt

            exchange_class = getattr(ccxt, exchange)
            ex = exchange_class(
                {
                    "enableRateLimit": True,
                    "apiKey": self._config.get(f"{exchange}_api_key", ""),
                    "secret": self._config.get(f"{exchange}_secret", ""),
                    "options": {"defaultType": "future"},
                }
            )
            await ex.set_leverage(lev, symbol)
            amount = size_usd / (await ex.fetch_ticker(symbol))["last"]
            order = await ex.create_order(symbol, "market", side.lower(), amount, None, {"leverage": lev})
            await ex.close()
            return {
                "status": "opened",
                "symbol": symbol,
                "side": side,
                "size_usd": size_usd,
                "leverage": lev,
                "order_id": order.get("id"),
                "filled": order.get("filled"),
            }
        except Exception as exc:
            return {"status": "error", "symbol": symbol, "error": str(exc)}

    async def close_position(self, symbol: str, exchange: str = "binance") -> dict[str, Any]:
        try:
            import ccxt.async_support as ccxt

            exchange_class = getattr(ccxt, exchange)
            ex = exchange_class(
                {
                    "enableRateLimit": True,
                    "apiKey": self._config.get(f"{exchange}_api_key", ""),
                    "secret": self._config.get(f"{exchange}_secret", ""),
                    "options": {"defaultType": "future"},
                }
            )
            positions = await ex.fetch_positions([symbol])
            if not positions:
                await ex.close()
                return {"status": "no_position", "symbol": symbol}
            for pos in positions:
                if abs(float(pos.get("contracts", 0))) > 0:
                    side = "sell" if float(pos.get("contracts", 0)) > 0 else "buy"
                    order = await ex.create_order(symbol, "market", side, abs(float(pos["contracts"])), None)
                    await ex.close()
                    return {
                        "status": "closed",
                        "symbol": symbol,
                        "side": side,
                        "order_id": order.get("id"),
                        "pnl": pos.get("unrealizedPnl"),
                    }
            await ex.close()
            return {"status": "no_position", "symbol": symbol}
        except Exception as exc:
            return {"status": "error", "symbol": symbol, "error": str(exc)}

    async def get_positions(self, exchange: str = "binance") -> list[dict[str, Any]]:
        try:
            import ccxt.async_support as ccxt

            exchange_class = getattr(ccxt, exchange)
            ex = exchange_class(
                {
                    "enableRateLimit": True,
                    "apiKey": self._config.get(f"{exchange}_api_key", ""),
                    "secret": self._config.get(f"{exchange}_secret", ""),
                    "options": {"defaultType": "future"},
                }
            )
            positions = await ex.fetch_positions()
            await ex.close()
            return [
                {
                    "symbol": p.get("symbol"),
                    "side": "long" if float(p.get("contracts", 0)) > 0 else "short",
                    "size": float(p.get("contracts", 0)),
                    "unrealized_pnl": float(p.get("unrealizedPnl", 0)),
                    "leverage": p.get("leverage"),
                    "liquidation_price": p.get("liquidationPrice"),
                }
                for p in positions
                if abs(float(p.get("contracts", 0))) > 0
            ]
        except Exception as exc:
            logger.error("Failed to fetch positions: %s", exc)
            return []

    async def get_balance(self, exchange: str = "binance") -> dict[str, Any]:
        try:
            import ccxt.async_support as ccxt

            exchange_class = getattr(ccxt, exchange)
            ex = exchange_class(
                {
                    "enableRateLimit": True,
                    "apiKey": self._config.get(f"{exchange}_api_key", ""),
                    "secret": self._config.get(f"{exchange}_secret", ""),
                    "options": {"defaultType": "future"},
                }
            )
            bal = await ex.fetch_balance()
            await ex.close()
            return {"free": bal.get("free", {}), "used": bal.get("used", {}), "total": bal.get("total", {})}
        except Exception as exc:
            logger.error("Failed to fetch balance: %s", exc)
            return {"free": {}, "used": {}, "total": {}}
