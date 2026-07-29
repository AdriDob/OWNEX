from __future__ import annotations

import logging

logger = logging.getLogger("ownex.aider")

try:
    import aider

    _AIDER_AVAILABLE = True
except ImportError:
    _AIDER_AVAILABLE = False
    logger.warning("aider not installed — plugin disabled")
