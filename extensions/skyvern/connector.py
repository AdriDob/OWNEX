from __future__ import annotations

import logging
import os

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.skyvern.connector")

try:
    from skyvern import SkyvernClient

    _SKYVERN_AVAILABLE = True
except ImportError:
    _SKYVERN_AVAILABLE = False
    SkyvernClient = None  # type: ignore[assignment]


class SkyvernSensorConnector(IConnector):
    """AI-powered browser automation connector via Skyvern.

    Uses vision + LLM to navigate any website, fill forms, and
    extract structured data — no brittle selectors needed.
    """

    connector_id = "skyvern_sensor"
    app_id = "ownex"
    display_name = "Skyvern Browser AI"

    def __init__(self) -> None:
        self._connected = False
        self._client: SkyvernClient | None = None
        self._api_key: str = ""

    async def connect(self) -> bool:
        if not _SKYVERN_AVAILABLE:
            logger.warning("skyvern package not installed")
            return False
        try:
            self._api_key = os.environ.get("SKYVERN_API_KEY", "")
            if not self._api_key:
                logger.warning("SKYVERN_API_KEY not set — using local mode")
            self._client = SkyvernClient(api_key=self._api_key) if self._api_key else SkyvernClient()
            self._connected = True
            logger.info("Skyvern connected")
            return True
        except Exception as exc:
            logger.error("Skyvern connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._client = None
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connected=self._connected,
            error=None if self._connected else "client not initialized",
        )

    def get_config_fields(self) -> list[dict]:
        return [
            {
                "key": "skyvern_api_key",
                "label": "Skyvern API Key (optional, local mode if empty)",
                "type": "text",
            },
        ]

    async def navigate(self, url: str, goal: str = "") -> dict:
        """Navigate to a URL with an AI goal."""
        if not self._client:
            return {"error": "not connected"}
        try:
            result = await self._client.navigate(url, goal=goal)
            return result or {}
        except Exception as exc:
            logger.error("Skyvern navigate failed: %s", exc)
            return {"error": str(exc)}

    async def extract(self, url: str, fields: list[str] | None = None) -> dict:
        """Extract structured data from a page."""
        if not self._client:
            return {"error": "not connected"}
        try:
            result = await self._client.extract(url, fields=fields or [])
            return result or {}
        except Exception as exc:
            logger.error("Skyvern extract failed: %s", exc)
            return {"error": str(exc)}

    async def monitor(self, url: str, selector: str = "") -> dict:
        """Monitor a page for visual/structural changes."""
        if not self._client:
            return {"error": "not connected"}
        try:
            result = await self._client.monitor(url, selector=selector)
            return result or {}
        except Exception as exc:
            logger.error("Skyvern monitor failed: %s", exc)
            return {"error": str(exc)}
