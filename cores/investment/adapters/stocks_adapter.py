from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("orion.investment.stocks")


class AlpacaAdapter:
    """Adapter for Alpaca Markets stock/options trading.

    Supports US equities, options, and crypto via Alpaca's v2 API.
    Paper trading by default; live trading with API keys.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._api_key = self._config.get("api_key", "")
        self._secret_key = self._config.get("secret_key", "")
        self._base_url = self._config.get("base_url", "https://paper-api.alpaca.markets")
        self._connected = False

    @property
    def name(self) -> str:
        return "alpaca"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        if not self._api_key or not self._secret_key:
            logger.warning("Alpaca adapter: no API keys configured — running in dry-run mode")
            self._connected = True
            return True
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/v2/account",
                    headers={
                        "APCA-API-KEY-ID": self._api_key,
                        "APCA-API-SECRET-KEY": self._secret_key,
                    },
                    timeout=10,
                )
                self._connected = resp.status_code == 200
                if self._connected:
                    logger.info("Connected to Alpaca (paper trading)")
                else:
                    logger.warning("Alpaca connection returned %d", resp.status_code)
                return self._connected
        except ImportError:
            logger.warning("httpx not installed — Alpaca adapter in dry-run mode")
            self._connected = True
            return True
        except Exception as exc:
            logger.error("Failed to connect to Alpaca: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._connected = False

    async def get_account(self) -> dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/v2/account",
                    headers={
                        "APCA-API-KEY-ID": self._api_key,
                        "APCA-API-SECRET-KEY": self._secret_key,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "account_id": data.get("id"),
                        "status": data.get("status"),
                        "equity": float(data.get("equity", 0)),
                        "cash": float(data.get("cash", 0)),
                        "buying_power": float(data.get("buying_power", 0)),
                        "day_trade_count": int(data.get("day_trade_count", 0)),
                        "pattern_day_trader": data.get("pattern_day_trader", False),
                        "currency": data.get("currency", "USD"),
                    }
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.error("Account fetch failed: %s", exc)
            return {"error": str(exc)}

    async def get_positions(self) -> list[dict[str, Any]]:
        if not self._connected:
            return []
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/v2/positions",
                    headers={
                        "APCA-API-KEY-ID": self._api_key,
                        "APCA-API-SECRET-KEY": self._secret_key,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    return [
                        {
                            "symbol": p.get("symbol"),
                            "asset_class": p.get("asset_class"),
                            "qty": float(p.get("qty", 0)),
                            "side": p.get("side"),
                            "market_value": float(p.get("market_value", 0)),
                            "cost_basis": float(p.get("cost_basis", 0)),
                            "unrealized_pl": float(p.get("unrealized_pl", 0)),
                            "unrealized_plpc": float(p.get("unrealized_plpc", 0)),
                            "current_price": float(p.get("current_price", 0)),
                        }
                        for p in resp.json()
                    ]
                return []
        except Exception as exc:
            logger.error("Positions fetch failed: %s", exc)
            return []

    async def get_order(self, order_id: str) -> dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/v2/orders/{order_id}",
                    headers={
                        "APCA-API-KEY-ID": self._api_key,
                        "APCA-API-SECRET-KEY": self._secret_key,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "id": data.get("id"),
                        "symbol": data.get("symbol"),
                        "side": data.get("side"),
                        "type": data.get("type"),
                        "qty": float(data.get("qty", 0)),
                        "filled_qty": float(data.get("filled_qty", 0)),
                        "price": float(data.get("price", 0)),
                        "status": data.get("status"),
                        "created_at": data.get("created_at"),
                    }
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"error": str(exc)}

    async def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: float | None = None,
        stop_price: float | None = None,
        order_class: str = "simple",
        take_profit: float | None = None,
        stop_loss: float | None = None,
    ) -> dict[str, Any]:
        """Place a stock or options order.

        Supports simple, bracket, and stop orders for equities and options.
        """
        if not self._connected:
            return {"status": "not_connected"}
        try:
            import httpx

            body: dict[str, Any] = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "qty": str(qty),
                "time_in_force": time_in_force,
                "order_class": order_class,
            }
            if limit_price is not None:
                body["limit_price"] = str(limit_price)
            if stop_price is not None:
                body["stop_price"] = str(stop_price)
            if take_profit is not None:
                body["take_profit"] = {"limit_price": str(take_profit)}
            if stop_loss is not None:
                body["stop_loss"] = {"stop_price": str(stop_loss)}

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/v2/orders",
                    headers={
                        "APCA-API-KEY-ID": self._api_key,
                        "APCA-API-SECRET-KEY": self._secret_key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=15,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "status": "accepted",
                        "order_id": data.get("id"),
                        "symbol": data.get("symbol"),
                        "side": data.get("side"),
                        "qty": float(data.get("qty", 0)),
                        "type": data.get("type"),
                        "order_status": data.get("status"),
                    }
                return {"status": "rejected", "error": resp.text}
        except Exception as exc:
            logger.error("Order placement failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    async def get_market_data(self, symbol: str) -> dict[str, Any]:
        """Get current market data for a symbol."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/v2/assets/{symbol}",
                    headers={
                        "APCA-API-KEY-ID": self._api_key,
                        "APCA-API-SECRET-KEY": self._secret_key,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "symbol": data.get("symbol"),
                        "name": data.get("name"),
                        "asset_class": data.get("asset_class"),
                        "exchange": data.get("exchange"),
                        "status": data.get("status"),
                        "tradable": data.get("tradable"),
                        "marginable": data.get("marginable"),
                        "shortable": data.get("shortable"),
                        "easy_to_borrow": data.get("easy_to_borrow"),
                    }
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"error": str(exc)}

    async def get_option_chain(self, underlying: str) -> list[dict[str, Any]]:
        """Get option chain for an underlying equity."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/v2/assets/{underlying}/options",
                    headers={
                        "APCA-API-KEY-ID": self._api_key,
                        "APCA-API-SECRET-KEY": self._secret_key,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    return resp.json() or []
                return []
        except Exception as exc:
            logger.error("Option chain fetch failed: %s", exc)
            return []


class IBKRAdapter:
    """Adapter for Interactive Brokers (IBKR) stock/options/futures trading.

    Uses IBKR's TWS/IB Gateway via the ib_insync library.
    Supports stocks, options, futures, and forex.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._host = self._config.get("host", "127.0.0.1")
        self._port = self._config.get("port", 7497)
        self._client_id = self._config.get("client_id", 1)
        self._connected = False

    @property
    def name(self) -> str:
        return "ibkr"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        try:
            from ib_insync import IB

            self._ib = IB()
            self._ib.connect(self._host, self._port, clientId=self._client_id)
            self._connected = True
            logger.info("Connected to IBKR at %s:%d", self._host, self._port)
            return True
        except ImportError:
            logger.warning("ib_insync not installed — IBKR adapter in dry-run mode")
            self._connected = True
            return True
        except Exception as exc:
            logger.error("Failed to connect to IBKR: %s", exc)
            return False

    async def disconnect(self) -> None:
        if hasattr(self, "_ib") and self._ib.isConnected():
            self._ib.disconnect()
        self._connected = False

    async def get_account(self) -> dict[str, Any]:
        if not self._connected:
            return {"error": "Not connected"}
        try:
            ib = getattr(self, "_ib", None)
            if ib is None:
                return {"error": "IB not initialized"}
            account = ib.accountSummary()
            values = {item.tag: item.value for item in account}
            return {
                "account_id": values.get("Account", ""),
                "status": "connected",
                "equity": float(values.get("NetLiquidation", 0)),
                "cash": float(values.get("CashBalance", 0)),
                "buying_power": float(values.get("BuyingPower", 0)),
                "currency": values.get("Currency", "USD"),
            }
        except Exception as exc:
            return {"error": str(exc)}

    async def get_positions(self) -> list[dict[str, Any]]:
        if not self._connected:
            return []
        try:
            ib = getattr(self, "_ib", None)
            if ib is None:
                return []
            positions = ib.positions()
            return [
                {
                    "symbol": p.contract.symbol,
                    "asset_class": p.contract.secType,
                    "qty": p.position,
                    "side": "long" if p.position > 0 else "short",
                    "market_value": p.marketValue,
                    "cost_basis": p.avgCost,
                    "unrealized_pl": p.unrealizedPNL,
                    "current_price": p.marketPrice,
                }
                for p in positions
            ]
        except Exception as exc:
            logger.error("IBKR positions fetch failed: %s", exc)
            return []

    async def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MKT",
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        strike: float | None = None,
        right: str | None = None,
        last_trade_date_or_contract_month: str | None = None,
    ) -> dict[str, Any]:
        """Place a stock, option, or futures order via IBKR."""
        if not self._connected:
            return {"status": "not_connected"}
        try:
            from ib_insync import Contract, LimitOrder, MarketOrder

            ib = getattr(self, "_ib", None)
            if ib is None:
                return {"error": "IB not initialized"}

            if sec_type == "OPT" and strike and right and last_trade_date_or_contract_month:
                contract = Contract(
                    symbol=symbol,
                    secType="OPT",
                    exchange=exchange,
                    currency=currency,
                    strike=strike,
                    right=right,
                    lastTradeDateOrContractMonth=last_trade_date_or_contract_month,
                )
            else:
                contract = Contract(
                    symbol=symbol,
                    secType=sec_type,
                    exchange=exchange,
                    currency=currency,
                )

            if order_type.upper() == "MKT":
                order = MarketOrder(side, qty)
            elif order_type.upper() == "LMT":
                order = LimitOrder(side, qty, 0.0)
            else:
                order = MarketOrder(side, qty)

            trade = ib.placeOrder(contract, order)
            return {
                "status": "placed",
                "order_id": trade.order.orderId,
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "order_type": order_type,
            }
        except Exception as exc:
            logger.error("IBKR order placement failed: %s", exc)
            return {"status": "error", "error": str(exc)}


def build_alpaca_adapter(config: dict[str, Any] | None = None) -> AlpacaAdapter:
    """Factory function to create Alpaca adapter."""
    return AlpacaAdapter(config)


def build_ibkr_adapter(config: dict[str, Any] | None = None) -> IBKRAdapter:
    """Factory function to create IBKR adapter."""
    return IBKRAdapter(config)
