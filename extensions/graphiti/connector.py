from __future__ import annotations

import logging
import os
from pathlib import Path

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.graphiti.connector")

try:
    from graphiti import Graphiti as GraphitiClient

    _GRAPHITI_AVAILABLE = True
except ImportError:
    _GRAPHITI_AVAILABLE = False
    GraphitiClient = None  # type: ignore[assignment]


class GraphitiConnector(IConnector):
    """Connector to Graphiti real-time knowledge graph.

    Graphiti automatically builds and updates a knowledge graph from
    streaming observations, detecting entities, relationships, and
    temporal patterns without manual schema definition.
    """

    connector_id = "graphiti_kg"
    app_id = "ownex"
    display_name = "Graphiti Knowledge Graph"

    def __init__(self) -> None:
        self._connected = False
        self._client: GraphitiClient | None = None

    async def connect(self) -> bool:
        if not _GRAPHITI_AVAILABLE:
            logger.warning("graphiti package not installed")
            return False
        try:
            data_dir = os.environ.get(
                "OWNEX_GRAPHITI_DIR",
                str(Path.home() / ".ownex" / "memory" / "graphiti"),
            )
            Path(data_dir).mkdir(parents=True, exist_ok=True)

            self._client = GraphitiClient(data_dir=data_dir)
            self._connected = True
            logger.info("Graphiti connected at %s", data_dir)
            return True
        except Exception as exc:
            logger.error("Graphiti connect failed: %s", exc)
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
                "key": "graphiti_dir",
                "label": "Graphiti data directory",
                "type": "text",
                "default": "~/.ownex/memory/graphiti",
            },
        ]

    async def add_observation(self, text: str, source: str = "") -> bool:
        if not self._client:
            return False
        try:
            self._client.add_observation(text, source=source)
            return True
        except Exception as exc:
            logger.error("Graphiti add_observation failed: %s", exc)
            return False

    async def query_relationships(self, entity: str) -> list[dict]:
        if not self._client:
            return []
        try:
            results = self._client.query_relationships(entity)
            return results if isinstance(results, list) else []
        except Exception as exc:
            logger.error("Graphiti query failed: %s", exc)
            return []
