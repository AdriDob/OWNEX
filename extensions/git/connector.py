from __future__ import annotations

from core.interfaces.connector import IConnector, ConnectorHealth


class GitConnector(IConnector):
    connector_id = "git_adapter"
    app_id = "ownex"
    display_name = "Git Automation"

    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> bool:
        if not _GIT_AVAILABLE:
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return [
            {"key": "git_auto_commit", "label": "Auto commit", "type": "text", "default": "true"},
            {"key": "git_branch", "label": "Working branch", "type": "text", "default": "ownex/agent"},
        ]
