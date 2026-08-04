"""Coinbase Connector — REST API wrapper with HMAC auth."""

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

logger = logging.getLogger("orion.atlas.connectors.coinbase")

BASE_URL = "https://api.coinbase.com"


class CoinbaseConnector(AtlasConnector):
    connector_id = "coinbase"
    display_name = "Coinbase"

    def __init__(self) -> None:
        self._api_key = os.environ.get("COINBASE_API_KEY", "")
        self._secret = os.environ.get("COINBASE_SECRET", "")
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        if not self._api_key:
            logger.warning("Coinbase not configured: set COINBASE_API_KEY")
            return False
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=15)
        try:
            resp = await self._client.get("/api/v3/brokerage/time")
            ok = resp.status_code == 200
            if ok:
                logger.info("Coinbase connected")
            return ok
        except Exception as exc:
            logger.error("Coinbase connect failed: %s", exc)
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
            resp = await self._client.get("/api/v3/brokerage/time")
            latency = (time.time() - start) * 1000
            return ConnectorHealth(connected=resp.status_code == 200, latency_ms=round(latency, 1))
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        if self._client is None:
            return None
        try:
            path = "/v2/accounts"
            headers = self._auth_headers("GET", path, "")
            resp = await self._client.get(path, headers=headers)
            if resp.status_code != 200:
                logger.warning("Coinbase portfolio error: %d %s", resp.status_code, resp.text[:200])
                return None
            data = resp.json()
            positions = []
            total_value = 0.0
            for acc in data.get("data", []):
                balance = float(acc.get("balance", {}).get("amount", 0))
                if balance > 0:
                    currency = acc.get("currency", "")
                    usd_price = await self._get_usd_price(currency)
                    value = balance * usd_price if usd_price else balance
                    total_value += value
                    positions.append(
                        NormalizedPosition(
                            symbol=currency,
                            name=acc.get("name", currency),
                            asset_type="crypto",
                            quantity=balance,
                            current_price=usd_price or 0.0,
                            value=value,
                        )
                    )
            return NormalizedPortfolio(total_value=total_value, positions=positions, provider="coinbase")
        except Exception as exc:
            logger.warning("Coinbase portfolio failed: %s", exc)
            return None

    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        return []

    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        if self._client is None:
            return None
        try:
            path = f"/v2/prices/{symbol}-USD/spot"
            headers = self._auth_headers("GET", path, "")
            resp = await self._client.get(path, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                price = float(data.get("data", {}).get("amount", 0))
                return NormalizedPrice(symbol=symbol, price=price, source="coinbase")
            return None
        except Exception:
            return None

    async def search_symbols(self, query: str) -> list[dict]:
        return []

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "COINBASE_API_KEY", "label": "API Key", "type": "password"},
            {"key": "COINBASE_SECRET", "label": "Secret", "type": "password"},
        ]

    # ── Internal ─────────────────────────────────────

    def _auth_headers(self, method: str, path: str, body: str = "") -> dict:
        """Generate Coinbase API v2 HMAC auth headers.

        Coinbase uses CB-ACCESS-SIGN = HMAC-SHA256(secret, timestamp + method + path + body)
        """
        timestamp = str(int(time.time()))
        message = timestamp + method.upper() + path + body
        signature = hmac.new(
            self._secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "CB-ACCESS-KEY": self._api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
        }

    async def _get_usd_price(self, currency: str) -> float | None:
        if currency == "USD":
            return 1.0
        try:
            if self._client is None:
                return None
            path = f"/v2/prices/{currency}-USD/spot"
            headers = self._auth_headers("GET", path, "")
            resp = await self._client.get(path, headers=headers)
            if resp.status_code == 200:
                return float(resp.json().get("data", {}).get("amount", 0))
            # fallback to CoinGecko
            from cores.crypto.coingecko import get_coingecko_feed

            return get_coingecko_feed().get_price(currency)
        except Exception:
            return None
