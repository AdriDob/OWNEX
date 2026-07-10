"""Hello World extension — hook handlers."""

from __future__ import annotations

import logging

from core.extension.hooks import on_hook

logger = logging.getLogger("orion.ext.hello")


@on_hook("after_startup")
def on_startup(apps_count: int) -> None:
    """Log a greeting when the system starts."""
    logger.info("👋 Hello World! System started with %d apps", apps_count)
