from __future__ import annotations

import importlib.util
import logging

logger = logging.getLogger("ownex.graphify")

_GRAPHIFY_AVAILABLE = importlib.util.find_spec("graphify") is not None

if not _GRAPHIFY_AVAILABLE:
    logger.warning("graphify not installed — Graphify code intelligence extension disabled")
