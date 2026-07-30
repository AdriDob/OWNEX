from __future__ import annotations

import logging
import os

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.composio.connector")

try:
    from composio import ComposioToolSet

    _COMPOSIO_AVAILABLE = True
except ImportError:
    _COMPOSIO_AVAILABLE = False
    ComposioToolSet = None  # type: ignore[assignment]


class ComposioConnector(IConnector):
    """Connector to Composio toolkit platform.

    Provides 1000+ integrated tools with managed authentication,
    enabling OWNEX agents to interact with external platforms
    without implementing individual integrations.
    """

    connector_id = "composio_toolset"
    app_id = "ownex"
    display_name = "Composio Toolkits"

    def __init__(self) -> None:
        self._connected = False
        self._toolset: ComposioToolSet | None = None
        self._api_key: str = ""

    async def connect(self) -> bool:
        if not _COMPOSIO_AVAILABLE:
            logger.warning("composio-core not installed")
            return False
        try:
            self._api_key = os.environ.get("COMPOSIO_API_KEY", "")
            if not self._api_key:
                logger.warning("COMPOSIO_API_KEY not set — Composio may be limited")
            self._toolset = ComposioToolSet(api_key=self._api_key) if self._api_key else ComposioToolSet()
            self._connected = True
            logger.info("Composio connected")
            return True
        except Exception as exc:
            logger.error("Composio connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._toolset = None
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connected=self._connected,
            error=None if self._connected else "client not initialized",
        )

    def get_config_fields(self) -> list[dict]:
        return [
            {
                "key": "composio_api_key",
                "label": "Composio API Key",
                "type": "text",
            },
        ]

    async def get_tools(self, apps: list[str] | None = None) -> list[dict]:
        """Get available tools, optionally filtered by app."""
        if not self._toolset:
            return []
        try:
            tools = self._toolset.get_tools(apps=apps)
            return tools if isinstance(tools, list) else []
        except Exception as exc:
            logger.error("Composio get_tools failed: %s", exc)
            return []

    async def execute_action(self, action: str, params: dict | None = None) -> dict:
        """Execute a specific action via Composio."""
        if not self._toolset:
            return {"error": "not connected"}
        try:
            result = self._toolset.execute_action(action, params=params or {})
            return result or {}
        except Exception as exc:
            logger.error("Composio execute_action failed: %s", exc)
            return {"error": str(exc)}

    async def list_apps(self) -> list[str]:
        """List all available app integrations."""
        if not self._toolset:
            return []
        try:
            return self._toolset.get_apps()
        except Exception as exc:
            logger.error("Composio list_apps failed: %s", exc)
            return []


async def on_agent_action(event: object) -> None:
    if not _COMPOSIO_AVAILABLE:
        return
    action = getattr(event, "action", "") or ""
    params = getattr(event, "params", None) or {}
    if action:
        connector = ComposioConnector()
        await connector.connect()
        result = await connector.execute_action(action, params)
        if result and hasattr(event, "set_result"):
            event.set_result(result)


async def on_tool_discovery(event: object) -> None:
    if not _COMPOSIO_AVAILABLE:
        return
    connector = ComposioConnector()
    await connector.connect()
    apps = getattr(event, "apps", None)
    tools = await connector.get_tools(apps=apps)
    if tools and hasattr(event, "set_result"):
        event.set_result(tools)
