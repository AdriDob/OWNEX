"""Binance Connector — REST API wrapper."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time

import httpx

from apps.atlas.connectors.base import AtlasConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedPortfolio, NormalizedPosition, NormalizedPrice, NormalizedTransaction

logger = logging.getLogger("orion.atlas.connectors.binance")

BASE_URL = "https://api.binance.com"


class BinanceConnector(AtlasConnector):
    connector_id = "binance"
    display_name = "Binance"

    def __init__(self) -> None:
        self._api_key = os.environ.get("BINANCE_API_KEY", "")
        self._secret_key = os.environ.get("BINANCE_SECRET_KEY", "")
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        if not self._api_key or not self._secret_key:
            logger.warning("Binance not configured: set BINANCE_API_KEY and BINANCE_SECRET_KEY")
            return False
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=15)
        try:
            resp = await self._client.get("/api/v3/ping")
            ok = resp.status_code == 200
            if ok:
                logger.info("Binance connected")
            return ok
        except Exception as exc:
            logger.error("Binance connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health(self) -> ConnectorHealth:
        try:
            start = time.time()
            if self._client is None:
                return ConnectorHealth(connected=False, error="Not connected")
            resp = await self._client.get("/api/v3/ping")
            latency = (time.time() - start) * 1000
            return ConnectorHealth(
                connected=resp.status_code == 200,
                latency_ms=round(latency, 1),
            )
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        if self._client is None:
            return None
        try:
            account = await self._signed_get("/api/v3/account")
            if not account:
                return None
            balances = account.get("balances", [])
            positions = []
            total_value = 0.0
            for b in balances:
                free = float(b.get("free", 0))
                locked = float(b.get("locked", 0))
                total = free + locked
                if total > 0:
                    # Fetch current price for non-zero assets
                    price = await self._get_price(b["asset"])
                    value = total * price if price else 0.0
                    total_value += value
                    positions.append(NormalizedPosition(
                        symbol=b["asset"],
                        name=b["asset"],
                        asset_type="crypto",
                        quantity=total,
                        current_price=price or 0.0,
                        value=value,
                    ))
            return NormalizedPortfolio(
                total_value=total_value,
                cash=0.0,
                positions=positions,
                provider="binance",
            )
        except Exception as exc:
            logger.warning("Binance portfolio failed: %s", exc)
            return None

    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        return []

    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        price = await self._get_price(symbol.replace("USD", "USDT"))
        if price is None:
            return None
        return NormalizedPrice(symbol=symbol, price=price, source="binance")

    async def search_symbols(self, query: str) -> list[dict]:
        if self._client is None:
            return []
        try:
            resp = await self._client.get("/api/v3/exchangeInfo")
            if resp.status_code != 200:
                return []
            data = resp.json()
            symbols = data.get("symbols", [])
            results = []
            for s in symbols:
                if query.upper() in s["symbol"] and s["status"] == "TRADING":
                    results.append({"symbol": s["symbol"], "name": s["baseAsset"], "type": "crypto"})
            return results[:20]
        except Exception:
            return []

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "BINANCE_API_KEY", "label": "API Key", "type": "password"},
            {"key": "BINANCE_SECRET_KEY", "label": "Secret Key", "type": "password"},
        ]

    # ── Internal ─────────────────────────────────────────────────

    async def _signed_get(self, path: str, params: dict | None = None) -> dict | None:
        if self._client is None:
            return None
        params = params or {}
        params["timestamp"] = int(time.time() * 1000)
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        signature = hmac.new(self._secret_key.encode(), query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = signature
        resp = await self._client.get(path, params=params, headers={"X-MBX-APIKEY": self._api_key})
        return resp.json() if resp.status_code == 200 else None

    async def _get_price(self, symbol: str) -> float | None:
        if self._client is None:
            return None
        try:
            resp = await self._client.get("/api/v3/ticker/price", params={"symbol": symbol})
            if resp.status_code == 200:
                return float(resp.json().get("price", 0))
            return None
        except Exception:
            return None
