"""Polymarket BTC Latency Arb - WebSocket Feeds Package."""

from __future__ import annotations

from cores.polymarket.btc_latency_arb.feeds.base import FeedCallback, PriceFeed
from cores.polymarket.btc_latency_arb.feeds.binance_ws import BinanceWSFeed
from cores.polymarket.btc_latency_arb.feeds.polymarket_ws import PolymarketWSFeed

__all__ = [
    "PriceFeed",
    "FeedCallback",
    "BinanceWSFeed",
    "PolymarketWSFeed",
]
