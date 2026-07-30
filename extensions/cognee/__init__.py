from __future__ import annotations

import logging

logger = logging.getLogger("ownex.cognee")

try:
    import cognee

    _COGNEE_AVAILABLE = True
except ImportError:
    _COGNEE_AVAILABLE = False
    logger.warning("cognee not installed — Cognee memory extension disabled")
