"""OWNEX Opportunity Score API — /api/opportunity-score/

Top 5 personalized recommendations using OWNEX scoring engine.
Data sourced from CATEYE Opportunity Intelligence Layer.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from core.opportunity import PersonalHistoryTracker, Top5Engine
from core.opportunity.adapter import adapt_opportunities
from cores.opportunity import get_engine as get_cateye_engine

logger = logging.getLogger("ownex.opportunity.api")

router = APIRouter(prefix="/api/opportunity-score", tags=["opportunity-score"])

_TOP5_ENGINE = Top5Engine()
_HISTORY_TRACKER = PersonalHistoryTracker()


def _get_scored_opportunities() -> list:
    """Fetch opportunities from CATEYE engine and adapt to OWNEX format."""
    try:
        cateye_engine = get_cateye_engine()
        if not cateye_engine.get_all():
            cateye_engine.discover_all()
        opportunities = cateye_engine.get_all()
        personal = _HISTORY_TRACKER.get_history()
        return adapt_opportunities(opportunities, personal)
    except Exception as exc:
        logger.warning("[OWNEX] Failed to fetch/adapt opportunities: %s", exc)
        return []


@router.get("/top5")
def get_top5() -> dict[str, Any]:
    """Get top 5 personalized opportunities."""
    scored = _get_scored_opportunities()
    result = _TOP5_ENGINE.compute(scored)
    return result.to_dict()
