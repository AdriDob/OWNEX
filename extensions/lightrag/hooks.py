from __future__ import annotations

import logging

logger = logging.getLogger("ownex.lightrag.hooks")

try:
    from extensions.lightrag import _LIGHTRAG_AVAILABLE
except ImportError:
    _LIGHTRAG_AVAILABLE = False


async def on_memory_store(event: object) -> None:
    """Hook: store observations and facts into LightRAG graph."""
    if not _LIGHTRAG_AVAILABLE:
        return
    from extensions.lightrag.connector import LightRAGConnector

    text = getattr(event, "text", None) or str(getattr(event, "data", ""))
    source = getattr(event, "source", "memory_store")
    if text:
        connector = LightRAGConnector()
        await connector.connect()
        await connector.insert(text, source=source)


async def on_memory_retrieve(event: object) -> None:
    """Hook: retrieve graph-enriched context for a query."""
    if not _LIGHTRAG_AVAILABLE:
        return
    from extensions.lightrag.connector import LightRAGConnector

    query = getattr(event, "query", "") or str(getattr(event, "data", ""))
    if query:
        connector = LightRAGConnector()
        await connector.connect()
        result = await connector.query(query)
        if result and hasattr(event, "set_result"):
            event.set_result(result)


async def on_context_enrich(event: object) -> None:
    """Hook: enrich agent context with graph-retrieved knowledge."""
    if not _LIGHTRAG_AVAILABLE:
        return
    from extensions.lightrag.connector import LightRAGConnector

    query = getattr(event, "context_query", "") or str(getattr(event, "data", ""))
    if query:
        connector = LightRAGConnector()
        await connector.connect()
        enriched = await connector.query(query, mode="hybrid")
        if enriched and hasattr(event, "context"):
            event.context["lightrag"] = enriched
