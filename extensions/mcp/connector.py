"""MCP connector — optional dependency guard."""

from __future__ import annotations

import logging

# Soft import guard
try:
    import mcp  # noqa: F401

    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger(__name__)


class MCPConnector(IConnector):
    connector_id = "mcp_protocol"
    app_id = "ownex"
    display_name = "MCP Protocol"

    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> bool:
        if not _MCP_AVAILABLE:
            logger.warning("MCP library not installed; run: pip install mcp")
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return [
            {"key": "mcp_host", "label": "Host", "type": "text", "default": "localhost"},
            {"key": "mcp_port", "label": "Port", "type": "text", "default": "9000"},
            {"key": "mcp_protocol", "label": "Protocol", "type": "text", "default": "tcp"},
        ]
