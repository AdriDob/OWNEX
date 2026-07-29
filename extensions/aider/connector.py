from __future__ import annotations

from core.interfaces.connector import IConnector, ConnectorHealth


class AiderConnector(IConnector):
    connector_id = "aider_editor"
    app_id = "ownex"
    display_name = "Aider Code Editor"

    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> bool:
        if not _AIDER_AVAILABLE:
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return [
            {"key": "aider_model", "label": "Model", "type": "text", "default": "gpt-4o"},
            {"key": "aider_auto_commit", "label": "Auto commit", "type": "text", "default": "false"},
        ]
