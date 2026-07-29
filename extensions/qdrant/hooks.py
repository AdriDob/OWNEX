from __future__ import annotations

import logging

from core.extension.hooks import on_hook

LOG = logging.getLogger("ownex.qdrant")


@on_hook("after_startup")
def qdrant_startup(apps_count: int, **context) -> None:
    LOG.info("Qdrant: memory system ready (apps: %d)", apps_count or 0)


@on_hook("before_ai_reasoning")
def qdrant_context(prompt: str, **context) -> dict | None:
    return {"memory_source": "qdrant", "semantic_context": True}
