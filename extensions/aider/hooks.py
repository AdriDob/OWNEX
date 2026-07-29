from __future__ import annotations

import logging

from core.extension.hooks import on_hook

LOG = logging.getLogger("ownex.aider")


@on_hook("before_validation")
def before_validation_aider(finding_ids: list, **context) -> dict | None:
    return {"aider_ready": True, "context": "validation_hook"}


@on_hook("after_report")
def after_report_aider(report_id: str, **context) -> None:
    LOG.info("Aider: report %s generated, ready for code suggestions", report_id)


@on_hook("before_ai_reasoning")
def before_ai_reasoning_aider(prompt: str, **context) -> dict | None:
    return {"editor_source": "aider", "code_context_built": True}
