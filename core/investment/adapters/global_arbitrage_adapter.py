from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("orion.investment.global_arbitrage")


def walk_book_for_size(levels: list[list[float]], size_usd: float) -> tuple[float, float] | None:
    """Average fill price for ``size_usd`` walking ``levels`` deepest-last.

    ``levels`` is a ccxt-style book side: ``[[price, amount_base], ...]`` already
    sorted best price first. Returns ``(vwap, filled_usd)``, or ``None`` when the
    visible depth cannot absorb the size — a partial fill is not a measurement of
    the slippage this order would suffer, so it is reported as unmeasurable
    rather than extrapolated.
    """
    remaining = size_usd
    spent = 0.0
    base = 0.0
    for level in levels:
        if remaining <= 0:
            break
        try:
            price, amount = float(level[0]), float(level[1])
        except (TypeError, ValueError, IndexError):
            return None
        if price <= 0 or amount <= 0:
            continue
        level_usd = price * amount
        take = min(level_usd, remaining)
        spent += take
        base += take / price
        remaining -= take
    if remaining > 0 or base <= 0 or spent <= 0:
        return None
    return spent / base, spent


def residual_spread_pct(buy_fill_price: float, sell_fill_price: float) -> float:
    """Spread that still exists once both legs have actually filled.

    This is the only gross figure worth accounting for: it is measured from the
    two vwaps, so it already contains the depth cost of each book and whatever
    the second leg moved while the first one was filling. The spread quoted at
    scan time is a claim; this is what the position captured.
    """
    if buy_fill_price <= 0 or sell_fill_price <= 0:
        raise ValueError("fill prices must be positive to measure the residual spread")
    return (sell_fill_price - buy_fill_price) / buy_fill_price * 100.0


def quote_drift_pct(side: str, scan_price: float, touch_after: float) -> float:
    """How far a leg's touch moved against us between scan and fill, in %.

    Execution risk lives here: the buy leg ends up paying above the ask it was
    scanned at, the sell leg ends up receiving below the bid it was scanned at.
    Positive always means adverse; a negative value means the market moved in
    our favour and is reported as such instead of being hidden at zero.
    """
    if side not in ("buy", "sell"):
        raise ValueError(f"unknown leg side: {side!r}")
    if scan_price <= 0 or touch_after <= 0:
        raise ValueError("scan price and touch must be positive to measure drift")
    if side == "buy":
        return (touch_after - scan_price) / scan_price * 100.0
    return (scan_price - touch_after) / scan_price * 100.0


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
                if self._min_quote_volume_usd and sum(tickers[ex][symbol]["qv"] for ex in tickers if symbol in tickers[ex]) < self._min_quote_volume_usd:
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

    async def _walk_leg(
        self,
        ccxt_module: Any,
        exchange_name: str,
        symbol: str,
        side: str,
        deploy_usd: float,
    ) -> dict[str, Any]:
        """Fill price of one leg on its live book, plus that book's touch.

        Returns a dict carrying ``reason`` instead of raising when the book is
        unreachable or too thin: the caller reports it as unmeasurable rather
        than turning a missing book into a zero-cost assumption.
        """
        try:
            exchange_class = getattr(ccxt_module, exchange_name)
            ex = exchange_class({"enableRateLimit": True})
            try:
                book = await ex.fetch_order_book(symbol, limit=50)
            finally:
                await ex.close()
        except Exception as exc:
            return {"reason": f"book_unavailable:{exchange_name}", "error": str(exc)}
        levels = (book.get("asks") if side == "buy" else book.get("bids")) or []
        walked = walk_book_for_size(levels, deploy_usd)
        if walked is None:
            return {"reason": f"insufficient_depth:{exchange_name}"}
        vwap, filled = walked
        touch: float | None = None
        for level in levels:
            try:
                candidate = float(level[0])
            except (TypeError, ValueError, IndexError):
                continue
            if candidate > 0:
                touch = candidate
                break
        if touch is None:
            return {"reason": f"no_touch_price:{exchange_name}"}
        # Adverse move inside this book: paying above the touch / receiving below
        adverse_pct = (vwap - touch) / touch * 100.0 if side == "buy" else (touch - vwap) / touch * 100.0
        return {
            "exchange": exchange_name,
            "vwap": vwap,
            "touch": touch,
            "filled_usd": filled,
            "adverse_pct": adverse_pct,
        }

    async def measure_slippage(self, opportunity: dict[str, Any], deploy_usd: float) -> dict[str, Any]:
        """Execution cost of ``deploy_usd`` measured on both live books, in fill order.

        The two legs do not fill at the same instant: the buy leg is lifted first
        and the sell leg only exits afterwards, into whatever its book looks like
        at that later moment. So the spread quoted at scan time is not the spread
        captured, and pricing the trade off it would overstate the edge.

        Consequently this measures:

        * ``residual_spread_pct`` — spread surviving both fills, computed from the
          two vwaps. It is the authoritative gross: it already contains depth
          cost and any drift of the second leg.
        * ``depth_slippage_pct`` — adverse fill inside each book against its own
          touch (how thin the books are).
        * ``drift_pct`` — how far each touch moved against us between the scan
          quote and the fill, i.e. the risk the first leg fills and the second
          one no longer offers the price. ``leg_gap_seconds`` is the real elapsed
          time between the two fills that this drift was measured across.

        The split is diagnostic; only ``residual_spread_pct`` should be booked as
        gross. Returns ``measured: False`` when ccxt is missing or a book cannot
        be priced — callers must then treat the net P&L as PARTIAL instead of
        complete.

        ``leg_unhedged`` separates two very different failures behind that same
        ``measured: False``. The legs are priced in fill order, so a failure on
        the BUY leg means nothing was ever bought: there is no position and no
        cost to report. A failure on the SELL leg is the opposite — the buy leg
        already has a fill price, so a real execution would be long with no exit
        into the visible depth. That trade has no realized P&L at all (the
        position is still open, at market risk), which is a different fact from
        a cost that could not be measured, and the two must not be recorded as
        the same thing.
        """
        if deploy_usd <= 0:
            return {"measured": False, "leg_unhedged": False, "reason": "no_deploy_size"}
        try:
            import ccxt.async_support as ccxt
        except ImportError:
            return {"measured": False, "leg_unhedged": False, "reason": "ccxt_not_installed"}

        symbol = opportunity["symbol"]
        buy = await self._walk_leg(ccxt, opportunity["buy_on"], symbol, "buy", deploy_usd)
        if "reason" in buy:
            # Nothing filled: no position, so nothing is exposed.
            return {"measured": False, "leg_unhedged": False, **buy}

        # Leg 1 is now priced (filled): from here on, the clock is the exposure
        # window in which the second leg has to still be there.
        filled_at = time.monotonic()
        sell = await self._walk_leg(ccxt, opportunity["sell_on"], symbol, "sell", deploy_usd)
        gap_seconds = time.monotonic() - filled_at
        if "reason" in sell:
            # Leg 1 has a fill price and leg 2 has nowhere to go: a real
            # execution would be holding the bought size unhedged. Report the
            # exposure instead of a measurement failure.
            return {
                "measured": False,
                "leg_unhedged": True,
                "unhedged_value_usd": buy["filled_usd"],
                "buy_fill_price": buy["vwap"],
                "buy_touch_price": buy["touch"],
                "leg_gap_seconds": round(gap_seconds, 4),
                **sell,
            }

        try:
            residual = residual_spread_pct(buy["vwap"], sell["vwap"])
            buy_drift = quote_drift_pct("buy", float(opportunity["buy_price"]), buy["touch"])
            sell_drift = quote_drift_pct("sell", float(opportunity["sell_price"]), sell["touch"])
        except (TypeError, ValueError, KeyError) as exc:
            # Both legs priced: the pair could have been closed, so the failure
            # is in the arithmetic, not in the exposure.
            return {"measured": False, "leg_unhedged": False, "reason": "unusable_quotes", "error": str(exc)}

        depth_pct = buy["adverse_pct"] + sell["adverse_pct"]
        return {
            "measured": True,
            "leg_unhedged": False,
            "residual_spread_pct": round(residual, 6),
            "depth_slippage_pct": round(depth_pct, 6),
            "drift_pct": round(buy_drift + sell_drift, 6),
            "buy_slippage_pct": round(buy["adverse_pct"], 6),
            "sell_slippage_pct": round(sell["adverse_pct"], 6),
            "buy_drift_pct": round(buy_drift, 6),
            "sell_drift_pct": round(sell_drift, 6),
            "buy_fill_price": buy["vwap"],
            "sell_fill_price": sell["vwap"],
            "buy_touch_price": buy["touch"],
            "sell_touch_after": sell["touch"],
            "leg_gap_seconds": round(gap_seconds, 4),
        }

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


def build_global_arbitrage_adapter(config: dict[str, Any] | None = None) -> GlobalArbitrageAdapter:
    """Factory function to create Global Arbitrage adapter."""
    return GlobalArbitrageAdapter(config)
