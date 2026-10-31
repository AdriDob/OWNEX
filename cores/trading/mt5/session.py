"""Session state for MT5 bridge arm.

Manages armed flag, TTL expiration, and risk guard checks.

All state is ephemeral — lost on process restart. Persisted via
environment / bridge-sidecar if needed.
"""

from __future__ import annotations

import time
from typing import Any

# Global session state (for backward compatibility with existing code)
_session: ArmSession | None = None


class ArmSession:
    """Tracks a single arm session with TTL and risk limits."""

    def __init__(self, body: dict[str, Any], ttl_hours: int | None = None):
        self.armed: bool = True
        self.armed_at: float = time.time()

        # Determine ttl_hours: use explicit parameter, then fall back to body dict
        if ttl_hours is None:
            ttl_hours = body.get("ttl_hours")
        if ttl_hours is None:
            ttl_hours = 8  # default 8 hours

        if ttl_hours == 0:
            self.ttl_seconds: float = 0
        elif isinstance(ttl_hours, (int, float)):
            self.ttl_seconds: float = ttl_hours * 3600
        else:
            self.ttl_seconds: float = 8 * 3600  # default fallback

        self.expires_at: float = self.armed_at + self.ttl_seconds
        self.max_lot: float = body.get("max_lot", 0.01)
        self.whitelist: list = body.get("symbols", ["EURUSD"])
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


# Global session management
def set_session(body: dict[str, Any], ttl_hours: int | None = None) -> ArmSession:
    """Create/overwrite the global arm session."""
    global _session
    _session = ArmSession(body, ttl_hours)
    return _session


def get_session() -> ArmSession | None:
    """Return the current global arm session."""
    return _session


# No global state alternative functions
def create_session(body: dict[str, Any], ttl_hours: int | None = None) -> ArmSession:
    """Create a new arm session (no global state)."""
    return ArmSession(body, ttl_hours)
