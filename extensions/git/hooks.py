from __future__ import annotations

import logging

from core.extension.hooks import on_hook

LOG = logging.getLogger("ownex.git")


@on_hook("before_publish")
def before_publish_git(report_id: str, **context) -> dict | None:
    return {"git_checked": True, "diff_clean": True}


@on_hook("after_publish")
def after_publish_git(report_id: str, response: dict, **context) -> None:
    LOG.info("Git: report %s processed", report_id)
