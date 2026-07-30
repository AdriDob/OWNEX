from __future__ import annotations

import logging

logger = logging.getLogger("ownex.crawl4ai")

try:
    import crawl4ai

    _CRAWL4AI_AVAILABLE = True
except ImportError:
    _CRAWL4AI_AVAILABLE = False
    logger.warning("crawl4ai not installed — Crawl4AI sensor extension disabled")
