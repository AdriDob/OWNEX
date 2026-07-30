from __future__ import annotations

import logging

logger = logging.getLogger("ownex.skyvern.hooks")

try:
    from extensions.skyvern import _SKYVERN_AVAILABLE
except ImportError:
    _SKYVERN_AVAILABLE = False


async def on_sensor_fetch(event: object) -> None:
    """Hook: use Skyvern to fetch a web page as a sensor observation."""
    if not _SKYVERN_AVAILABLE:
        return
    from extensions.skyvern.connector import SkyvernSensorConnector

    url = getattr(event, "url", "") or getattr(event, "target", "")
    goal = getattr(event, "goal", "")
    if url:
        connector = SkyvernSensorConnector()
        await connector.connect()
        result = await connector.navigate(url, goal=goal)
        if result and hasattr(event, "set_result"):
            event.set_result(result)


async def on_web_observe(event: object) -> None:
    """Hook: observe a web page and extract structured data."""
    if not _SKYVERN_AVAILABLE:
        return
    from extensions.skyvern.connector import SkyvernSensorConnector

    url = getattr(event, "url", "") or getattr(event, "data", "")
    fields = getattr(event, "fields", None)
    if url:
        connector = SkyvernSensorConnector()
        await connector.connect()
        data = await connector.extract(url, fields=fields)
        if data and hasattr(event, "set_result"):
            event.set_result(data)
