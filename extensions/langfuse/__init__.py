from __future__ import annotations

import logging

logger = logging.getLogger("ownex.langfuse")

try:
    from langfuse import Langfuse

    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False
    logger.warning("langfuse not installed — Langfuse observability extension disabled")
