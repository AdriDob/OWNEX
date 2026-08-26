"""Polymarket BTC Latency Arbitrage - Main Package.

Standalone high-risk investment type for Binance->Polymarket
latency arbitrage on BTC UP/DOWN markets.
"""

from __future__ import annotations

from core.polymarket.btc_latency_arb.config import BTCArbConfig
from core.polymarket.btc_latency_arb.execution import OrderExecutor
from core.polymarket.btc_latency_arb.paper_engine import PaperTradingEngine
from core.polymarket.btc_latency_arb.persistence import TradeHistory
from core.polymarket.btc_latency_arb.risk import RiskManager
from core.polymarket.btc_latency_arb.runner import BTCArbRunner
from core.polymarket.btc_latency_arb.sizing import PositionSizer

__all__ = [
    "BTCArbConfig",
    "BTCArbRunner",
    "PaperTradingEngine",
    "RiskManager",
    "PositionSizer",
    "OrderExecutor",
    "TradeHistory",
]
