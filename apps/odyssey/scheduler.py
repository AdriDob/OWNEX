"""ODYSSEY scheduler jobs — bet sync, analytics calculation."""

from __future__ import annotations

import logging

from core.events.event_bus import get_core_event_bus

logger = logging.getLogger("orion.odyssey.scheduler")


async def sync_bets() -> None:
    """Sync bets from connected providers (Polymarket, etc.)."""
    bus = get_core_event_bus()
    try:
        bus.publish("odyssey:bet:sync:started")
        # TODO: iterate providers, fetch recent bets, upsert into DB
        bus.publish("odyssey:bet:sync:completed")
        logger.info("Bet sync completed")
    except Exception as exc:
        logger.error("Bet sync failed: %s", exc)
        bus.publish("odyssey:bet:sync:failed", error=str(exc))


async def calculate_analytics() -> None:
    """Recalculate all analytics metrics."""
    bus = get_core_event_bus()
    try:
        bus.publish("odyssey:analytics:recalculated")
        # TODO: recalculate ROI, EV, CLV, win rate across all bets
        logger.info("Analytics recalculated")
    except Exception as exc:
        logger.error("Analytics recalculation failed: %s", exc)
