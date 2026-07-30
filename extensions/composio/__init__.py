from __future__ import annotations

import logging

logger = logging.getLogger("ownex.composio")

try:
    from composio import ComposioToolSet

    _COMPOSIO_AVAILABLE = True
except ImportError:
    _COMPOSIO_AVAILABLE = False
    logger.warning("composio-core not installed — Composio extension disabled")
