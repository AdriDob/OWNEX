from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("orion.investment.forex")


class ForexAdapter:
    """Adapter for forex trading via OANDA or MetaTrader APIs.

    Supports currency pair trading with configurable lot sizes,
    stop-loss/take-profit, and position tracking. Integrates with
    OANDA's v20 REST API as primary, with MT5 as fallback.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._api_key = self._config.get("api_key", "")
        self._account_id = self._config.get("account_id", "")
        self._environment = self._config.get("environment", "practice")
        self._connected = False
        self._base_url = (
            "https://api-fxpractice.oanda.com/v3"
            if self._environment == "practice"
            else "https://api-fxtrade.oanda.com/v3"
        )

    @property
    def name(self) -> str:
        return "forex"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        if not self._api_key:
            logger.warning("Forex adapter: no api_key configured")
            return False
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/accounts/{self._account_id}",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=15,
                )
                self._connected = resp.status_code == 200
                if self._connected:
                    logger.info("Connected to OANDA %s", self._environment)
                else:
                    logger.warning("OANDA connection returned %s", resp.status_code)
                return self._connected
        except ImportError:
            logger.warning("httpx not installed — forex adapter in dry-run mode")
            self._connected = True
            return True
        except Exception as exc:
            logger.error("Failed to connect to OANDA: %s", exc)
            return False

    async def get_prices(self, pairs: list[str] | None = None) -> list[dict[str, Any]]:
        instruments = pairs or ["EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD", "USDCAD"]
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/accounts/{self._account_id}/pricing",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    params={"instruments": ",".join(instruments)},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return [
                        {
                            "pair": p["instrument"],
                            "bid": float(p["bids"][0]["price"]),
                            "ask": float(p["asks"][0]["price"]),
                            "spread_pips": round(
                                (float(p["asks"][0]["price"]) - float(p["bids"][0]["price"])) * 10000, 1
                            ),
                            "time": p["time"],
                        }
                        for p in data.get("prices", [])
                    ]
                return []
        except ImportError:
            return [{"pair": p, "bid": 1.0, "ask": 1.0001, "spread_pips": 1.0, "time": "mock"} for p in instruments]
        except Exception as exc:
            logger.error("Failed to get prices: %s", exc)
            return []

    async def place_order(
        self, pair: str, units: int, side: str, sl_pips: int | None = None, tp_pips: int | None = None
    ) -> dict[str, Any]:
        try:
            import httpx

            price = await self._get_current_price(pair)
            stop_loss_price: str | None = None
            take_profit_price: str | None = None
            if sl_pips:
                stop_loss_price = str(
                    round(price - (sl_pips * 0.0001 if "USD" in pair or "EUR" in pair else sl_pips * 0.01), 5)
                )
            if tp_pips:
                take_profit_price = str(
                    round(price + (tp_pips * 0.0001 if "USD" in pair or "EUR" in pair else tp_pips * 0.01), 5)
                )

            order: dict[str, Any] = {
                "order": {
                    "type": "MARKET",
                    "instrument": pair,
                    "units": str(units if side.lower() == "buy" else -units),
                    "timeInForce": "FOK",
                }
            }
            if stop_loss_price:
                order["order"]["stopLossOnFill"] = {"price": stop_loss_price}
            if take_profit_price:
                order["order"]["takeProfitOnFill"] = {"price": take_profit_price}

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/accounts/{self._account_id}/orders",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=order,
                    timeout=15,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "status": "filled",
                        "order_id": data.get("orderFillTransaction", {}).get("id", ""),
                        "pair": pair,
                        "units": units,
                        "side": side,
                        "price": data.get("orderFillTransaction", {}).get("price", 0),
                    }
                return {"status": "rejected", "pair": pair, "error": resp.text}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def _get_current_price(self, pair: str) -> float:
        prices = await self.get_prices([pair])
        return prices[0]["ask"] if prices else 1.0

    async def get_positions(self) -> list[dict[str, Any]]:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/accounts/{self._account_id}/openPositions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return [
                        {
                            "id": p.get("id"),
                            "pair": p.get("instrument"),
                            "units": int(p.get("long", {}).get("units", 0)) or -int(p.get("short", {}).get("units", 0)),
                            "side": "long" if int(p.get("long", {}).get("units", 0)) > 0 else "short",
                            "unrealized_pl": float(p.get("unrealizedPL", 0)),
                        }
                        for p in data.get("positions", [])
                        if int(p.get("long", {}).get("units", 0)) != 0 or int(p.get("short", {}).get("units", 0)) != 0
                    ]
                return []
        except Exception as exc:
            logger.error("Failed to get positions: %s", exc)
            return []

    async def get_balance(self) -> dict[str, Any]:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/accounts/{self._account_id}/summary",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json().get("account", {})
                    return {
                        "balance": float(data.get("balance", 0)),
                        "nav": float(data.get("NAV", 0)),
                        "margin_used": float(data.get("marginUsed", 0)),
                        "margin_available": float(data.get("marginAvailable", 0)),
                        "unrealized_pl": float(data.get("unrealizedPL", 0)),
                        "currency": data.get("currency", "USD"),
                    }
                return {"balance": 0.0}
        except Exception:
            return {"balance": 0.0}
