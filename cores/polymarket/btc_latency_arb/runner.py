"""Main Runner for Polymarket BTC Latency Arbitrage."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass
from typing import Any

from core.polymarket.btc_latency_arb.config import BTCArbConfig
from core.polymarket.btc_latency_arb.data import fetch_chainlink_btc_usd, fetch_polymarket_snapshot
from core.polymarket.btc_latency_arb.engines import (
    Decision,
    EdgeResult,
    ScoredDirection,
    apply_time_awareness,
    compute_edge,
    decide,
    detect_regime,
    score_direction,
)
from core.polymarket.btc_latency_arb.feeds import BinanceWSFeed, PolymarketWSFeed
from core.polymarket.btc_latency_arb.indicators import (
    compute_heiken_ashi,
    compute_macd,
    compute_rsi,
    compute_rsi_series,
    compute_session_vwap,
    compute_vwap_distance,
    compute_vwap_series,
    compute_vwap_slope,
    count_consecutive,
    count_vwap_crosses,
    slope_last,
    sma,
)
from core.polymarket.btc_latency_arb.paper_engine import PaperTradingEngine
from core.polymarket.btc_latency_arb.persistence import TradeHistory

logger = logging.getLogger("orion.polymarket.btc_latency_arb.runner")


@dataclass(slots=True)
class MarketData:
    """Aggregated market data for decision making."""

    # Binance data
    binance_price: float | None = None
    binance_last_update: int = 0

    # Polymarket data
    polymarket_up: float | None = None
    polymarket_down: float | None = None
    polymarket_last_update: int = 0

    # Chainlink (fallback)
    chainlink_price: float | None = None
    chainlink_last_update: int = 0

    # Derived
    vwap: float | None = None
    vwap_series: list[float] = None
    vwap_slope: float | None = None
    vwap_distance: float | None = None
    vwap_cross_count: int | None = None

    rsi: float | None = None
    rsi_series: list[float] = None
    rsi_slope: float | None = None
    rsi_ma: float | None = None

    macd: dict[str, float] | None = None

    ha_candles: list[dict] = None
    ha_color: str | None = None
    ha_count: int = 0

    failed_vwap_reclaim: bool = False

    volume_recent: float | None = None
    volume_avg: float | None = None

    regime: str = "CHOP"
    regime_reason: str = "init"

    # Time
    settlement_ms: int | None = None
    time_left_min: float | None = None

    # Candles for indicators
    closes_1m: list[float] = None
    candles_1m: list[dict] = None
    candles_5m: list[dict] = None


class BTCArbRunner:
    """Main runner for BTC latency arbitrage bot."""

    def __init__(self, config: BTCArbConfig) -> None:
        self.config = config
        self._running = False
        self._tasks: list[asyncio.Task] = []

        # Feeds
        self._binance_feed = BinanceWSFeed(
            ws_url=config.feeds.binance_ws_url,
            symbol=config.feeds.symbol.lower(),
        )
        self._polymarket_feed = PolymarketWSFeed(
            ws_url=config.feeds.polymarket_ws_url,
            market_id=config.feeds.market_id,
        )

        # Paper trading
        self._paper_engine = PaperTradingEngine(config.paper)

        # Persistence
        self._trade_history = TradeHistory(config)

        # Market data state
        self._market_data = MarketData(
            vwap_series=[],
            rsi_series=[],
            ha_candles=[],
            closes_1m=[],
            candles_1m=[],
            candles_5m=[],
        )

        # Callbacks
        self._setup_feed_callbacks()

        # Statistics
        self._stats = {
            "cycles": 0,
            "signals": 0,
            "trades": 0,
            "errors": 0,
            "start_time": time.time(),
        }

    def _setup_feed_callbacks(self) -> None:
        """Setup feed event callbacks."""

        # Binance tick callback
        def on_binance_tick(tick: Any) -> None:
            self._market_data.binance_price = tick.price
            self._market_data.binance_last_update = tick.timestamp

        # Binance kline callback
        def on_binance_kline(kline: Any) -> None:
            if kline.is_closed:
                self._update_candles(kline)

        # Polymarket orderbook callback
        def on_polymarket_orderbook(ob: Any) -> None:
            self._market_data.polymarket_last_update = ob.timestamp
            bid, ask = self._polymarket_feed.get_best_bid_ask()
            if bid is not None:
                self._market_data.polymarket_up = bid  # Approximation
            if ask is not None:
                self._market_data.polymarket_down = ask  # Approximation

        self._binance_feed.on_tick(on_binance_tick)
        self._binance_feed.on_kline(on_binance_kline)
        self._polymarket_feed.on_orderbook(on_polymarket_orderbook)

    def _update_candles(self, kline: Any) -> None:
        """Update candle data from closed kline."""
        candle = {
            "open": kline.open_price,
            "high": kline.high_price,
            "low": kline.low_price,
            "close": kline.close_price,
            "volume": kline.volume,
            "timestamp": kline.start_time,
        }

        self._market_data.candles_1m.append(candle)
        self._market_data.closes_1m.append(kline.close_price)

        # Keep last 240 candles (4 hours)
        if len(self._market_data.candles_1m) > 240:
            self._market_data.candles_1m = self._market_data.candles_1m[-240:]
            self._market_data.closes_1m = self._market_data.closes_1m[-240:]

    async def start(self) -> None:
        """Start the runner."""
        if self._running:
            logger.warning("Runner already running")
            return

        self._running = True
        logger.info("Starting BTC Latency Arb Runner...")

        # Connect feeds
        binance_ok = await self._binance_feed.connect()
        if not binance_ok:
            logger.error("Failed to connect Binance feed")
            self._running = False
            return

        polymarket_ok = await self._polymarket_feed.connect()
        if not polymarket_ok:
            logger.warning("Polymarket feed connection failed (will retry)")

        # Start main loop
        task = asyncio.create_task(self._main_loop())
        self._tasks.append(task)

        # Start periodic market snapshot fetch
        snapshot_task = asyncio.create_task(self._snapshot_loop())
        self._tasks.append(snapshot_task)

        # Start Chainlink fallback fetch
        chainlink_task = asyncio.create_task(self._chainlink_loop())
        self._tasks.append(chainlink_task)

        # Start position monitoring
        monitor_task = asyncio.create_task(self._position_monitor_loop())
        self._tasks.append(monitor_task)

        logger.info("BTC Latency Arb Runner started")

    async def stop(self) -> None:
        """Stop the runner."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping BTC Latency Arb Runner...")

        for task in self._tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()

        await self._binance_feed.disconnect()
        await self._polymarket_feed.disconnect()

        # Save trade history
        self._trade_history.save()

        logger.info("BTC Latency Arb Runner stopped")

    async def _main_loop(self) -> None:
        """Main detection and execution loop."""
        interval = self.config.strategy.check_interval_ms / 1000.0

        while self._running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.exception("Main loop error: %s", e)
                self._stats["errors"] += 1

            await asyncio.sleep(interval)

    async def _run_cycle(self) -> None:
        """Single detection/execution cycle."""
        self._stats["cycles"] += 1

        # Skip if not enough data
        if len(self._market_data.closes_1m) < 50:
            return

        # 1. Update indicators
        self._update_indicators()

        # 2. Check if we have Polymarket prices
        if self._market_data.polymarket_up is None or self._market_data.polymarket_down is None:
            # Try to get from feed orderbook
            ob = self._polymarket_feed.get_last_orderbook()
            if ob:
                bids = [b[0] for b in ob.bids]
                asks = [a[0] for a in ob.asks]
                if bids and asks:
                    self._market_data.polymarket_up = max(bids)
                    self._market_data.polymarket_down = min(asks)

        if self._market_data.polymarket_up is None or self._market_data.polymarket_down is None:
            return  # Wait for market data

        # 3. Compute time to settlement
        if self._market_data.settlement_ms:
            self._market_data.time_left_min = max(0, (self._market_data.settlement_ms - time.time() * 1000) / 60000)

        # 4. Score direction
        scored = self._score_direction()
        if not scored:
            return

        # 4. Apply time awareness
        time_aware = apply_time_awareness(
            scored.raw_up,
            self._market_data.time_left_min,
            self.config.strategy.min_seconds_left // 60,  # window in minutes
        )

        # 5. Compute edge
        edge = compute_edge(
            model_up=time_aware["adjusted_up"],
            model_down=time_aware["adjusted_down"],
            market_yes=self._market_data.polymarket_up,
            market_no=self._market_data.polymarket_down,
        )

        if edge.edge_up is None or edge.edge_down is None:
            return

        # 6. Make decision
        decision = decide(
            remaining_minutes=self._market_data.time_left_min or 15,
            edge_up=edge.edge_up,
            edge_down=edge.edge_down,
            model_up=time_aware["adjusted_up"],
            model_down=time_aware["adjusted_down"],
        )

        # 7. Execute if signal
        if decision.action == "ENTER":
            await self._execute_trade(decision, edge)

        # Log periodic status
        if self._stats["cycles"] % 100 == 0:
            self._log_status(scored, time_aware, edge, decision)

    def _update_indicators(self) -> None:
        """Update all technical indicators."""
        closes = self._market_data.closes_1m
        candles = self._market_data.candles_1m

        if not closes or len(closes) < 20:
            return

        # VWAP
        self._market_data.vwap = compute_session_vwap(candles)
        self._market_data.vwap_series = compute_vwap_series(candles)
        self._market_data.vwap_slope = compute_vwap_slope(self._market_data.vwap_series, 5)
        self._market_data.vwap_distance = compute_vwap_distance(
            self._market_data.binance_price or closes[-1], self._market_data.vwap or 0
        )
        self._market_data.vwap_cross_count = count_vwap_crosses(closes, self._market_data.vwap_series, 20)

        # RSI
        self._market_data.rsi = compute_rsi(closes, 14)
        self._market_data.rsi_series = compute_rsi_series(closes, 14)
        self._market_data.rsi_slope = slope_last(self._market_data.rsi_series, 3)
        self._market_data.rsi_ma = sma(self._market_data.rsi_series, 14)

        # MACD
        self._market_data.macd = compute_macd(closes, 12, 26, 9)

        # Heiken Ashi
        self._market_data.ha_candles = compute_heiken_ashi(candles)
        ha_info = count_consecutive(self._market_data.ha_candles)
        self._market_data.ha_color = ha_info["color"]
        self._market_data.ha_count = ha_info["count"]

        # Failed VWAP reclaim
        if self._market_data.vwap is not None and len(self._market_data.vwap_series) >= 3:
            vwap_now = self._market_data.vwap_series[-1]
            vwap_prev = self._market_data.vwap_series[-2]
            close_now = closes[-1]
            close_prev = closes[-2]
            self._market_data.failed_vwap_reclaim = close_now < vwap_now and close_prev > vwap_prev

        # Volume
        if len(candles) >= 20:
            self._market_data.volume_recent = sum(c["volume"] for c in candles[-20:])
        if len(candles) >= 120:
            self._market_data.volume_avg = sum(c["volume"] for c in candles[-120:]) / 6

        # Regime
        regime_info = detect_regime(
            price=self._market_data.binance_price or closes[-1],
            vwap=self._market_data.vwap,
            vwap_slope=self._market_data.vwap_slope,
            vwap_cross_count=self._market_data.vwap_cross_count,
            volume_recent=self._market_data.volume_recent,
            volume_avg=self._market_data.volume_avg,
        )
        self._market_data.regime = regime_info.regime
        self._market_data.regime_reason = regime_info.reason

    def _score_direction(self) -> ScoredDirection | None:
        """Score UP vs DOWN direction."""
        if self._market_data.rsi is None:
            return None

        return score_direction(
            {
                "price": self._market_data.binance_price or self._market_data.closes_1m[-1],
                "vwap": self._market_data.vwap,
                "vwap_slope": self._market_data.vwap_slope,
                "rsi": self._market_data.rsi,
                "rsi_slope": self._market_data.rsi_slope,
                "macd": self._market_data.macd,
                "heiken_color": self._market_data.ha_color,
                "heiken_count": self._market_data.ha_count,
                "failed_vwap_reclaim": self._market_data.failed_vwap_reclaim,
            }
        )

    async def _execute_trade(self, decision: Decision, edge: EdgeResult) -> None:
        """Execute paper trade based on decision."""
        self._stats["signals"] += 1

        # Determine size using position sizer (simplified for now)
        size_usd = min(
            self.config.strategy.max_position_usd,
            self.config.paper.initial_usd * 0.02,  # 2% default
        )

        # Check risk
        can_trade, reason = self._paper_engine.can_trade(size_usd)
        if not can_trade:
            logger.debug("Trade blocked: %s", reason)
            return

        # Determine market price and outcome
        if decision.side == "UP":
            market_price = self._market_data.polymarket_up
            outcome = "Yes"
        else:
            market_price = self._market_data.polymarket_down
            outcome = "No"

        if market_price is None or market_price <= 0:
            logger.warning("Invalid market price for %s: %s", decision.side, market_price)
            return

        # Get current market ID
        market_id = self.config.feeds.market_id or "auto"

        # Execute paper buy
        success, reason, position = self._paper_engine.execute_paper_buy(
            market_id=market_id,
            outcome=outcome,
            side=decision.side,
            market_price=market_price,
            size_usd=size_usd,
        )

        if success:
            self._stats["trades"] += 1
            self._trade_history.add_trade(
                {
                    "type": "entry",
                    "position_id": position.id,
                    "side": decision.side,
                    "outcome": outcome,
                    "entry_price": position.entry_price,
                    "size_usd": size_usd,
                    "market_price": market_price,
                    "decision": decision.__dict__,
                    "edge": edge.__dict__,
                    "market_data": {
                        "binance_price": self._market_data.binance_price,
                        "polymarket_up": self._market_data.polymarket_up,
                        "polymarket_down": self._market_data.polymarket_down,
                        "regime": self._market_data.regime,
                        "time_left_min": self._market_data.time_left_min,
                    },
                    "timestamp": int(time.time() * 1000),
                }
            )

    async def _snapshot_loop(self) -> None:
        """Periodic market snapshot fetch."""
        while self._running:
            try:
                await asyncio.sleep(10)  # Every 10 seconds
                snapshot = await fetch_polymarket_snapshot(self.config)

                if snapshot.get("ok"):
                    prices = snapshot.get("prices", {})
                    if prices.get("up") is not None:
                        self._market_data.polymarket_up = prices["up"]
                    if prices.get("down") is not None:
                        self._market_data.polymarket_down = prices["down"]

                    market = snapshot.get("market", {})
                    if market.get("endDate"):
                        from datetime import datetime

                        end_dt = datetime.fromisoformat(market["endDate"].replace("Z", "+00:00"))
                        self._market_data.settlement_ms = int(end_dt.timestamp() * 1000)

                    # Update market ID for feed
                    if market.get("id") and market["id"] != self._polymarket_feed._market_id:
                        self._polymarket_feed._market_id = market["id"]
                        await self._polymarket_feed.subscribe_orderbook(market["id"])

            except Exception as e:
                logger.warning("Snapshot loop error: %s", e)

    async def _chainlink_loop(self) -> None:
        """Periodic Chainlink price fetch (fallback)."""
        while self._running:
            try:
                await asyncio.sleep(5)  # Every 5 seconds
                result = await fetch_chainlink_btc_usd(self.config)
                if result.get("price") is not None:
                    self._market_data.chainlink_price = result["price"]
                    self._market_data.chainlink_last_update = result.get("updated_at", 0)

                    # Use as Binance price if Binance not available
                    if self._market_data.binance_price is None:
                        self._market_data.binance_price = result["price"]
            except Exception as e:
                logger.warning("Chainlink loop error: %s", e)

    async def _position_monitor_loop(self) -> None:
        """Monitor open positions for exit conditions."""
        while self._running:
            try:
                await asyncio.sleep(2)  # Check every 2 seconds

                for position in self._paper_engine.open_positions:
                    # Get current market price for this position
                    if position.outcome.lower() in ("yes", "up"):
                        current_price = self._market_data.polymarket_up
                    else:
                        current_price = self._market_data.polymarket_down

                    if current_price is None:
                        continue

                    # Check stop loss (10%)
                    if self._paper_engine.check_stop_loss(position, current_price, 0.10):
                        success, reason, trade = self._paper_engine.execute_paper_sell(position.id, current_price)
                        if success and trade:
                            self._trade_history.add_trade(
                                {
                                    "type": "exit",
                                    "trade": trade.__dict__,
                                    "reason": "stop_loss",
                                    "timestamp": int(time.time() * 1000),
                                }
                            )
                            logger.info("Stop loss triggered for %s", position.id)

                    # Check time-based exit (near settlement)
                    if self._market_data.time_left_min is not None and self._market_data.time_left_min < 1.0:  # Less than 1 min
                        success, reason, trade = self._paper_engine.execute_paper_sell(position.id, current_price)
                        if success and trade:
                            self._trade_history.add_trade(
                                {
                                    "type": "exit",
                                    "trade": trade.__dict__,
                                    "reason": "time_exit",
                                    "timestamp": int(time.time() * 1000),
                                }
                            )
                            logger.info("Time exit for %s", position.id)

            except Exception as e:
                logger.warning("Position monitor error: %s", e)

    def _log_status(self, scored: ScoredDirection, time_aware: dict, edge: EdgeResult, decision: Decision) -> None:
        """Log periodic status."""
        logger.info(
            "Cycle %d | Regime: %s | RawUP: %.3f | AdjUP: %.3f | Edge: UP=%.3f DOWN=%.3f | Decision: %s %s (%s) | Time: %.1fmin | Trades: %d",
            self._stats["cycles"],
            self._market_data.regime,
            scored.raw_up,
            time_aware["adjusted_up"],
            edge.edge_up or 0,
            edge.edge_down or 0,
            decision.action,
            decision.side or "-",
            decision.strength or "-",
            self._market_data.time_left_min or 0,
            self._stats["trades"],
        )

    def get_status(self) -> dict[str, Any]:
        """Get runner status for API."""
        return {
            "running": self._running,
            "stats": self._stats,
            "market_data": {
                "binance_price": self._market_data.binance_price,
                "polymarket_up": self._market_data.polymarket_up,
                "polymarket_down": self._market_data.polymarket_down,
                "chainlink_price": self._market_data.chainlink_price,
                "regime": self._market_data.regime,
                "time_left_min": self._market_data.time_left_min,
                "vwap": self._market_data.vwap,
                "rsi": self._market_data.rsi,
                "macd": self._market_data.macd,
            },
            "paper_engine": self._paper_engine.get_performance(),
            "open_positions": len(self._paper_engine.open_positions),
            "feeds": {
                "binance": self._binance_feed.get_stats(),
                "polymarket": self._polymarket_feed.get_stats(),
            },
        }

    async def run_single_cycle(self) -> dict[str, Any]:
        """Run a single cycle (for scheduler integration)."""
        await self._run_cycle()
        return self.get_status()


async def run_continuous(config: BTCArbConfig | None = None) -> None:
    """Run the bot continuously (entry point for scheduler)."""
    if config is None:
        config = BTCArbConfig()

    runner = BTCArbRunner(config)
    await runner.start()

    try:
        # Keep running until cancelled
        while runner._running:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.stop()
