from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from core.opportunity import PersonalHistoryTracker, Top5Engine

logger = logging.getLogger("ownex.opportunity.api")

router = APIRouter(prefix="/api/opportunity-score", tags=["opportunity-score"])

_TOP5_ENGINE = Top5Engine()
_HISTORY_TRACKER = PersonalHistoryTracker()


@router.get("/top5")
def get_top5() -> dict[str, Any]:
    _HISTORY_TRACKER.get_history()
    result = _TOP5_ENGINE.compute([])
    return result.to_dict()
