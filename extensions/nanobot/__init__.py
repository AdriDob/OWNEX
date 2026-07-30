from __future__ import annotations

import logging

logger = logging.getLogger("ownex.nanobot")

try:
    from nanobot import Nanobot

    _NANOBOT_AVAILABLE = True
except ImportError:
    _NANOBOT_AVAILABLE = False
    logger.warning("nanobot not installed — Nanobot agent frontend extension disabled")
