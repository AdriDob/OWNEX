from __future__ import annotations

import logging

from core.extension.hooks import on_hook

LOG = logging.getLogger("ownex.playwright")


@on_hook("before_scan")
def before_scan_web(target_id: str, scan_type: str, **context) -> bool | None:
    if scan_type not in ("web", "full", "recon"):
        return None
    LOG.info("Playwright sensor: preparing to scan target %s", target_id)
    return None


@on_hook("after_scan")
def after_scan_web(target_id: str, findings_count: int, **context) -> None:
    LOG.info("Playwright sensor: scan complete for %s (%d findings)", target_id, findings_count or 0)


@on_hook("before_ai_reasoning")
def before_ai_reasoning_web(prompt: str, tools: list, **context) -> dict | None:
    return {"sensor_source": "playwright", "context_built": True}
