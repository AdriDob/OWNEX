from __future__ import annotations

import logging

logger = logging.getLogger("ownex.graphiti.hooks")

try:
    from extensions.graphiti import _GRAPHITI_AVAILABLE
except ImportError:
    _GRAPHITI_AVAILABLE = False


async def on_observation_ingested(event: object) -> None:
    if not _GRAPHITI_AVAILABLE:
        return
    from extensions.graphiti.connector import GraphitiConnector

    text = getattr(event, "text", None) or str(getattr(event, "data", ""))
    source = getattr(event, "source", "observation")
    if text:
        connector = GraphitiConnector()
        await connector.connect()
        await connector.add_observation(text, source=source)


async def on_relationship_query(event: object) -> None:
    if not _GRAPHITI_AVAILABLE:
        return
    from extensions.graphiti.connector import GraphitiConnector

    entity = getattr(event, "entity", "") or str(getattr(event, "data", ""))
    if entity:
        connector = GraphitiConnector()
        await connector.connect()
        results = await connector.query_relationships(entity)
        if results and hasattr(event, "set_result"):
            event.set_result(results)
