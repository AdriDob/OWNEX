"""Polymarket module configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class PolymarketConfig:
    """Global configuration for Polymarket module."""

    # API
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    clob_api_url: str = "https://clob.polymarket.com"
    ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: float = 60.0

    # Timeouts
    request_timeout: float = 10.0
    ws_heartbeat_interval: float = 30.0

    # Strategy defaults
    default_max_position_usd: float = 100.0
    default_max_total_exposure: float = 500.0

    # Risk
    max_daily_loss: float = 50.0
    max_drawdown_pct: float = 0.10  # 10%

    @classmethod
    def from_env(cls) -> PolymarketConfig:
        """Create config from environment variables."""
        return cls(
            gamma_api_url=os.getenv("POLYMARKET_GAMMA_API", cls.gamma_api_url),
            clob_api_url=os.getenv("POLYMARKET_CLOB_API", cls.clob_api_url),
            ws_url=os.getenv("POLYMARKET_WS_URL", cls.ws_url),
            rate_limit_requests=int(os.getenv("POLYMARKET_RATE_LIMIT", str(cls.rate_limit_requests))),
            default_max_position_usd=float(os.getenv("POLYMARKET_MAX_POSITION", str(cls.default_max_position_usd))),
            default_max_total_exposure=float(os.getenv("POLYMARKET_MAX_EXPOSURE", str(cls.default_max_total_exposure))),
        )
