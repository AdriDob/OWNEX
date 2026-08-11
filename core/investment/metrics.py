from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.investment.models import InvestmentSnapshot, RiskMetrics

logger = logging.getLogger("orion.investment.metrics")


def _data_dir() -> Path:
    return Path.home() / ".orion" / "investment"


class InvestmentMetrics:
    """Tracks investment performance across all strategies.

    Provides ROI, Sharpe ratio, drawdown, and other metrics
    per strategy and consolidated.
    """

    def __init__(self) -> None:
        self._trade_history: list[dict[str, Any]] = []
        self._daily_snapshots: list[dict[str, Any]] = []
        _data_dir().mkdir(parents=True, exist_ok=True)
        self._load_history()

    def record_trade(
        self,
        strategy_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        pnl_pct: float,
        fee: float = 0.0,
        duration_hours: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        trade = {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "fee": fee,
            "duration_hours": duration_hours,
            "won": pnl > 0,
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        }
        self._trade_history.append(trade)
        self._persist_trade(trade)
        logger.debug("Trade recorded: %s %s $%.2f (%.2f%%)", strategy_id, symbol, pnl, pnl_pct)

    def record_daily_snapshot(self, snapshot: InvestmentSnapshot) -> None:
        entry = {
            "date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "total_capital": snapshot.total_capital,
            "deployed": snapshot.deployed,
            "available": snapshot.available,
            "total_pnl": snapshot.total_pnl,
            "total_pnl_pct": snapshot.total_pnl_pct,
            "timestamp": snapshot.timestamp,
        }
        self._daily_snapshots.append(entry)
        self._persist_snapshot(entry)

    def get_strategy_metrics(self, strategy_id: str) -> RiskMetrics:
        trades = [t for t in self._trade_history if t["strategy_id"] == strategy_id]
        return self._compute_metrics(strategy_id, trades)

    def get_all_strategy_metrics(self) -> dict[str, RiskMetrics]:
        by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for t in self._trade_history:
            by_strategy[t["strategy_id"]].append(t)
        return {sid: self._compute_metrics(sid, trades) for sid, trades in by_strategy.items()}

    def _compute_metrics(self, strategy_id: str, trades: list[dict[str, Any]]) -> RiskMetrics:
        if not trades:
            return RiskMetrics(strategy_id=strategy_id)

        winning = [t for t in trades if t["won"]]
        losing = [t for t in trades if not t["won"]]

        max_dd = self._calculate_max_drawdown(trades)

        avg_win = sum(t["pnl_pct"] for t in winning) / max(len(winning), 1) if winning else 0.0
        avg_loss = sum(abs(t["pnl_pct"]) for t in losing) / max(len(losing), 1) if losing else 0.0

        returns = [t["pnl_pct"] for t in trades]
        avg_return = sum(returns) / max(len(returns), 1)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / max(len(returns), 1)) ** 0.5 if returns else 0.0
        sharpe = (avg_return / max(std_return, 0.001)) * (252**0.5) if std_return > 0 else 0.0

        consecutive_losses = 0
        max_consecutive_losses = 0
        for t in trades:
            if not t["won"]:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0

        current_dd = self._calculate_current_drawdown(trades)

        return RiskMetrics(
            strategy_id=strategy_id,
            current_drawdown_pct=current_dd,
            max_drawdown_pct=max_dd,
            sharpe_ratio=round(sharpe, 2),
            win_rate=round(len(winning) / max(len(trades), 1), 4),
            profit_factor=round(sum(t["pnl"] for t in winning) / max(abs(sum(t["pnl"] for t in losing)), 0.001), 2),
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            consecutive_losses=consecutive_losses,
            worst_streak=max_consecutive_losses,
            avg_win_pct=round(avg_win, 2),
            avg_loss_pct=round(avg_loss, 2),
            is_drawdown=current_dd > 5.0,
        )

    def _calculate_max_drawdown(self, trades: list[dict]) -> float:
        if not trades:
            return 0.0
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in trades:
            cumulative += t["pnl"]
            if cumulative > peak:
                peak = cumulative
            drawdown = (peak - cumulative) / max(peak, 1) * 100
            max_dd = max(max_dd, drawdown)
        return round(max_dd, 2)

    def _calculate_current_drawdown(self, trades: list[dict]) -> float:
        if not trades:
            return 0.0
        cumulative = 0.0
        peak = 0.0
        for t in trades:
            cumulative += t["pnl"]
            if cumulative > peak:
                peak = cumulative
        if peak <= 0:
            return 0.0
        return round((peak - cumulative) / peak * 100, 2)

    def consolidated_metrics(self) -> dict[str, Any]:
        all_metrics = self.get_all_strategy_metrics()
        total_trades = sum(m.total_trades for m in all_metrics.values())
        winning = sum(m.winning_trades for m in all_metrics.values())
        total_pnl = sum(sum(t["pnl"] for t in self._trade_history if t["strategy_id"] == sid) for sid in all_metrics)

        return {
            "total_trades": total_trades,
            "winning_trades": winning,
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(winning / max(total_trades, 1), 4),
            "strategies": {
                sid: {
                    "sharpe": m.sharpe_ratio,
                    "win_rate": m.win_rate,
                    "profit_factor": m.profit_factor,
                    "total_trades": m.total_trades,
                    "current_drawdown_pct": m.current_drawdown_pct,
                    "max_drawdown_pct": m.max_drawdown_pct,
                    "is_drawdown": m.is_drawdown,
                    "should_pause": m.should_pause,
                    "is_healthy": m.is_healthy,
                }
                for sid, m in all_metrics.items()
            },
            "snapshots_count": len(self._daily_snapshots),
        }

    def pnl_chart_data(self, days: int = 30) -> list[dict[str, Any]]:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        recent = [t for t in self._trade_history if t.get("timestamp", "") >= cutoff.isoformat()]
        daily: dict[str, float] = defaultdict(float)
        for t in recent:
            day = t["timestamp"][:10]
            daily[day] += t["pnl"]
        return [{"date": d, "pnl": round(p, 2)} for d, p in sorted(daily.items())]

    def _persist_trade(self, trade: dict[str, Any]) -> None:
        try:
            path = _data_dir() / "trades.jsonl"
            with open(path, "a") as f:
                f.write(json.dumps(trade, default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to persist trade: %s", e)

    def _persist_snapshot(self, snapshot: dict[str, Any]) -> None:
        try:
            path = _data_dir() / "daily_snapshots.jsonl"
            with open(path, "a") as f:
                f.write(json.dumps(snapshot, default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to persist snapshot: %s", e)

    def _load_history(self) -> None:
        trades_path = _data_dir() / "trades.jsonl"
        if trades_path.exists():
            try:
                for line in trades_path.read_text().strip().split("\n"):
                    if line.strip():
                        self._trade_history.append(json.loads(line))
            except Exception as e:
                logger.warning("Failed to load trade history: %s", e)

        snap_path = _data_dir() / "daily_snapshots.jsonl"
        if snap_path.exists():
            try:
                for line in snap_path.read_text().strip().split("\n"):
                    if line.strip():
                        self._daily_snapshots.append(json.loads(line))
            except Exception as e:
                logger.warning("Failed to load snapshot history: %s", e)


_INSTANCE: InvestmentMetrics | None = None


def get_investment_metrics() -> InvestmentMetrics:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = InvestmentMetrics()
    return _INSTANCE


def reset_investment_metrics() -> None:
    global _INSTANCE
    _INSTANCE = None
