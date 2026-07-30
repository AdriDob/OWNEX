from __future__ import annotations

import logging

logger = logging.getLogger("ownex.skyvern")

try:
    from skyvern import SkyvernClient

    _SKYVERN_AVAILABLE = True
except ImportError:
    _SKYVERN_AVAILABLE = False
    logger.warning("skyvern not installed — Skyvern sensor extension disabled")
