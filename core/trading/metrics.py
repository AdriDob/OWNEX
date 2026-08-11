from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class TradeRecord:
    pair: str
    side: str
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    pnl: Decimal
    pnl_percent: Decimal
    fee: Decimal
    entry_time: datetime
    exit_time: datetime
    duration_seconds: float = 0.0


@dataclass
class PerformanceMetrics:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: Decimal = Decimal()
    total_fees: Decimal = Decimal()
    net_pnl: Decimal = Decimal()
    profit_factor: float = 0.0
    avg_win: Decimal = Decimal()
    avg_loss: Decimal = Decimal()
    largest_win: Decimal = Decimal()
    largest_loss: Decimal = Decimal()
    max_drawdown_pct: float = 0.0
    max_drawdown_usd: Decimal = Decimal()
    sharpe_ratio: float = 0.0
    avg_trade_duration_seconds: float = 0.0
    start_balance: Decimal = Decimal()
    end_balance: Decimal = Decimal()
    return_pct: float = 0.0
    calculated_at: datetime = field(default_factory=datetime.utcnow)


def calculate_performance(
    trades: Sequence[TradeRecord],
    initial_balance: Decimal | None = None,
    final_balance: Decimal | None = None,
    risk_free_rate: float = 0.05,
) -> PerformanceMetrics:
    metrics = PerformanceMetrics()
    metrics.total_trades = len(trades)

    if not trades:
        return metrics

    wins = [t for t in trades if t.pnl > Decimal()]
    losses = [t for t in trades if t.pnl < Decimal()]
    metrics.winning_trades = len(wins)
    metrics.losing_trades = len(losses)
    metrics.win_rate = len(wins) / len(trades) if trades else 0.0

    metrics.total_pnl = sum((t.pnl for t in trades), Decimal())
    metrics.total_fees = sum((t.fee for t in trades), Decimal())
    metrics.net_pnl = metrics.total_pnl - metrics.total_fees

    total_gross_profit = sum((t.pnl for t in wins), Decimal())
    total_gross_loss = abs(sum((t.pnl for t in losses), Decimal()))
    metrics.profit_factor = (
        float(total_gross_profit / total_gross_loss) if total_gross_loss > Decimal() else float("inf")
    )

    if wins:
        metrics.avg_win = sum((t.pnl for t in wins), Decimal()) / len(wins)
        metrics.largest_win = max(t.pnl for t in wins)
    if losses:
        metrics.avg_loss = sum((t.pnl for t in losses), Decimal()) / len(losses)
        metrics.largest_loss = min(t.pnl for t in losses)

    if initial_balance and initial_balance > Decimal():
        metrics.start_balance = initial_balance
        end = final_balance or (initial_balance + metrics.net_pnl)
        metrics.end_balance = end
        metrics.return_pct = float((end - initial_balance) / initial_balance * Decimal("100"))

    if initial_balance and len(trades) > 1:
        returns: list[float] = []
        running = float(initial_balance)
        peak = running
        max_dd = 0.0
        max_dd_value = Decimal()
        for t in trades:
            pnl_float = float(t.pnl)
            prev = running
            running += pnl_float
            if running > peak:
                peak = running
            dd = (peak - running) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                max_dd_value = Decimal(str(peak)) - Decimal(str(running))
            returns.append((running - prev) / prev if prev > 0 else 0)
        metrics.max_drawdown_pct = max_dd * 100
        metrics.max_drawdown_usd = max_dd_value

        if len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = variance**0.5
            if std_dev > 0:
                metrics.sharpe_ratio = ((avg_return - risk_free_rate / 365) / std_dev) * (365**0.5)

    durations = [t.duration_seconds for t in trades if t.duration_seconds > 0]
    if durations:
        metrics.avg_trade_duration_seconds = sum(durations) / len(durations)

    return metrics
