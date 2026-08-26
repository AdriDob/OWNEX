"""Engines Package for Polymarket BTC Latency Arb."""

from __future__ import annotations

from core.polymarket.btc_latency_arb.engines.edge import Decision, EdgeResult, compute_edge, decide
from core.polymarket.btc_latency_arb.engines.probability import ScoredDirection, apply_time_awareness, score_direction
from core.polymarket.btc_latency_arb.engines.regime import RegimeInfo, detect_regime

__all__ = [
    "detect_regime",
    "RegimeInfo",
    "score_direction",
    "apply_time_awareness",
    "ScoredDirection",
    "compute_edge",
    "decide",
    "EdgeResult",
    "Decision",
]
