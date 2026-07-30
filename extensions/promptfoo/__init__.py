from __future__ import annotations

import logging

logger = logging.getLogger("ownex.promptfoo")

try:
    import promptfoo

    _PROMPTFOO_AVAILABLE = True
except ImportError:
    _PROMPTFOO_AVAILABLE = False
    logger.warning("promptfoo not installed — PromptFoo evaluation extension disabled")
