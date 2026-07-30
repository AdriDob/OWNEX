from __future__ import annotations

import logging

logger = logging.getLogger("ownex.graphify")

import importlib.util

_GRAPHIFY_AVAILABLE = importlib.util.find_spec("graphify") is not None

if not _GRAPHIFY_AVAILABLE:
    logger.warning("graphify not installed — Graphify code intelligence extension disabled")
