"""Session state for MT5 bridge arm.

Manages armed flag, TTL expiration, and risk guard checks.

All state is ephemeral — lost on process restart. Persisted via
environment / bridge-sidecar if needed.
"""

from __future__ import annotations

import time
from typing import Any


class ArmSession:
    """Tracks a single arm session with TTL and risk limits."""

    def __init__(self, body: dict[str, Any], ttl_hours: int | None = None):
        self.armed: bool = True
        self.armed_at: float = time.time()
        if ttl_hours is None:
            self.ttl_seconds: float = 8 * 3600
        elif ttl_hours == 0:
            self.ttl_seconds: float = 0
        else:
            self.ttl_seconds: float = ttl_hours * 3600
        self.expires_at: float = self.armed_at + self.ttl_seconds
        self.max_lot: float = body.get("max_lot", 0.01)
        self.whitelist: list[str] = body.get("symbols", ["EURUSD"])
        self.max_open: int = body.get("max_open", 1)
        self.max_daily_loss_pct: float = body.get("max_daily_loss_pct", 2.0)
        self.purpose: str = body.get("purpose", "demo-canary")
        self.kill: bool = False  # set by disarm/kill endpoints

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at

    def check_lot(self, lot: float) -> bool:
        return not self.expired and not self.kill and lot <= self.max_lot

    def check_symbol(self, symbol: str) -> bool:
        return not self.expired and not self.kill and symbol in self.whitelist

    def check_open(self, open_positions: int) -> bool:
        return not self.expired and not self.kill and open_positions < self.max_open

    def check_daily_loss(self, daily_loss_pct: float) -> bool:
        return not self.expired and not self.kill and daily_loss_pct <= self.max_daily_loss_pct

    def to_dict(self) -> dict[str, Any]:
        return {
            "armed": self.armed,
            "expires_at": self.expires_at,
            "max_lot": self.max_lot,
            "symbols": self.whitelist,
            "max_open": self.max_open,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "purpose": self.purpose,
            "kill": self.kill,
        }


# Manual session management (no global state)
def create_session(body: dict[str, Any], ttl_hours: int | None = None) -> ArmSession:
    """Create a new arm session with the given body and TTL."""
    return ArmSession(body, ttl_hours)


def get_session() -> ArmSession | None:
    """Return the current session (for compatibility with existing code)."""
    # No global state — callers should create/manage their own session
    return None


# Backward compatibility aliases
set_session = create_session
