"""Opportunity API — scoring and retrieval for OWNEX Opportunity Engine.

Endpoints:
- GET /api/opportunities/top5 — top 5 diversified opportunities across domains
- POST /api/opportunities/feedback — record acceptance/rejection to update scoring
"""

from __future__ import annotations

from logging import getLogger

from fastapi import APIRouter, HTTPException

from core.opportunity.scoring import FeedbackOutcome, get_engine

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

logger = getLogger(__name__)


@router.get("/top5")
def get_top5():
    """Get top opportunities, diversified by domain."""
    try:
        results = get_engine().get_top5_by_domain(limit=100)
        return {
            row.domain: [{"id": e.opportunity_id, "title": e.title, "score": e.final_score} for e in row.entries]
            for row in results
        }
    except Exception as e:
        logger.error("Failed to fetch opportunities top5: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/feedback")
def record_feedback(body: dict[str, str]):
    """Accept or reject an opportunity to learn from user feedback."""
    try:
        finding_id = int(body.get("finding_id"))
        outcome_str = body.get("outcome")
        if outcome_str not in {"accept", "reject"}:
            raise HTTPException(status_code=400, detail="Invalid outcome. Use 'accept' or 'reject'.")
        outcome = FeedbackOutcome(outcome_str)
        get_engine().record_feedback(finding_id, outcome)
        return {"status": "ok", "finding_id": finding_id, "outcome": outcome.value}
    except Exception as e:
        logger.error("Failed to record feedback: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
