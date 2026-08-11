"""DeFi Yield Tracker — monitors yield positions and publishes yield events.

Tracks positions across DeFi protocols, computes APY via DefiLlama,
and publishes `financial:crypto_defi_yield` events to the EventBus
so the financial layer records them in the ledger.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.defi.positions import DefiPosition, YieldSnapshot

logger = logging.getLogger("orion.core.defi.tracker")

DEFILLAMA_API = "https://yields.llama.fi"


class DefiYieldTracker:
    """Tracks DeFi positions and yields.

    Maintains a list of positions, periodically refreshes APY from
    DefiLlama, and publishes yield events to the EventBus.
    """

    def __init__(self) -> None:
        self._positions: list[DefiPosition] = []
        self._snapshots: list[YieldSnapshot] = []
        self._event_bus = None

    def set_event_bus(self, bus: Any) -> None:
        self._event_bus = bus

    def add_position(self, position: DefiPosition) -> None:
        self._positions.append(position)

    def remove_position(self, protocol: str, asset: str) -> bool:
        before = len(self._positions)
        self._positions = [p for p in self._positions if not (p.protocol == protocol and p.asset == asset)]
        return len(self._positions) < before

    def list_positions(self) -> list[DefiPosition]:
        return list(self._positions)

    def clear_positions(self) -> None:
        self._positions.clear()

    def snapshot(self) -> YieldSnapshot:
        snap = YieldSnapshot(positions=list(self._positions))
        self._snapshots.append(snap)
        if len(self._snapshots) > 1000:
            self._snapshots = self._snapshots[-500:]
        return snap

    def latest_snapshot(self) -> YieldSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def refresh_apy_from_defillama(self, timeout: int = 15) -> dict[str, float]:
        """Fetch current APYs from DefiLlama for tracked positions.

        Returns a dict mapping protocol_slug -> apy (as percentage).
        """
        try:
            import requests

            resp = requests.get(f"{DEFILLAMA_API}/pools", timeout=timeout)
            if resp.status_code != 200:
                logger.warning("[DEFI] DefiLlama returned %s", resp.status_code)
                return {}

            pools = resp.json().get("data", [])
            apys: dict[str, float] = {}

            for position in self._positions:
                slug = position.protocol.lower().replace(" ", "-")
                chain = position.chain.lower()

                matching = [
                    p
                    for p in pools
                    if slug in p.get("project", "").lower()
                    and chain in p.get("chain", "").lower()
                    and "usd" in p.get("symbol", "").lower()
                ]

                if matching:
                    best = max(matching, key=lambda p: float(p.get("apy", 0)))
                    apy = float(best.get("apy", 0))
                    apys[position.protocol] = apy
                    position.apy = apy

            return apys

        except ImportError:
            logger.warning("[DEFI] requests not available for DefiLlama")
            return {}
        except Exception as exc:
            logger.warning("[DEFI] DefiLlama refresh error: %s", exc)
            return {}

    def publish_yield_events(self) -> list[dict[str, Any]]:
        """Publish yield events for all positions to EventBus.

        Returns a list of event dicts that were published.
        """
        events = []
        for position in self._positions:
            monthly = position.monthly_yield
            event = {
                "event_type": "financial:crypto_defi_yield",
                "protocol": position.protocol,
                "chain": position.chain,
                "asset": position.asset,
                "amount": position.amount,
                "usd_value": position.usd_value,
                "apy": position.apy,
                "monthly_yield": round(monthly, 2),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            events.append(event)

            if self._event_bus is not None:
                try:
                    self._event_bus.publish("financial:crypto_defi_yield", event)
                except Exception as exc:
                    logger.warning("[DEFI] Event publish error: %s", exc)

        if events:
            logger.info("[DEFI] Published %s yield events", len(events))
        return events

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "total_positions": len(self._positions),
            "total_value": round(snap.total_value, 2),
            "total_monthly_yield": round(snap.total_monthly_yield, 2),
            "weighted_apy": round(snap.weighted_apy, 2),
            "positions": [p.to_dict() for p in self._positions],
            "last_snapshot": snap.to_dict(),
        }


# Singleton instance shared across the system
_DEFI_TRACKER: DefiYieldTracker | None = None


def get_defi_tracker() -> DefiYieldTracker:
    global _DEFI_TRACKER
    if _DEFI_TRACKER is None:
        _DEFI_TRACKER = DefiYieldTracker()
    return _DEFI_TRACKER
