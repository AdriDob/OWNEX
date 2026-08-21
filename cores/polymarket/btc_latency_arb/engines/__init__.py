"""Engines Package for Polymarket BTC Latency Arb."""

from __future__ import annotations

from core.polymarket.btc_latency_arb.engines.regime import detect_regime, RegimeInfo
from core.polymarket.btc_latency_arb.engines.probability import score_direction, apply_time_awareness, ScoredDirection
from core.polymarket.btc_latency_arb.engines.edge import compute_edge, decide, EdgeResult, Decision

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
