from __future__ import annotations

import logging
import os
from pathlib import Path

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.cognee.connector")

try:
    import cognee  # noqa: F401

    _COGNEE_AVAILABLE = True
    CogneeClient = object  # cognee is module-level, no explicit client class needed
except ImportError:
    _COGNEE_AVAILABLE = False
    CogneeClient = None  # type: ignore[assignment]


class CogneeConnector(IConnector):
    """Connector to Cognee AI Memory platform.

    Cognee provides a cognitive architecture combining:
    - Knowledge graphs for relationships
    - Vector stores for semantic search
    - Automatic memory consolidation
    """

    connector_id = "cognee_memory"
    app_id = "ownex"
    display_name = "Cognee AI Memory"

    def __init__(self) -> None:
        self._connected = False
        self._data_dir: str = ""

    async def connect(self) -> bool:
        if not _COGNEE_AVAILABLE:
            logger.warning("cognee package not installed")
            return False

        try:
            data_dir = os.environ.get(
                "OWNEX_COGNEE_DIR",
                str(Path.home() / ".ownex" / "memory" / "cognee"),
            )
            Path(data_dir).mkdir(parents=True, exist_ok=True)
            self._data_dir = data_dir

            import cognee
            from cognee import config as cognee_config

            cognee_config.data_root_dir = data_dir
            await cognee.initialize()

            self._connected = True
            logger.info("Cognee connected at %s", data_dir)
            return True
        except Exception as exc:
            logger.error("Cognee connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connected=self._connected,
            error=None if self._connected else "not initialized",
        )

    def get_config_fields(self) -> list[dict]:
        return [
            {
                "key": "cognee_dir",
                "label": "Cognee data directory",
                "type": "text",
                "default": "~/.ownex/memory/cognee",
            },
        ]

    async def add(self, text: str, metadata: dict | None = None) -> bool:
        """Add text to Cognee memory."""
        if not _COGNEE_AVAILABLE:
            return False
        try:
            import cognee

            await cognee.add(text, metadata=metadata or {})
            return True
        except Exception as exc:
            logger.error("Cognee add failed: %s", exc)
            return False

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search Cognee memory."""
        if not _COGNEE_AVAILABLE:
            return []
        try:
            import cognee

            results = await cognee.search(query, limit=limit)
            return results if isinstance(results, list) else []
        except Exception as exc:
            logger.error("Cognee search failed: %s", exc)
            return []


async def on_memory_store(event: object) -> None:
    if not _COGNEE_AVAILABLE:
        return
    text = getattr(event, "text", None) or str(getattr(event, "data", ""))
    if text:
        connector = CogneeConnector()
        await connector.connect()
        await connector.add(text)


async def on_memory_retrieve(event: object) -> None:
    if not _COGNEE_AVAILABLE:
        return
    query = getattr(event, "query", "") or str(getattr(event, "data", ""))
    if query:
        connector = CogneeConnector()
        await connector.connect()
        results = await connector.search(query)
        if results and hasattr(event, "set_result"):
            event.set_result(results)
