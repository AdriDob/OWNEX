from __future__ import annotations

import logging

logger = logging.getLogger("ownex.lightrag")

try:
    from lightrag import LightRAG as LightRAGClient
    from lightrag.llm import openai_complete, openai_embedding

    _LIGHTRAG_AVAILABLE = True
except ImportError:
    _LIGHTRAG_AVAILABLE = False
    logger.warning("lightrag not installed — LightRAG memory extension disabled")
