from __future__ import annotations

import logging

logger = logging.getLogger("ownex.git")

try:
    import git as gitlib

    _GIT_AVAILABLE = True
except ImportError:
    _GIT_AVAILABLE = False
    logger.warning("GitPython not installed — plugin disabled")
