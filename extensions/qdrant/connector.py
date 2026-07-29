from __future__ import annotations

from core.interfaces.connector import IConnector, ConnectorHealth


class QdrantConnector(IConnector):
    connector_id = "qdrant_memory"
    app_id = "ownex"
    display_name = "Qdrant Vector Memory"

    def __init__(self) -> None:
        self._connected = False
        self._client: object = None

    async def connect(self) -> bool:
        if not _QDRANT_AVAILABLE:
            return False
        self._client = QdrantClient(url="http://localhost:6333", timeout=10)
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return [
            {"key": "qdrant_url", "label": "Qdrant URL", "type": "text", "default": "http://localhost:6333"},
        ]
