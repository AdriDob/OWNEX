"""Persistence for Polymarket BTC Latency Arb trades."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from core.polymarket.btc_latency_arb.config import BTCArbConfig

logger = logging.getLogger("orion.polymarket.btc_latency_arb.persistence")


class TradeHistory:
    """Trade history persistence using JSONL format."""

    def __init__(self, config: BTCArbConfig) -> None:
        self.config = config
        self._trades: list[dict[str, Any]] = []
        self._max_in_memory = config.persistence.max_trades_in_memory
        self._load()

    def _load(self) -> None:
        """Load trade history from disk."""
        try:
            path = self.config.trades_path
            if path.exists():
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._trades.append(json.loads(line))
                # Keep only recent trades in memory
                if len(self._trades) > self._max_in_memory:
                    self._trades = self._trades[-self._max_in_memory :]
                logger.info("Loaded %d trades from %s", len(self._trades), path)
        except Exception as e:
            logger.warning("Failed to load trade history: %s", e)

    def add_trade(self, trade: dict[str, Any]) -> None:
        """Add a trade to history."""
        trade["_id"] = len(self._trades)
        trade["_timestamp"] = trade.get("timestamp", int(time.time() * 1000))
        self._trades.append(trade)

        # Persist to disk (append)
        self._persist_trade(trade)

        # Trim memory
        if len(self._trades) > self._max_in_memory:
            self._trades = self._trades[-self._max_in_memory :]

    def _persist_trade(self, trade: dict[str, Any]) -> None:
        """Append single trade to JSONL file."""
        try:
            path = self.config.trades_path
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a") as f:
                f.write(json.dumps(trade, default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to persist trade: %s", e)

    def get_trades(
        self,
        limit: int = 100,
        offset: int = 0,
        trade_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get trades with pagination."""
        trades = self._trades
        if trade_type:
            trades = [t for t in trades if t.get("type") == trade_type]
        return trades[offset : offset + limit]

    def get_performance(self) -> dict[str, Any]:
        """Calculate performance from trade history."""
        if not self._trades:
            return {
                "total_trades": 0,
                "entries": 0,
                "exits": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "avg_pnl": 0.0,
            }

        entries = [t for t in self._trades if t.get("type") == "entry"]
        exits = [t for t in self._trades if t.get("type") == "exit"]

        total_pnl = sum(t.get("trade", {}).get("pnl_usd", 0) for t in exits if "trade" in t)
        winning = sum(1 for t in exits if t.get("trade", {}).get("pnl_usd", 0) > 0)
        losing = sum(1 for t in exits if t.get("trade", {}).get("pnl_usd", 0) < 0)

        gross_profit = sum(
            t.get("trade", {}).get("pnl_usd", 0) for t in exits if t.get("trade", {}).get("pnl_usd", 0) > 0
        )
        gross_loss = abs(
            sum(t.get("trade", {}).get("pnl_usd", 0) for t in exits if t.get("trade", {}).get("pnl_usd", 0) < 0)
        )

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        win_rate = winning / len(exits) if exits else 0

        return {
            "total_trades": len(exits),
            "entries": len(entries),
            "exits": len(exits),
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_pnl": total_pnl / len(exits) if exits else 0,
            "winning_trades": winning,
            "losing_trades": losing,
        }

    def save(self) -> None:
        """Force save (no-op for JSONL append)."""
        pass

    def get_recent_signals(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent signal/decision events."""
        signals = [t for t in self._trades if t.get("type") == "entry"]
        return signals[-limit:]

    def clear(self) -> None:
        """Clear all trade history."""
        self._trades.clear()
        path = self.config.trades_path
        if path.exists():
            path.unlink()
        logger.info("Trade history cleared")
