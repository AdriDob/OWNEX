from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from cores.bounty_scraper.scraper import BountyScraper

logger = logging.getLogger("cateye.bounty_scraper.monitor")


class DiscoveryMonitor:
    """Background monitor that periodically discovers new bounty programs."""

    def __init__(self, interval_hours: int = 24):
        self._interval = interval_hours * 3600
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_check = 0.0
        self._check_count = 0
        self._scraper = BountyScraper()

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Discovery monitor started (interval=%dh)", self._interval // 3600)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Discovery monitor stopped")

    async def _loop(self):
        await asyncio.sleep(5)  # delay first run so startup completes first
        while self._running:
            try:
                programs = await asyncio.to_thread(self._scraper.scrape_all, domains=[])
                new_count = sum(1 for p in programs if p.is_new)
                logger.info(
                    "Discovery: %d programs found (%d new)",
                    len(programs), new_count,
                )
                self._last_check = time.time()
                self._check_count += 1
            except Exception as e:
                logger.error("Discovery monitor check failed: %s", e)
            await asyncio.sleep(self._interval)

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "interval_hours": self._interval // 3600,
            "last_check": datetime.fromtimestamp(self._last_check, tz=timezone.utc).isoformat()
            if self._last_check > 0
            else "",
            "check_count": self._check_count,
        }


_MONITOR: DiscoveryMonitor | None = None


def get_discovery_monitor() -> DiscoveryMonitor:
    global _MONITOR
    if _MONITOR is None:
        _MONITOR = DiscoveryMonitor()
    return _MONITOR
