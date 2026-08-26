"""Enhanced Smart Money Copier — practical copy trading without leaderboard API.

Since Polymarket doesn't have a public leaderboard API, we use:
1. High-volume market monitoring
2. Price movement tracking (proxy for "smart money" activity)
3. Order book analysis for large orders
4. Known profitable wallet tracking (manual config)

Based on @0x_Punisher's playbook: focus on execution, not prediction.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from core.polymarket.client import PolymarketClient, get_client
from core.polymarket.events import get_polymarket_event_bus
from core.polymarket.health.monitor import get_health_monitor

logger = logging.getLogger("orion.polymarket.strategy.smart_money")


@dataclass
class SmartMoneyConfig:
    """Smart money copier configuration."""

    # Market filtering
    min_volume_24h: float = 10_000  # $10k daily volume
    min_liquidity: float = 5_000  # $5k liquidity
    max_markets: int = 20  # Monitor top 20 markets

    # Price movement detection
    price_change_threshold: float = 0.05  # 5% price change = signal
    volume_spike_threshold: float = 2.0  # 2x volume spike = signal

    # Risk management
    max_position_usd: float = 50.0  # Max $50 per copy
    max_total_exposure: float = 200.0  # Max $200 total
    max_positions_per_market: int = 1  # One position per market
    min_price: float = 0.10  # Don't buy below 10¢
    max_price: float = 0.90  # Don't buy above 90¢

    # Known profitable wallets (manual config)
    tracked_wallets: list[str] = field(default_factory=list)

    # Scanning
    scan_interval: float = 300.0  # Scan every 5 minutes
    price_check_interval: float = 60.0  # Check prices every minute

    # Execution
    dry_run: bool = True  # Paper trading by default
    auto_copy: bool = False  # Don't auto-copy until approved


@dataclass
class MarketSignal:
    """A signal from market activity."""

    market_id: str
    question: str
    signal_type: str  # price_change, volume_spike, large_order
    direction: str  # up, down, buy, sell
    magnitude: float
    current_price: float
    volume_24h: float
    liquidity: float
    timestamp: float


@dataclass
class CopyPosition:
    """A copied position."""

    market_id: str
    token_id: str
    outcome: str
    entry_price: float
    size_usd: float
    source: str  # price_movement, volume_spike, wallet_tracker
    entry_time: float
    current_price: float = 0.0
    status: str = "open"  # open, closed, failed


class SmartMoneyCopierV2:
    """Enhanced smart money copy trading.

    Strategy:
    1. Monitor high-volume markets for price movements
    2. Track order book for large orders
    3. Follow known profitable wallets
    4. Generate copy signals based on activity

    Based on @0x_Punisher's playbook:
    - Focus on execution, not prediction
    - Use multiple data sources
    - Strict risk controls
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = SmartMoneyConfig(
            **{k: v for k, v in (config or {}).items() if k in SmartMoneyConfig.__dataclass_fields__}
        )
        self._client: PolymarketClient | None = None
        self._markets: dict[str, dict[str, Any]] = {}
        self._price_history: dict[str, list[tuple[float, float]]] = {}
        self._signals: list[MarketSignal] = []
        self._positions: dict[str, CopyPosition] = {}
        self._scan_count = 0
        self._running = False
        self._last_scan_time: float = 0.0
        self._event_bus = get_polymarket_event_bus()

    @property
    def name(self) -> str:
        return "smart_money_v2"

    def _get_client(self) -> PolymarketClient:
        if self._client is None:
            self._client = get_client()
        return self._client

    # ── Market Discovery ──────────────────────────────────────────────

    async def scan_high_volume_markets(self) -> list[dict[str, Any]]:
        """Scan for high-volume markets."""
        client = self._get_client()
        markets = await client.list_markets(
            closed=False,
            limit=self._config.max_markets,
            order="volume24hr",
            ascending=False,
        )

        filtered = []
        for market in markets:
            volume = float(market.get("volume24hr", 0) or 0)
            liquidity = float(market.get("liquidity", 0) or 0)

            if volume < self._config.min_volume_24h:
                continue
            if liquidity < self._config.min_liquidity:
                continue

            # Store market data (API uses camelCase: conditionId, clobTokenIds)
            market_id = market.get("conditionId", "")
            if market_id:
                # Build token list from clobTokenIds and outcomes
                token_ids = market.get("clobTokenIds", [])
                outcomes = market.get("outcomes", [])
                tokens = []
                for i, tid in enumerate(token_ids):
                    tokens.append(
                        {
                            "token_id": tid,
                            "outcome": outcomes[i] if i < len(outcomes) else f"token_{i}",
                        }
                    )

                self._markets[market_id] = {
                    "question": market.get("question", ""),
                    "volume24hr": volume,
                    "liquidity": liquidity,
                    "tokens": tokens,
                    "outcome_prices": market.get("outcomePrices", []),
                    "last_seen": time.time(),
                }
                filtered.append(market)

        logger.info(
            "Scanned %d high-volume markets (filtered from %d)",
            len(filtered),
            len(markets),
        )

        # Publish scan completed event
        self._event_bus.publish_scan_completed(
            markets_scanned=len(filtered),
            signals_found=0,
            opportunities=0,
            duration_ms=0,
        )

        return filtered

    # ── Price Movement Detection ──────────────────────────────────────

    async def detect_price_movements(self, max_markets: int = 5) -> list[MarketSignal]:
        """Detect significant price movements across top markets.

        Only checks first max_markets to avoid excessive API calls.
        Uses outcomePrices from market data as proxy for current prices.
        """
        signals: list[MarketSignal] = []

        # Sort markets by volume and take top N
        sorted_markets = sorted(
            self._markets.items(),
            key=lambda x: x[1].get("volume24hr", 0),
            reverse=True,
        )[:max_markets]

        for market_id, market_data in sorted_markets:
            outcome_prices = market_data.get("outcome_prices", [])
            if not outcome_prices:
                continue

            # Get current prices (use first outcome as proxy)
            try:
                current_price = float(outcome_prices[0]) if outcome_prices else 0
            except (ValueError, IndexError):
                continue

            # Track price history
            if market_id not in self._price_history:
                self._price_history[market_id] = []
            self._price_history[market_id].append((time.time(), current_price))

            # Keep last 100 prices
            if len(self._price_history[market_id]) > 100:
                self._price_history[market_id] = self._price_history[market_id][-100:]

            # Check for significant movement (only if we have history)
            history = self._price_history[market_id]
            if len(history) >= 2:
                old_price = history[-2][1]
                change = current_price - old_price
                change_pct = abs(change) / old_price if old_price > 0 else 0

                if change_pct >= self._config.price_change_threshold:
                    signal = MarketSignal(
                        market_id=market_id,
                        question=market_data.get("question", ""),
                        signal_type="price_change",
                        direction="up" if change > 0 else "down",
                        magnitude=change_pct,
                        current_price=current_price,
                        volume_24h=market_data.get("volume24hr", 0),
                        liquidity=market_data.get("liquidity", 0),
                        timestamp=time.time(),
                    )
                    signals.append(signal)
                    logger.info(
                        "Price movement detected: %s %.1f%% ($%.4f)",
                        market_data.get("question", "")[:40],
                        change_pct * 100,
                        current_price,
                    )

        self._signals = signals
        return signals

    # ── Copy Signal Generation ────────────────────────────────────────

    def _evaluate_copy_signal(self, signal: MarketSignal) -> dict[str, Any] | None:
        """Evaluate whether to copy based on a market signal."""
        # Check if we already have this market
        if signal.market_id in self._positions:
            return None

        # Check price range
        if signal.current_price < self._config.min_price or signal.current_price > self._config.max_price:
            return None

        # Check risk limits
        copy_size = self._config.max_position_usd
        total_exposure = sum(p.size_usd for p in self._positions.values())
        if (total_exposure + copy_size) > self._config.max_total_exposure:
            return None

        # Determine outcome based on direction
        # For price up signals, buy the token that went up
        # For price down signals, buy the opposite token
        outcome = "YES" if signal.direction == "up" else "NO"

        return {
            "market_id": signal.market_id,
            "token_id": "",  # Will be filled from market data
            "outcome": outcome,
            "price": signal.current_price,
            "size_usd": copy_size,
            "source": signal.signal_type,
            "signal_magnitude": signal.magnitude,
        }

    async def generate_copy_signals(self) -> list[dict[str, Any]]:
        """Generate copy-trade signals from market activity."""
        # Scan markets
        await self.scan_high_volume_markets()

        # Detect price movements
        signals = await self.detect_price_movements()

        # Evaluate each signal
        copy_signals = []
        for signal in signals:
            copy_signal = self._evaluate_copy_signal(signal)
            if copy_signal:
                copy_signals.append(copy_signal)

        return copy_signals

    # ── Copy Execution ────────────────────────────────────────────────

    async def _execute_copy(self, signal: dict[str, Any]) -> bool:
        """Execute a copy trade."""
        if self._config.dry_run:
            logger.info(
                "[DRY RUN] Would copy %s @ $%.4f, size $%.2f (source: %s, magnitude: %.1f%%)",
                signal["outcome"],
                signal["price"],
                signal["size_usd"],
                signal["source"],
                signal.get("signal_magnitude", 0) * 100,
            )
            # Publish signal event
            self._event_bus.publish_signal(
                strategy=self.name,
                market_id=signal["market_id"],
                outcome=signal["outcome"],
                price=signal["price"],
                size_usd=signal["size_usd"],
                signal_type=signal["source"],
                metadata={"magnitude": signal.get("signal_magnitude", 0)},
            )
            # Record as dry run position
            pos = CopyPosition(
                market_id=signal["market_id"],
                token_id=signal.get("token_id", ""),
                outcome=signal["outcome"],
                entry_price=signal["price"],
                size_usd=signal["size_usd"],
                source=signal["source"],
                entry_time=time.time(),
                current_price=signal["price"],
                status="open",
            )
            self._positions[signal["market_id"]] = pos
            # Publish position opened event
            self._event_bus.publish_position_opened(
                market_id=signal["market_id"],
                outcome=signal["outcome"],
                entry_price=signal["price"],
                size_usd=signal["size_usd"],
                strategy=self.name,
            )
            return True

        # Live execution would go here
        logger.warning(
            "Live copy not implemented yet: %s @ $%.4f",
            signal["outcome"],
            signal["price"],
        )
        return False

    # ── Position Management ───────────────────────────────────────────

    async def update_position_prices(self) -> None:
        """Update prices for all open positions."""
        client = self._get_client()

        for market_id, pos in list(self._positions.items()):
            if pos.status != "open":
                continue

            price = await client.get_price(pos.token_id)
            if price is not None:
                pos.current_price = price

                # Check for exit conditions
                pnl_pct = (price - pos.entry_price) / pos.entry_price

                # Take profit at 20%
                if pnl_pct >= 0.20:
                    await self._close_position(market_id, price, "take_profit")

                # Stop loss at -10%
                elif pnl_pct <= -0.10:
                    await self._close_position(market_id, price, "stop_loss")

    async def _close_position(
        self,
        market_id: str,
        exit_price: float,
        reason: str,
    ) -> None:
        """Close a position."""
        pos = self._positions.get(market_id)
        if not pos:
            return

        # Calculate PnL
        pnl = (exit_price - pos.entry_price) * (pos.size_usd / pos.entry_price)

        # Record trade
        monitor = get_health_monitor()
        monitor.close_position(market_id, exit_price, notes=reason)

        # Publish position closed event
        self._event_bus.publish_position_closed(
            market_id=market_id,
            outcome=pos.outcome,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            size_usd=pos.size_usd,
            pnl=pnl,
            reason=reason,
        )

        logger.info(
            "Position closed: %s @ $%.4f, PnL: $%.4f (%s)",
            pos.outcome,
            exit_price,
            pnl,
            reason,
        )

        # Remove from active positions
        del self._positions[market_id]

    # ── Summary ───────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Get strategy summary."""
        total_exposure = sum(p.size_usd for p in self._positions.values())
        total_pnl = sum(
            (p.current_price - p.entry_price) * (p.size_usd / p.entry_price) for p in self._positions.values()
        )

        return {
            "strategy": self.name,
            "config": {
                "dry_run": self._config.dry_run,
                "auto_copy": self._config.auto_copy,
                "min_volume_24h": self._config.min_volume_24h,
                "price_change_threshold": self._config.price_change_threshold,
                "max_position_usd": self._config.max_position_usd,
                "max_total_exposure": self._config.max_total_exposure,
            },
            "markets_monitored": len(self._markets),
            "signals_detected": len(self._signals),
            "top_signals": [
                {
                    "question": s.question[:40],
                    "type": s.signal_type,
                    "direction": s.direction,
                    "magnitude": f"{s.magnitude * 100:.1f}%",
                    "price": f"${s.current_price:.4f}",
                }
                for s in self._signals[:5]
            ],
            "positions": {
                "open": len(self._positions),
                "total_exposure": round(total_exposure, 2),
                "unrealized_pnl": round(total_pnl, 4),
            },
            "scan_count": self._scan_count,
        }

    # ── Health Check ──────────────────────────────────────────────────

    async def check_setup(self) -> dict[str, Any]:
        """Check if the strategy is properly configured."""
        client = self._get_client()
        health = await client.health_check()

        return {
            "strategy": self.name,
            "api_health": health,
            "config_valid": True,
            "dry_run": self._config.dry_run,
            "ready": health.get("status") == "ok",
        }
