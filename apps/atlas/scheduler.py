"""ATLAS scheduler jobs — price sync, rebalance checks."""

from __future__ import annotations

import logging

from core.events.event_bus import get_core_event_bus

logger = logging.getLogger("orion.atlas.scheduler")


async def sync_prices() -> None:
    """Sync current prices for all tracked assets.

    This is a placeholder — real implementation will call providers.
    """
    bus = get_core_event_bus()
    try:
        # TODO: iterate assets, fetch price from provider, update DB
        bus.publish("atlas:price:sync:started")
        logger.info("Price sync started")
        bus.publish("atlas:price:sync:completed")
    except Exception as exc:
        logger.error("Price sync failed: %s", exc)
        bus.publish("atlas:price:sync:failed", error=str(exc))


async def check_rebalance() -> None:
    """Check if any portfolio needs rebalancing.

    Placeholder — will compare current allocation vs target.
    """
    bus = get_core_event_bus()
    try:
        bus.publish("atlas:rebalance:check:started")
        # TODO: implement rebalance logic
        bus.publish("atlas:rebalance:check:completed")
    except Exception as exc:
        logger.error("Rebalance check failed: %s", exc)
