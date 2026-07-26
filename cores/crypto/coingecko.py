"""CoinGecko price feed — unified price oracle for all crypto assets.

Free tier (100 calls/min, 10k/month) at api.coingecko.com/api/v3.
No API key required for demo.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request

from cores.crypto.base import cache_usd_price

logger = logging.getLogger("cateye.crypto.coingecko")

BASE_URL = "https://api.coingecko.com/api/v3"


def compute_rsi(prices: list[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        diff = prices[-i] - prices[-i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 1)


def compute_sma(prices: list[float], period: int = 20) -> float:
    if len(prices) < period:
        return prices[-1] if prices else 0.0
    return round(sum(prices[-period:]) / period, 2)


def compute_macd(prices: list[float]) -> tuple[float, float, float]:
    fast = 12
    slow = 26
    signal = 9
    if len(prices) < slow + signal:
        return (0.0, 0.0, 0.0)
    ema12 = _ema(prices, fast)
    ema26 = _ema(prices, slow)
    macd_line = ema12 - ema26
    macd_hist = [
        _ema([p for p in prices[: i + 1] if p], fast) - _ema([p for p in prices[: i + 1] if p], slow)
        for i in range(len(prices))
    ]
    macd_hist = [x for x in macd_hist if x != 0.0]
    signal_line = _ema(macd_hist[-signal:] if len(macd_hist) >= signal else macd_hist, min(signal, len(macd_hist)))
    histogram = macd_line - signal_line
    return (round(macd_line, 2), round(signal_line, 2), round(histogram, 2))


def _ema(prices: list[float], period: int) -> float:
    if len(prices) < period:
        return sum(prices) / len(prices)
    k = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = price * k + ema * (1 - k)
    return ema


# CoinGecko IDs for common assets
COINGECKO_IDS: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
    "SOL": "solana",
    "BNB": "binancecoin",
    "ADA": "cardano",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "TRX": "tron",
    "ARB": "arbitrum",
    "OP": "optimism",
    "APT": "aptos",
    "SUI": "sui",
    "NEAR": "near",
    "FET": "fetch-ai",
    "RENDER": "render-token",
    "INJ": "injective-protocol",
    "TIA": "celestia",
    "SEI": "sei-network",
    "PEPE": "pepe",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
}

# Reverse lookup: CoinGecko ID -> symbol
_ID_TO_SYMBOL = {v: k for k, v in COINGECKO_IDS.items()}


class CoinGeckoFeed:
    """Price feed from CoinGecko with in-memory cache."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[dict, float]] = {}  # symbol -> (data, timestamp)
        self._cache_ttl = 60  # seconds
        self._last_call = 0.0
        self._min_interval = 1.5  # sec between calls (respect rate limit)

    def get_price(self, symbol: str, vs_currency: str = "usd") -> float:
        """Get current USD price for a single symbol."""
        data = self._get(symbol, vs_currency)
        if data:
            return data.get(vs_currency, 0.0)
        return 0.0

    def get_prices(self, symbols: list[str], vs_currency: str = "usd") -> dict[str, float]:
        """Get current prices for multiple symbols at once."""
        coin_ids = [COINGECKO_IDS.get(s.upper(), s.lower()) for s in symbols]
        prices = self._fetch_simple_price(coin_ids, vs_currency)
        result: dict[str, float] = {}
        for symbol, cid in COINGECKO_IDS.items():
            if cid in prices:
                result[symbol] = prices[cid].get(vs_currency, 0.0)
        # Also cache
        for symbol, cid in COINGECKO_IDS.items():
            if cid in prices:
                usd_price = prices[cid].get(vs_currency, 0.0)
                cache_usd_price(symbol, usd_price)
        return result

    def get_24h_change(self, symbol: str) -> float | None:
        """Get 24h price change percentage."""
        data = self._get(symbol)
        if data:
            return data.get(f"{list(data.keys())[0]}_24h_change") if len(data) == 1 else None
        return None

    def health(self) -> dict:
        """Check if CoinGecko API is reachable."""
        try:
            req = urllib.request.Request(f"{BASE_URL}/ping", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                ok = resp.status == 200
            return {
                "available": ok,
                "cached_symbols": len(self._cache),
                "cache_ttl": self._cache_ttl,
            }
        except Exception as exc:
            return {"available": False, "error": str(exc), "cached_symbols": len(self._cache)}

    # ── Internal ─────────────────────────────────────

    def _get(self, symbol: str, vs_currency: str = "usd") -> dict | None:
        try:
            coin_id = COINGECKO_IDS.get(symbol.upper())
            if not coin_id:
                return None
            now = time.time()
            cached = self._cache.get(coin_id)
            if cached and (now - cached[1]) < self._cache_ttl:
                return cached[0]

            # Rate limit: ensure at least 1.5s between calls
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)

            result = self._fetch_simple_price([coin_id], vs_currency)
            coin_data = result.get(coin_id, {})
            self._cache[coin_id] = (coin_data, time.time())
            self._last_call = time.time()

            price = coin_data.get(vs_currency, 0.0)
            if price > 0:
                cache_usd_price(symbol.upper(), price)

            return coin_data
        except Exception as exc:
            logger.warning("CoinGecko price fetch failed for %s: %s", symbol, exc)
            return None

    def get_ohlc(self, symbol: str, days: int = 30, vs_currency: str = "usd") -> list[float]:
        """Fetch daily closing prices for technical analysis."""
        coin_id = COINGECKO_IDS.get(symbol.upper())
        if not coin_id:
            return []
        url = f"{BASE_URL}/coins/{coin_id}/ohlc?vs_currency={vs_currency}&days={days}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            return [candle[4] for candle in data]
        except Exception as exc:
            logger.warning("CoinGecko OHLC failed for %s: %s", symbol, exc)
            return []

    def get_technical_signals(self, symbol: str) -> dict:
        """Compute RSI, SMA, MACD for a symbol. Returns dict with signal and interpretation."""
        closes = self.get_ohlc(symbol, days=30)
        if len(closes) < 15:
            return {
                "symbol": symbol,
                "error": "insufficient data",
                "rsi": 50.0,
                "sma_20": 0.0,
                "sma_50": 0.0,
                "macd": (0.0, 0.0, 0.0),
                "signal": "neutral",
                "price": self.get_price(symbol),
            }
        price = closes[-1]
        rsi = compute_rsi(closes, 14)
        sma_20 = compute_sma(closes, 20)
        sma_50 = compute_sma(closes, min(50, len(closes)))
        macd_line, signal_line, histogram = compute_macd(closes)

        signals = []
        if rsi > 70:
            signals.append("overbought")
        elif rsi < 30:
            signals.append("oversold")
        if sma_20 > sma_50:
            signals.append("uptrend")
        else:
            signals.append("downtrend")
        if histogram > 0:
            signals.append("macd_bullish")
        else:
            signals.append("macd_bearish")

        return {
            "symbol": symbol,
            "price": price,
            "rsi": rsi,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "macd_line": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram,
            "signals": signals,
            "samples": len(closes),
        }

    def _fetch_simple_price(self, coin_ids: list[str], vs_currency: str = "usd") -> dict:
        ids_param = ",".join(coin_ids)
        url = f"{BASE_URL}/simple/price?ids={ids_param}&vs_currencies={vs_currency}&include_24hr_change=true"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            logger.warning("CoinGecko API error: %s", exc)
            return {}


_feed: CoinGeckoFeed | None = None


def get_coingecko_feed() -> CoinGeckoFeed:
    global _feed
    if _feed is None:
        _feed = CoinGeckoFeed()
    return _feed
