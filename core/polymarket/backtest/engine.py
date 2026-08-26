"""Polymarket Backtesting Engine — simulate strategies against historical data.

Features:
- Historical price data fetching
- Strategy simulation with configurable parameters
- Performance metrics (Sharpe, win rate, max drawdown, etc.)
- Comparison between strategies
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("orion.polymarket.backtest")


@dataclass
class BacktestConfig:
    """Backtesting configuration."""

    # Time range
    start_date: str = "2026-01-01"
    end_date: str = "2026-08-21"

    # Initial capital
    initial_capital: float = 1000.0

    # Risk management
    max_position_pct: float = 0.1  # Max 10% per position
    max_positions: int = 10
    stop_loss_pct: float = 0.10  # 10% stop loss
    take_profit_pct: float = 0.20  # 20% take profit

    # Fees
    maker_fee: float = 0.001  # 0.1%
    taker_fee: float = 0.002  # 0.2%

    # Slippage
    slippage_pct: float = 0.005  # 0.5% slippage


@dataclass
class Trade:
    """A simulated trade."""

    market_id: str
    outcome: str
    entry_price: float
    exit_price: float
    size_usd: float
    entry_time: float
    exit_time: float
    pnl: float
    pnl_pct: float
    fees: float
    slippage: float
    reason: str  # take_profit, stop_loss, signal, manual


@dataclass
class BacktestResult:
    """Backtesting results."""

    strategy: str
    config: BacktestConfig
    trades: list[Trade]

    # Performance metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0

    # Time metrics
    avg_holding_time: float = 0.0
    total_fees: float = 0.0
    total_slippage: float = 0.0


class BacktestEngine:
    """Backtesting engine for Polymarket strategies.

    Usage:
        engine = BacktestEngine(config)
        result = engine.run(strategy_func, historical_data)
        engine.print_report(result)
    """

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self._config = config or BacktestConfig()
        self._positions: dict[str, dict[str, Any]] = {}
        self._trades: list[Trade] = []
        self._equity_curve: list[tuple[float, float]] = []

    async def fetch_historical_data(
        self,
        market_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch historical price data for a market.

        In production, this would fetch from Polymarket API or cache.
        For now, returns simulated data.
        """
        # TODO: Implement real historical data fetching
        # This would call the Polymarket CLOB API for price history
        logger.info(
            "Fetching historical data for %s (%s to %s)",
            market_id,
            start_date,
            end_date,
        )
        return []

    def run(
        self,
        strategy_func: Callable[[dict[str, Any]], dict[str, Any] | None],
        historical_data: list[dict[str, Any]],
        market_id: str = "simulated",
    ) -> BacktestResult:
        """Run backtest with a strategy function.

        Args:
            strategy_func: Function that takes market data and returns trade signal
            historical_data: List of historical price/volume data
            market_id: Market identifier

        Returns:
            BacktestResult with performance metrics
        """
        capital = self._config.initial_capital
        self._positions = {}
        self._trades = []
        self._equity_curve = [(0, capital)]

        for i, data_point in enumerate(historical_data):
            timestamp = data_point.get("timestamp", time.time())
            price = data_point.get("price", 0)
            volume = data_point.get("volume", 0)

            if price <= 0:
                continue

            # Check existing positions for exit conditions
            self._check_exits(price, timestamp, capital)

            # Get strategy signal
            signal = strategy_func(data_point)

            if signal and signal.get("execute"):
                # Calculate position size
                size_pct = self._config.max_position_pct
                size_usd = capital * size_pct

                if size_usd > 0 and len(self._positions) < self._config.max_positions:
                    self._open_position(
                        market_id=market_id,
                        outcome=signal.get("outcome", "YES"),
                        price=price,
                        size_usd=size_usd,
                        timestamp=timestamp,
                    )

            # Update equity curve
            unrealized = self._calculate_unrealized_pnl(price)
            equity = capital + unrealized
            self._equity_curve.append((timestamp, equity))

        # Close remaining positions at last price
        if historical_data:
            last_price = historical_data[-1].get("price", 0)
            last_time = historical_data[-1].get("timestamp", time.time())
            self._close_all_positions(last_price, last_time)

        # Calculate metrics
        return self._calculate_metrics()

    def _open_position(
        self,
        market_id: str,
        outcome: str,
        price: float,
        size_usd: float,
        timestamp: float,
    ) -> None:
        """Open a new position."""
        # Apply slippage
        slippage = price * self._config.slippage_pct
        entry_price = price + slippage

        # Apply fees
        fees = size_usd * self._config.taker_fee

        self._positions[market_id] = {
            "outcome": outcome,
            "entry_price": entry_price,
            "size_usd": size_usd,
            "entry_time": timestamp,
            "fees": fees,
            "slippage": slippage,
        }

        logger.debug(
            "Opened position: %s @ $%.4f, size $%.2f",
            outcome,
            entry_price,
            size_usd,
        )

    def _check_exits(self, current_price: float, timestamp: float, capital: float) -> None:
        """Check for exit conditions on all positions."""
        for market_id, pos in list(self._positions.items()):
            entry_price = pos["entry_price"]
            pnl_pct = (current_price - entry_price) / entry_price

            # Stop loss
            if pnl_pct <= -self._config.stop_loss_pct:
                self._close_position(
                    market_id=market_id,
                    exit_price=current_price,
                    timestamp=timestamp,
                    reason="stop_loss",
                )

            # Take profit
            elif pnl_pct >= self._config.take_profit_pct:
                self._close_position(
                    market_id=market_id,
                    exit_price=current_price,
                    timestamp=timestamp,
                    reason="take_profit",
                )

    def _close_position(
        self,
        market_id: str,
        exit_price: float,
        timestamp: float,
        reason: str,
    ) -> None:
        """Close a position and record the trade."""
        pos = self._positions.pop(market_id, None)
        if not pos:
            return

        entry_price = pos["entry_price"]
        size_usd = pos["size_usd"]
        entry_time = pos["entry_time"]

        # Apply slippage on exit
        slippage = exit_price * self._config.slippage_pct
        actual_exit = exit_price - slippage

        # Calculate PnL
        pnl = (actual_exit - entry_price) * (size_usd / entry_price)
        pnl_pct = (actual_exit - entry_price) / entry_price

        # Total fees
        exit_fees = size_usd * self._config.maker_fee
        total_fees = pos["fees"] + exit_fees

        trade = Trade(
            market_id=market_id,
            outcome=pos["outcome"],
            entry_price=entry_price,
            exit_price=actual_exit,
            size_usd=size_usd,
            entry_time=entry_time,
            exit_time=timestamp,
            pnl=pnl - total_fees,
            pnl_pct=pnl_pct,
            fees=total_fees,
            slippage=pos["slippage"] + slippage,
            reason=reason,
        )
        self._trades.append(trade)

        logger.debug(
            "Closed position: %s @ $%.4f, PnL: $%.4f (%s)",
            pos["outcome"],
            actual_exit,
            trade.pnl,
            reason,
        )

    def _close_all_positions(self, last_price: float, last_time: float) -> None:
        """Close all remaining positions."""
        for market_id in list(self._positions.keys()):
            self._close_position(
                market_id=market_id,
                exit_price=last_price,
                timestamp=last_time,
                reason="backtest_end",
            )

    def _calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL for all open positions."""
        total = 0.0
        for pos in self._positions.values():
            entry_price = pos["entry_price"]
            size_usd = pos["size_usd"]
            pnl = (current_price - entry_price) * (size_usd / entry_price)
            total += pnl
        return total

    def _calculate_metrics(self) -> BacktestResult:
        """Calculate performance metrics from trades."""
        trades = self._trades
        config = self._config

        # Basic counts
        total_trades = len(trades)
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]

        win_rate = len(winning) / total_trades * 100 if total_trades > 0 else 0
        total_pnl = sum(t.pnl for t in trades)
        total_pnl_pct = total_pnl / config.initial_capital * 100

        # Averages
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        avg_win = sum(t.pnl for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.pnl for t in losing) / len(losing) if losing else 0

        # Max drawdown
        max_drawdown = 0.0
        peak = config.initial_capital
        for _, equity in self._equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Sharpe ratio (simplified)
        if trades:
            returns = [t.pnl_pct for t in trades]
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe = (avg_return / std_return * 252**0.5) if std_return > 0 else 0
        else:
            sharpe = 0

        # Profit factor
        gross_profit = sum(t.pnl for t in winning)
        gross_loss = abs(sum(t.pnl for t in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        # Time metrics
        holding_times = [(t.exit_time - t.entry_time) for t in trades]
        avg_holding = sum(holding_times) / len(holding_times) if holding_times else 0

        # Fees and slippage
        total_fees = sum(t.fees for t in trades)
        total_slippage = sum(t.slippage for t in trades)

        return BacktestResult(
            strategy="backtest",
            config=config,
            trades=trades,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_pnl=avg_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            expectancy=expectancy,
            avg_holding_time=avg_holding,
            total_fees=total_fees,
            total_slippage=total_slippage,
        )

    def print_report(self, result: BacktestResult) -> None:
        """Print a formatted backtest report."""
        print("\n" + "=" * 60)
        print("BACKTEST REPORT")
        print("=" * 60)
        print(f"\nStrategy: {result.strategy}")
        print(f"Period: {result.config.start_date} to {result.config.end_date}")
        print(f"Initial Capital: ${result.config.initial_capital:,.2f}")

        print("\n--- PERFORMANCE ---")
        print(f"Total Trades:    {result.total_trades}")
        print(f"Winning:         {result.winning_trades} ({result.win_rate:.1f}%)")
        print(f"Losing:          {result.losing_trades}")
        print(f"Total PnL:       ${result.total_pnl:,.2f} ({result.total_pnl_pct:.1f}%)")
        print(f"Avg PnL/Trade:   ${result.avg_pnl:,.2f}")
        print(f"Avg Win:         ${result.avg_win:,.2f}")
        print(f"Avg Loss:        ${result.avg_loss:,.2f}")

        print("\n--- RISK ---")
        print(f"Max Drawdown:    {result.max_drawdown:.1%}")
        print(f"Sharpe Ratio:    {result.sharpe_ratio:.2f}")
        print(f"Profit Factor:   {result.profit_factor:.2f}")
        print(f"Expectancy:      ${result.expectancy:,.2f}")

        print("\n--- COSTS ---")
        print(f"Total Fees:      ${result.total_fees:,.2f}")
        print(f"Total Slippage:  ${result.total_slippage:,.4f}")
        print(f"Avg Holding:     {result.avg_holding_time:.1f}s")

        # Trade breakdown
        if result.trades:
            print("\n--- TRADES (last 10) ---")
            for t in result.trades[-10:]:
                emoji = "✅" if t.pnl > 0 else "❌"
                print(
                    f"  {emoji} {t.outcome} @ ${t.entry_price:.4f} → ${t.exit_price:.4f} "
                    f"PnL: ${t.pnl:+.2f} ({t.reason})"
                )

        print("\n" + "=" * 60)
