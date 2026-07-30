from __future__ import annotations

import logging

logger = logging.getLogger("ownex.n8n")

try:
    import httpx

    _N8N_AVAILABLE = True
except ImportError:
    _N8N_AVAILABLE = False
    logger.warning("httpx not installed — n8n extension disabled")
