from __future__ import annotations

from core.interfaces.connector import ConnectorHealth, IConnector


class MCPBridgeConnector(IConnector):
    connector_id = "mcp_bridge"
    app_id = "ownex"
    display_name = "MCP Bridge"

    def __init__(self) -> None:
        self._connected = False
        self._sessions: list[object] = []

    async def connect(self) -> bool:
        if not _MCP_AVAILABLE:
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return [
            {"key": "mcp_server_command", "label": "Server command", "type": "text"},
            {"key": "mcp_server_args", "label": "Server args (JSON)", "type": "text"},
        ]
