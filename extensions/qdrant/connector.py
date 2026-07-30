"""Qdrant connector — optional dependency guard."""

from __future__ import annotations

# Soft import guard
try:
    from qdrant_client import QdrantClient  # noqa: F401
    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False

from core.interfaces.connector import ConnectorHealth, IConnector


class QdrantConnector(IConnector):
    connector_id = "qdrant_vector"
    app_id = "ownex"
    display_name = "Qdrant Vector DB"

    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> bool:
        if not _QDRANT_AVAILABLE:
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return [
            {"key": "qdrant_url", "label": "Qdrant URL", "type": "text", "default": "http://localhost:6333"},
            {"key": "collection_name", "label": "Collection", "type": "text", "default": "vectors"},
            {"key": "vector_size", "label": "Vector size", "type": "text", "default": "768"},
        ]
