"""Kraken Connector — REST API wrapper with private portfolio fetch."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
import urllib.parse

import httpx

from apps.atlas.connectors.base import AtlasConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedPortfolio, NormalizedPosition, NormalizedPrice, NormalizedTransaction

logger = logging.getLogger("orion.atlas.connectors.kraken")

BASE_URL = "https://api.kraken.com"


class KrakenConnector(AtlasConnector):
    connector_id = "kraken"
    display_name = "Kraken"

    def __init__(self) -> None:
        self._api_key = os.environ.get("KRAKEN_API_KEY", "")
        self._secret = os.environ.get("KRAKEN_SECRET", "")
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        if not self._api_key:
            logger.warning("Kraken not configured: set KRAKEN_API_KEY and KRAKEN_SECRET")
            return False
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=15)
        try:
            resp = await self._client.get("/0/public/Time")
            ok = resp.status_code == 200
            if ok:
                logger.info("Kraken connected")
            return ok
        except Exception as exc:
            logger.error("Kraken connect failed: %s", exc)
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
            resp = await self._client.get("/0/public/Time")
            latency = (time.time() - start) * 1000
            return ConnectorHealth(connected=resp.status_code == 200, latency_ms=round(latency, 1))
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        if self._client is None:
            return None
        try:
            # Step 1: get asset pairs to map asset IDs to readable names
            asset_info = await self._public_get("/0/public/Assets")
            asset_map: dict[str, str] = {}
            if asset_info and asset_info.get("error") == []:
                for asset_id, info in asset_info.get("result", {}).items():
                    altname = info.get("altname", asset_id)
                    asset_map[asset_id] = altname

            # Step 2: get account balance via private API
            balance_data = await self._private_post("/0/private/Balance")
            if not balance_data or balance_data.get("error") != []:
                logger.warning("Kraken balance error: %s", balance_data)
                return None

            balances = balance_data.get("result", {})

            # Step 3: get USD prices for ticker symbols
            tickers = [f"{asset}USD" for asset in balances if asset_map.get(asset, asset)]
            prices = await self._get_ticker_prices(tickers)

            positions = []
            total_value = 0.0
            for asset_id, balance_str in balances.items():
                balance = float(balance_str)
                if balance <= 0:
                    continue
                symbol = asset_map.get(asset_id, asset_id)
                usd_price = prices.get(f"{symbol}USD", prices.get(f"{asset_id}USD", 0.0))
                if usd_price == 0 and asset_id.startswith("Z"):
                    usd_price = prices.get(f"{asset_id[1:]}USD", 0.0)
                value = balance * usd_price
                total_value += value
                positions.append(NormalizedPosition(
                    symbol=symbol,
                    name=symbol,
                    asset_type="crypto",
                    quantity=balance,
                    current_price=usd_price,
                    value=value,
                ))

            return NormalizedPortfolio(
                total_value=total_value,
                cash=0.0,
                positions=positions,
                provider="kraken",
            )
        except Exception as exc:
            logger.warning("Kraken portfolio failed: %s", exc)
            return None

    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        return []

    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        try:
            ticker = f"{symbol}USD" if not symbol.endswith("USD") else symbol
            prices = await self._get_ticker_prices([ticker])
            price = prices.get(ticker, 0.0)
            if price:
                return NormalizedPrice(symbol=symbol, price=price, source="kraken")
            return None
        except Exception:
            return None

    async def search_symbols(self, query: str) -> list[dict]:
        return []

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "KRAKEN_API_KEY", "label": "API Key", "type": "password"},
            {"key": "KRAKEN_SECRET", "label": "Secret", "type": "password"},
        ]

    # ── Internal ─────────────────────────────────────

    async def _public_get(self, path: str) -> dict | None:
        if self._client is None:
            return None
        try:
            resp = await self._client.get(path)
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None

    async def _private_post(self, path: str, params: dict | None = None) -> dict | None:
        """Kraken API v0 private POST with HMAC-SHA512 signing."""
        if self._client is None:
            return None
        params = params or {}
        url_path = path
        nonce = str(int(time.time() * 1000))
        params["nonce"] = nonce

        # Build POST body
        body = urllib.parse.urlencode(params)

        # Sign: SHA256(nonce + body) then HMAC-SHA512(path, sha256)
        sha256_hash = hashlib.sha256((nonce + body).encode()).digest()
        hmac_message = url_path.encode() + sha256_hash
        signature = hmac.new(
            base64.b64decode(self._secret),
            hmac_message,
            hashlib.sha512,
        ).digest()
        signature_b64 = base64.b64encode(signature).decode()

        headers = {
            "API-Key": self._api_key,
            "API-Sign": signature_b64,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            resp = await self._client.post(path, data=params, headers=headers)
            return resp.json() if resp.status_code == 200 else None
        except Exception as exc:
            logger.warning("Kraken private API error %s: %s", path, exc)
            return None

    async def _get_ticker_prices(self, tickers: list[str]) -> dict[str, float]:
        if not tickers or self._client is None:
            return {}
        try:
            pair = ",".join(tickers)
            resp = await self._client.get(f"/0/public/Ticker?pair={pair}")
            if resp.status_code != 200:
                return {}
            data = resp.json()
            result = data.get("result", {})
            prices: dict[str, float] = {}
            for key, info in result.items():
                price = float(info.get("c", ["0"])[0])
                if price > 0:
                    prices[key] = price
            return prices
        except Exception as exc:
            logger.warning("Kraken ticker error: %s", exc)
            return {}
