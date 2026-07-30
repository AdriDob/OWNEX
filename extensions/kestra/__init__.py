from __future__ import annotations

import logging

logger = logging.getLogger("ownex.kestra")

try:
    import httpx

    _KESTRA_AVAILABLE = True
except ImportError:
    _KESTRA_AVAILABLE = False
    logger.warning("httpx not installed — Kestra extension disabled")
