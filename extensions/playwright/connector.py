from __future__ import annotations

import logging

from core.interfaces.connector import IConnector, ConnectorHealth

logger = logging.getLogger("ownex.playwright.connector")


class PlaywrightConnector(IConnector):
    connector_id = "playwright_sensor"
    app_id = "ownex"
    display_name = "Playwright Web Sensor"

    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> bool:
        try:
            from playwright.async_api import async_playwright

            self._pw = await async_playwright().start()
            self._connected = True
            return True
        except Exception as exc:
            logger.error("Playwright connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        if hasattr(self, "_pw"):
            await self._pw.stop()
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connected=self._connected,
            latency_ms=None,
            error=None if self._connected else "playwright not connected",
        )

    def get_config_fields(self) -> list[dict]:
        return [
            {"key": "playwright_headless", "label": "Headless mode", "type": "text", "default": "true"},
        ]
