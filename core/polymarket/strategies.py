from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("orion.polymarket.strategies")


def _fmt(t: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(t))


class BTCArbitrageStrategy:
    """Binance→Polymarket BTC latency arbitrage.

    Detects micro-moves on Binance 1s candles and trades the 5m
    Polymarket UP/DOWN market before the price catches up.
    Based on Yero/ClawdBot thesis and AdiiX implementation.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._binance_api = self._config.get("binance_api", "https://api.binance.com")
        self._polymarket_id = self._config.get("polymarket_id", "")
        self._btc_move_threshold = self._config.get("btc_move_threshold", 70)
        self._min_seconds_left = self._config.get("min_seconds_left", 120)
        self._max_position = self._config.get("max_position_usd", 1.0)
        self._running = False

    @property
    def name(self) -> str:
        return "polymarket_btc_arb"

    async def check_setup(self) -> dict[str, Any]:
        """Verify Binance API + Polymarket API are reachable."""
        result: dict[str, Any] = {"binance": False, "polymarket": False, "ready": False}
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self._binance_api}/api/v3/ticker/price?symbol=BTCUSDT")
                if r.status_code == 200:
                    result["btc_price"] = float(r.json()["price"])
                    result["binance"] = True
            if self._polymarket_id:
                r2 = await c.get(f"https://clob.polymarket.com/prices?market={self._polymarket_id}", timeout=5)
                if r2.status_code == 200:
                    result["polymarket"] = True
        except Exception as exc:
            logger.warning("BTC arb setup check failed: %s", exc)
        result["ready"] = result["binance"]
        return result

    async def scan_opportunity(self) -> dict[str, Any]:
        """Check current BTC move and Polymarket price for entry signal."""
        result: dict[str, Any] = {"signal": False, "reason": "", "btc_move": 0}
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{self._binance_api}/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=2")
                if r.status_code != 200:
                    result["reason"] = "Binance API error"
                    return result
                klines = r.json()
                if len(klines) < 2:
                    result["reason"] = "Not enough klines"
                    return result
                prev_close = float(klines[0][4])
                curr_price = float(klines[1][4])
                move = abs(curr_price - prev_close)
                result["btc_move"] = round(move, 2)
                result["btc_price"] = curr_price
                result["direction"] = "up" if curr_price > prev_close else "down"

                if move >= self._btc_move_threshold:
                    result["signal"] = True
                    result["reason"] = f"BTC moved ${move:.0f} in 1m (threshold ${self._btc_move_threshold})"
                else:
                    result["reason"] = f"BTC moved ${move:.0f}, need ${self._btc_move_threshold}"

                if self._polymarket_id:
                    px = await c.get(f"https://clob.polymarket.com/prices?market={self._polymarket_id}", timeout=5)
                    if px.status_code == 200:
                        result["polymarket_prices"] = px.json()
        except Exception as exc:
            result["reason"] = str(exc)
        return result

    def make_plan(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        """Build a trade plan from the scanned opportunity."""
        if not opportunity.get("signal"):
            return {"execute": False, "reason": opportunity.get("reason", "No signal")}

        direction = opportunity.get("direction", "up")
        entry_price = opportunity.get("btc_price", 0)
        return {
            "execute": True,
            "strategy": "BTC latency arb",
            "market_id": self._polymarket_id or "auto-detect",
            "side": "BUY" if direction == "up" else "SELL",
            "outcome": "YES" if direction == "up" else "NO",
            "size_usd": min(self._max_position, 1.0),
            "btc_price": entry_price,
            "btc_move": opportunity.get("btc_move"),
            "confidence": min(0.95, max(0.5, opportunity.get("btc_move", 0) / 150)),
            "timestamp": _fmt(time.time()),
        }


class SmartMoneyCopier:
    """Copy trade signals from top Polymarket traders.

    Inspired by MrFadiAi/Polymarket-bot and ent0n29/polybot.
    Uses top trader PnL/win-rate filtering to generate copy-trade signals.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._target_user = self._config.get("target_user", "")
        self._min_win_rate = self._config.get("min_win_rate", 60.0)
        self._max_traders = self._config.get("max_traders", 5)

    @property
    def name(self) -> str:
        return "polymarket_smart_money"

    async def scan_top_traders(self, limit: int = 20) -> list[dict[str, Any]]:
        """Scan top Polymarket traders by volume/PnL via Gamma API."""
        traders: list[dict[str, Any]] = []
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as c:
                url = f"https://gamma-api.polymarket.com/leaderboard?limit={limit}&offset=0"
                r = await c.get(url)
                if r.status_code == 200:
                    data = r.json()
                    for t in (data or [])[: self._max_traders]:
                        traders.append(
                            {
                                "address": t.get("address", ""),
                                "volume": t.get("volume", 0),
                                "pnl": t.get("pnl", 0),
                                "win_rate": t.get("winRate", 0),
                                "trades": t.get("tradesCount", 0),
                            }
                        )
                else:
                    logger.warning("Leaderboard API: %d", r.status_code)
        except Exception as exc:
            logger.warning("Failed to scan top traders: %s", exc)
        return traders

    async def get_trader_positions(self, address: str) -> list[dict[str, Any]]:
        """Get current open positions for a trader."""
        positions: list[dict[str, Any]] = []
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"https://gamma-api.polymarket.com/positions?user={address}&limit=10&closed=false")
                if r.status_code == 200:
                    positions = r.json()[:5]
        except Exception:
            pass
        return positions

    async def generate_copy_signals(self) -> list[dict[str, Any]]:
        """Generate copy-trade signals from top traders."""
        traders = await self.scan_top_traders()
        signals: list[dict[str, Any]] = []
        for t in traders:
            win_rate = float(t.get("win_rate", 0) or 0)
            if win_rate < self._min_win_rate:
                continue
            positions = await self.get_trader_positions(t.get("address", ""))
            for pos in positions:
                signals.append(
                    {
                        "trader": t["address"][:8],
                        "market": pos.get("market", ""),
                        "outcome": pos.get("outcome", ""),
                        "size": pos.get("size", 0),
                        "trader_win_rate": win_rate,
                        "trader_pnl": t.get("pnl", 0),
                        "timestamp": _fmt(time.time()),
                    }
                )
        return signals


class CompleteSetArbitrage:
    """Complete-set arbitrage on Polymarket binaries.

    When YES+NO prices != 1.0, the difference is arbitrage.
    Based on ent0n29/polybot's complete-set arb strategy.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._min_spread = self._config.get("min_spread", 0.03)

    @property
    def name(self) -> str:
        return "polymarket_complete_arb"

    async def scan_opportunities(self, limit: int = 100) -> list[dict[str, Any]]:
        """Scan markets for complete-set arbitrage opportunities."""
        opportunities: list[dict[str, Any]] = []
        try:
            import httpx

            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(
                    f"https://clob.polymarket.com/markets?limit={min(limit, 200)}",
                )
                if r.status_code != 200:
                    return opportunities
                for m in r.json() or []:
                    mid = m.get("id", "")
                    if not mid:
                        continue
                    px = await c.get(f"https://clob.polymarket.com/prices?market={mid}", timeout=5)
                    if px.status_code != 200:
                        continue
                    prices = px.json()
                    if not prices or not isinstance(prices, dict):
                        continue
                    vals = [float(v) for v in prices.values() if v is not None]
                    if len(vals) < 2:
                        continue
                    total = sum(vals)
                    spread = abs(total - 1.0)
                    if spread >= self._min_spread:
                        opportunities.append(
                            {
                                "market_id": mid,
                                "question": m.get("question", ""),
                                "prices": prices,
                                "total_probability": round(total, 4),
                                "spread": round(spread, 4),
                                "type": "overpriced" if total > 1.0 else "underpriced",
                                "action": "sell_complete_set" if total > 1.0 else "buy_complete_set",
                                "timestamp": _fmt(time.time()),
                            }
                        )
        except Exception as exc:
            logger.warning("Complete-set arb scan failed: %s", exc)
        return sorted(opportunities, key=lambda o: o["spread"], reverse=True)[:10]


class WeatherMarketStrategy:
    """Polymarket temperature settlement prediction.

    Fetches METAR/forecast data for a city and estimates
    settlement probabilities. Based on PolyWeather.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._city = self._config.get("city", "buenos-aires")
        self._open_meteo = self._config.get("open_meteo_api", "https://api.open-meteo.com/v1")

    @property
    def name(self) -> str:
        return "polymarket_weather"

    async def fetch_temperature(self) -> dict[str, Any]:
        """Fetch current + forecast temps from Open-Meteo (free, no key)."""
        try:
            import httpx

            params = {
                "latitude": -34.61,
                "longitude": -58.38,
                "current": "temperature_2m",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 3,
            }
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{self._open_meteo}/forecast", params=params)
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "current_temp": data.get("current", {}).get("temperature_2m"),
                        "today_max": data.get("daily", {}).get("temperature_2m_max", [None])[0],
                        "today_min": data.get("daily", {}).get("temperature_2m_min", [None])[0],
                        "forecast": {
                            "max": data.get("daily", {}).get("temperature_2m_max", []),
                            "min": data.get("daily", {}).get("temperature_2m_min", []),
                        },
                        "source": "open-meteo",
                        "timestamp": _fmt(time.time()),
                    }
                return {"error": f"HTTP {r.status_code}"}
        except Exception as exc:
            return {"error": str(exc)}

    def predict_settlement(self, temp_data: dict[str, Any], threshold: float = 30.0) -> dict[str, Any]:
        """Predict if temperature will be above/below a threshold."""
        current = temp_data.get("current_temp")
        forecast_max = temp_data.get("today_max")
        if current is None:
            return {"predictable": False, "reason": "No temperature data"}
        above = current > threshold or (forecast_max and forecast_max > threshold)
        confidence = min(0.9, abs(current - threshold) / 10 + 0.5)
        return {
            "predictable": True,
            "prediction": "above" if above else "below",
            "threshold_celsius": threshold,
            "current_temp": current,
            "forecast_max": forecast_max,
            "confidence": round(confidence, 2),
            "timestamp": _fmt(time.time()),
        }


class PolymarketLPMarketMaker:
    """Passive market making for Polymarket liquidity rewards.

    Manages limit orders to earn CLOB LP incentives.
    Based on lihanyu81/polymarket_lp_tool.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._active_orders: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "polymarket_lp"

    async def get_open_orders(self) -> list[dict[str, Any]]:
        """Fetch open orders (simulated without auth)."""
        logger.debug("LP: get_open_orders would call /orders with auth headers")
        return self._active_orders

    async def price_orders(self, market_id: str, prices: dict[str, float]) -> list[dict[str, Any]]:
        """Generate pricing recommendations for LP orders."""
        try:
            spread = max(prices.values()) - min(prices.values())
            mid = (max(prices.values()) + min(prices.values())) / 2
            coarse_tick = spread * 0.3
            orders = [
                {"market": market_id, "side": "BUY", "price": round(mid - coarse_tick, 4), "size": 10},
                {"market": market_id, "side": "SELL", "price": round(mid + coarse_tick, 4), "size": 10},
            ]
            logger.info("LP: priced %d orders at spread %.4f", len(orders), spread)
            return orders
        except Exception as exc:
            logger.warning("LP pricing failed: %s", exc)
            return []

    async def summary(self) -> dict[str, Any]:
        orders = await self.get_open_orders()
        return {
            "active_orders": len(orders),
            "strategy": "passive LP / market making",
            "note": "Requires Polymarket CLOB API keys + EIP-712 signing for live trading",
        }
