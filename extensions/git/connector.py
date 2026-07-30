"""Git connector — optional dependency guard."""

from __future__ import annotations

# Soft import guard
try:
    import git  # noqa: F401

    _GIT_AVAILABLE = True
except ImportError:
    _GIT_AVAILABLE = False

from core.interfaces.connector import ConnectorHealth, IConnector


class GitConnector(IConnector):
    connector_id = "git_integration"
    app_id = "ownex"
    display_name = "Git Integration"

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
            {"key": "repo_path", "label": "Repository path", "type": "text", "default": "."},
            {"key": "auto_sync", "label": "Auto sync", "type": "text", "default": "true"},
            {"key": "branch", "label": "Branch", "type": "text", "default": "main"},
        ]
