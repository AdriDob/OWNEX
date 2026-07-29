from __future__ import annotations

import logging

logger = logging.getLogger("ownex.qdrant")

try:
    from qdrant_client import QdrantClient
    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not installed — plugin disabled")
