from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("orion.investment.global_arbitrage")


class GlobalArbitrageAdapter:
    """Adapter for cross-border arbitrage detection and execution.

    Monitors price discrepancies across cryptocurrency exchanges and
    decentralized finance protocols. Supports triangular, cross-exchange,
    and cross-chain arbitrage with automated execution.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._exchanges = self._config.get(
            "exchanges",
            ["binance", "okx", "kraken", "coinbase", "bybit", "bitget", "mexc", "gateio"],
        )
        self._min_spread_pct = self._config.get("min_spread_pct", 0.5)
        self._max_position_usd = self._config.get("max_position_usd", 10000)
        # cap de cordura: spreads spot reales entre exchanges líquidos no superan un
        # ~10%; valores mayores son tickers basura/ilíquidos que corrompen el scan
        self._spread_sanity_max = self._config.get("spread_sanity_max", 10.0)
        # liquidez mínima (24h quoteVolume) suma de ambas puntas para ser ejecutable
        self._min_quote_volume_usd = self._config.get("min_quote_volume_usd", 500000.0)
        self._connected = False

    @property
    def name(self) -> str:
        return "global_arbitrage"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        try:
            import ccxt.async_support as ccxt

            for ex_name in self._exchanges:
                try:
                    exchange_class = getattr(ccxt, ex_name)
                    ex = exchange_class({"enableRateLimit": True})
                    await ex.load_markets()
                    await ex.close()
                except Exception as exc:
                    logger.debug("Exchange %s unavailable: %s", ex_name, exc)
            self._connected = True
            logger.info("Arbitrage adapter connected — %d exchanges configured", len(self._exchanges))
            return True
        except ImportError:
            logger.warning("ccxt not installed — arbitrage adapter in dry-run mode")
            self._connected = True
            return True
        except Exception as exc:
            logger.error("Failed to initialize arbitrage adapter: %s", exc)
            return False

    async def scan_opportunities(self) -> list[dict[str, Any]]:
        """Scan across exchanges for price discrepancies."""
        opportunities = []
        try:
            import ccxt.async_support as ccxt

            tickers: dict[str, dict[str, Any]] = {}
            for ex_name in self._exchanges:
                try:
                    exchange_class = getattr(ccxt, ex_name)
                    ex = exchange_class({"enableRateLimit": True})
                    ex_tickers = await ex.fetch_tickers()
                    tickers[ex_name] = {
                        s: {"bid": t.get("bid"), "ask": t.get("ask"), "qv": t.get("quoteVolume") or 0}
                        for s, t in ex_tickers.items()
                        if t.get("bid") and t.get("ask")
                    }
                    await ex.close()
                except Exception:
                    continue

            for symbol in set().union(*(t.keys() for t in tickers.values())):
                bids = {ex: tickers[ex][symbol]["bid"] for ex in tickers if symbol in tickers[ex]}
                asks = {ex: tickers[ex][symbol]["ask"] for ex in tickers if symbol in tickers[ex]}
                if len(bids) < 2:
                    continue
                # liquidez mínima (24h quoteVolume) sumada en ambas puntas: solo
                # pares de facto ejecutables, evita polvo y señales fantasma
                if self._min_quote_volume_usd and sum(
                    tickers[ex][symbol]["qv"] for ex in tickers if symbol in tickers[ex]
                ) < self._min_quote_volume_usd:
                    continue
                best_bid_ex = max(bids, key=lambda k: bids[k])
                best_ask_ex = min(asks, key=lambda k: asks[k])
                spread = (bids[best_bid_ex] - asks[best_ask_ex]) / asks[best_ask_ex] * 100
                if not (self._min_spread_pct <= spread <= self._spread_sanity_max):
                    continue
                opportunities.append(
                    {
                        "symbol": symbol,
                        "buy_on": best_ask_ex,
                        "buy_price": asks[best_ask_ex],
                        "sell_on": best_bid_ex,
                        "sell_price": bids[best_bid_ex],
                        "spread_pct": round(spread, 2),
                        "estimated_profit_usd": round(spread / 100 * self._max_position_usd, 2),
                    }
                )
            return sorted(opportunities, key=lambda o: o["spread_pct"], reverse=True)
        except ImportError:
            logger.warning("ccxt not installed — returning mock opportunity")
            return [
                {
                    "symbol": "BTC/USDT",
                    "buy_on": "kraken",
                    "buy_price": 65432,
                    "sell_on": "coinbase",
                    "sell_price": 65890,
                    "spread_pct": 0.7,
                    "estimated_profit_usd": 70.0,
                }
            ]
        except Exception as exc:
            logger.error("Arbitrage scan failed: %s", exc)
            return []

    async def execute_trade(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        """Execute an arbitrage trade pair (buy low on one exchange, sell high on another)."""
        try:
            import ccxt.async_support as ccxt

            results = {}
            for ex_name in [opportunity["buy_on"], opportunity["sell_on"]]:
                exchange_class = getattr(ccxt, ex_name)
                ex = exchange_class(
                    {
                        "enableRateLimit": True,
                        "apiKey": self._config.get(f"{ex_name}_api_key", ""),
                        "secret": self._config.get(f"{ex_name}_secret", ""),
                    }
                )
                side = "buy" if ex_name == opportunity["buy_on"] else "sell"
                amount = self._max_position_usd / opportunity["buy_price"]
                order = await ex.create_order(opportunity["symbol"], "market", side, amount)
                results[ex_name] = {
                    "order_id": order.get("id"),
                    "filled": order.get("filled"),
                    "price": order.get("price"),
                }
                await ex.close()
            return {
                "status": "executed",
                "results": results,
                "spread": opportunity["spread_pct"],
                "profit_est": opportunity["estimated_profit_usd"],
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def get_balance(self) -> dict[str, Any]:
        total = 0.0
        details: dict[str, Any] = {}
        try:
            import ccxt.async_support as ccxt

            for ex_name in self._exchanges:
                try:
                    exchange_class = getattr(ccxt, ex_name)
                    ex = exchange_class(
                        {
                            "enableRateLimit": True,
                            "apiKey": self._config.get(f"{ex_name}_api_key", ""),
                            "secret": self._config.get(f"{ex_name}_secret", ""),
                        }
                    )
                    bal = await ex.fetch_balance()
                    usd_value = bal.get("total", {}).get("USD", 0) or bal.get("USDT", {}).get("total", 0)
                    total += usd_value
                    details[ex_name] = usd_value
                    await ex.close()
                except Exception:
                    pass
            return {"total_usd": total, "details": details}
        except ImportError:
            return {"total_usd": 0, "details": {}}
