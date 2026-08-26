"""Paper Trading Engine for Polymarket BTC Latency Arb."""

from __future__ import annotations

import logging
import random
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.polymarket.btc_latency_arb.config import PaperTradingConfig

from core.trading.virtual_wallet import VirtualWallet

logger = logging.getLogger("orion.polymarket.btc_latency_arb.paper_engine")


@dataclass(slots=True)
class PaperPosition:
    """Paper trading position."""

    id: str
    side: str  # "UP" or "DOWN"
    outcome: str  # "Yes" or "No"
    entry_price: float  # Price paid (0-1)
    size_usd: float
    shares: float
    timestamp: int
    market_id: str


@dataclass(slots=True)
class PaperTrade:
    """Completed paper trade."""

    id: str
    position_id: str
    side: str
    outcome: str
    entry_price: float
    exit_price: float
    size_usd: float
    shares: float
    pnl_usd: float
    pnl_pct: float
    fees_usd: float
    slippage_usd: float
    latency_ms: int
    timestamp: int
    market_id: str


class PaperTradingEngine:
    """Realistic paper trading simulation engine."""

    def __init__(
        self,
        config: PaperTradingConfig,
        virtual_wallet: VirtualWallet | None = None,
    ) -> None:
        self.config = config
        self.wallet = virtual_wallet or VirtualWallet(initial_balances={"USDC": Decimal(str(config.initial_usd))})
        self._positions: dict[str, PaperPosition] = {}
        self._trades: list[PaperTrade] = []
        self._last_trade_time = 0.0
        self._daily_pnl = 0.0
        self._day_start = time.time()

    @property
    def open_positions(self) -> list[PaperPosition]:
        return list(self._positions.values())

    @property
    def trades(self) -> list[PaperTrade]:
        return list(self._trades)

    @property
    def daily_pnl(self) -> float:
        # Reset daily PnL if new day
        now = time.time()
        if now - self._day_start > 86400:
            self._daily_pnl = 0.0
            self._day_start = now
        return self._daily_pnl

    def can_trade(self, size_usd: float) -> tuple[bool, str]:
        """Check if trade is allowed."""
        # Check cooldown
        if time.time() - self._last_trade_time < self.config.cooldown_seconds:
            return False, f"Cooldown active ({self.config.cooldown_seconds}s)"

        # Check max concurrent positions
        if len(self._positions) >= self.config.max_concurrent_positions:
            return False, f"Max positions ({self.config.max_concurrent_positions}) reached"

        # Check daily loss limit
        if self.daily_pnl <= -self.config.max_daily_loss_usd:
            return False, f"Daily loss limit reached: ${self.daily_pnl:.2f}"

        # Check wallet balance
        usdc_balance = self.wallet.get_balance("USDC")
        if usdc_balance.free < Decimal(str(size_usd)):
            return False, f"Insufficient balance: ${usdc_balance.free:.2f}"

        # Check min order size
        if size_usd < self.config.min_order_usd:
            return False, f"Order size ${size_usd:.2f} below minimum ${self.config.min_order_usd}"

        return True, "OK"

    def execute_paper_buy(
        self,
        market_id: str,
        outcome: str,
        side: str,  # "UP" or "DOWN"
        market_price: float,  # Current market price (0-1)
        size_usd: float,
    ) -> tuple[bool, str, PaperPosition | None]:
        """Execute a paper buy order with realistic simulation."""
        can, reason = self.can_trade(size_usd)
        if not can:
            return False, reason, None

        # Apply slippage
        slippage_pct = random.uniform(0, self.config.slippage_bps / 10000.0)
        # Random direction for slippage (slightly worse for buyer)
        slippage_direction = 1 if random.random() > 0.3 else -1
        entry_price = market_price * (1 + slippage_direction * slippage_pct)
        entry_price = max(0.001, min(0.999, entry_price))

        # Calculate shares
        shares = size_usd / entry_price if entry_price > 0 else 0

        # Apply fee
        fee_pct = self.config.fee_bps / 10000.0
        fee_usd = size_usd * fee_pct
        slippage_usd = size_usd * slippage_pct * slippage_direction

        # Total cost
        total_cost = size_usd + fee_usd

        # Simulate fill latency
        latency_ms = random.randint(self.config.fill_latency_ms_min, self.config.fill_latency_ms_max)

        # Reserve funds
        try:
            self.wallet.reserve("USDC", Decimal(str(total_cost)), "paper_buy", "")
        except Exception as e:
            return False, f"Wallet reserve failed: {e}", None

        # Create position
        position_id = uuid.uuid4().hex[:12]
        position = PaperPosition(
            id=position_id,
            side=side,
            outcome=outcome,
            entry_price=entry_price,
            size_usd=size_usd,
            shares=shares,
            timestamp=int(time.time() * 1000),
            market_id=market_id,
        )

        self._positions[position_id] = position
        self._last_trade_time = time.time()

        logger.info(
            "Paper BUY: %s %s @ %.4f (%.2f USDC, %.4f shares, fee=%.2f, slip=%.2f, lat=%dms)",
            side,
            outcome,
            entry_price,
            size_usd,
            shares,
            fee_usd,
            slippage_usd,
            latency_ms,
        )

        return True, "OK", position

    def execute_paper_sell(
        self,
        position_id: str,
        market_price: float,
    ) -> tuple[bool, str, PaperTrade | None]:
        """Execute a paper sell (close position) with realistic simulation."""
        position = self._positions.get(position_id)
        if not position:
            return False, "Position not found", None

        # Apply slippage on exit
        slippage_pct = random.uniform(0, self.config.slippage_bps / 10000.0)
        slippage_direction = 1 if random.random() > 0.3 else -1
        exit_price = market_price * (1 - slippage_direction * slippage_pct)
        exit_price = max(0.001, min(0.999, exit_price))

        # Calculate PnL
        pnl_per_share = exit_price - position.entry_price
        pnl_usd = pnl_per_share * position.shares

        # Fees on exit
        fee_pct = self.config.fee_bps / 10000.0
        exit_value = position.shares * exit_price
        fee_usd = exit_value * fee_pct
        slippage_usd = exit_value * slippage_pct * slippage_direction

        net_pnl = pnl_usd - fee_usd
        pnl_pct = (net_pnl / position.size_usd) * 100 if position.size_usd > 0 else 0

        # Simulate fill latency
        latency_ms = random.randint(self.config.fill_latency_ms_min, self.config.fill_latency_ms_max)

        # Release reserved funds + credit PnL
        try:
            self.wallet.release("USDC", Decimal(str(position.size_usd)), "paper_sell", position_id)
            if net_pnl > 0:
                self.wallet.credit("USDC", Decimal(str(net_pnl)), "paper_pnl", position_id)
            else:
                self.wallet.debit("USDC", Decimal(str(abs(net_pnl))), "paper_pnl", position_id)
        except Exception as e:
            return False, f"Wallet update failed: {e}", None

        # Create trade record
        trade = PaperTrade(
            id=uuid.uuid4().hex[:12],
            position_id=position_id,
            side=position.side,
            outcome=position.outcome,
            entry_price=position.entry_price,
            exit_price=exit_price,
            size_usd=position.size_usd,
            shares=position.shares,
            pnl_usd=net_pnl,
            pnl_pct=pnl_pct,
            fees_usd=fee_usd,
            slippage_usd=slippage_usd,
            latency_ms=latency_ms,
            timestamp=int(time.time() * 1000),
            market_id=position.market_id,
        )

        self._trades.append(trade)
        del self._positions[position_id]
        self._daily_pnl += net_pnl

        # Record in wallet performance
        self.wallet.record_trade(Decimal(str(net_pnl)), Decimal(str(fee_usd)))

        logger.info(
            "Paper SELL: %s %s @ %.4f (entry=%.4f) PnL=$%.2f (%.2f%%) fee=%.2f lat=%dms",
            position.side,
            position.outcome,
            exit_price,
            position.entry_price,
            net_pnl,
            pnl_pct,
            fee_usd,
            latency_ms,
        )

        return True, "OK", trade

    def get_position_market_price(self, position: PaperPosition, current_up: float, current_down: float) -> float:
        """Get current market price for a position."""
        if position.outcome.lower() in ("yes", "up"):
            return current_up
        return current_down

    def check_stop_loss(self, position: PaperPosition, current_price: float, stop_loss_pct: float = 0.10) -> bool:
        """Check if position hit stop loss."""
        if position.entry_price <= 0:
            return False
        loss_pct = (position.entry_price - current_price) / position.entry_price
        return loss_pct >= stop_loss_pct

    def get_performance(self) -> dict[str, Any]:
        """Get paper trading performance metrics."""
        if not self._trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl_usd": 0.0,
                "total_fees_usd": 0.0,
                "avg_pnl_usd": 0.0,
                "avg_pnl_pct": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe": 0.0,
            }

        winning = [t for t in self._trades if t.pnl_usd > 0]
        losing = [t for t in self._trades if t.pnl_usd < 0]

        total_pnl = sum(t.pnl_usd for t in self._trades)
        total_fees = sum(t.fees_usd for t in self._trades)
        win_rate = len(winning) / len(self._trades) if self._trades else 0

        gross_profit = sum(t.pnl_usd for t in winning)
        gross_loss = abs(sum(t.pnl_usd for t in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Simple Sharpe (using trade returns)
        returns = [t.pnl_pct / 100.0 for t in self._trades]
        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if len(returns) > 1 else 0
        sharpe = (avg_return / std_return * (252**0.5)) if std_return > 0 else 0

        # Max drawdown
        cumulative = 0
        peak = 0
        max_dd = 0
        for t in self._trades:
            cumulative += t.pnl_usd
            if cumulative > peak:
                peak = cumulative
            dd = (peak - cumulative) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return {
            "total_trades": len(self._trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": win_rate,
            "total_pnl_usd": total_pnl,
            "total_fees_usd": total_fees,
            "avg_pnl_usd": total_pnl / len(self._trades),
            "avg_pnl_pct": sum(t.pnl_pct for t in self._trades) / len(self._trades),
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_dd * 100,
            "sharpe": sharpe,
        }

    def reset(self) -> None:
        """Reset paper engine state."""
        self._positions.clear()
        self._trades.clear()
        self._daily_pnl = 0.0
        self._day_start = time.time()
        self._last_trade_time = 0.0
        self.wallet.reset(initial_balances={"USDC": Decimal(str(self.config.initial_usd))})
