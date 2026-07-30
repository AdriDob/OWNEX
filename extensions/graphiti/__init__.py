from __future__ import annotations

import logging

logger = logging.getLogger("ownex.graphiti")

try:
    from graphiti import Graphiti

    _GRAPHITI_AVAILABLE = True
except ImportError:
    _GRAPHITI_AVAILABLE = False
    logger.warning("graphiti not installed — Graphiti extension disabled")
