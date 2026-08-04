"""Opportunity Feedback API — record and retrieve feedback for personalized scoring.

Endpoints:
- POST /api/opportunity-feedback/record — record acceptance/rejection for an opportunity
- GET /api/opportunity-feedback/summary — get feedback statistics
- GET /api/opportunity-feedback/multipliers — get personalized multipliers for context
"""

from __future__ import annotations

from logging import getLogger
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.opportunity.engine import get_engine

router = APIRouter(prefix="/api/opportunity-feedback", tags=["opportunity-feedback"])
engine = get_engine()
logger = getLogger(__name__)


class FeedbackRequest(BaseModel):
    """Request model for recording feedback."""

    opportunity_id: str = Field(..., description="ID of the opportunity")
    outcome: str = Field(..., description="Outcome: accepted, rejected, or skipped")
    category: str = Field(..., description="Category of the opportunity")
    platform: str = Field(..., description="Platform/source name")
    technology_tags: list[str] = Field(default_factory=list, description="Technology tags")
    estimated_payout: float = Field(default=0.0, description="Estimated payout amount")
    actual_payout: float = Field(default=0.0, description="Actual payout received")
    reasoning: str = Field(default="", description="User reasoning for the decision")


class MultipliersRequest(BaseModel):
    """Request model for getting personalized multipliers."""

    category: str = Field(..., description="Category of the opportunity")
    platform: str = Field(..., description="Platform/source name")
    technology_tags: list[str] = Field(default_factory=list, description="Technology tags")


@router.post("/record")
def record_feedback(request: FeedbackRequest) -> dict[str, Any]:
    """Record feedback for an opportunity to learn from user decisions."""
    try:
        # Validate outcome
        valid_outcomes = {"accepted", "rejected", "skipped"}
        if request.outcome.lower() not in valid_outcomes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid outcome. Must be one of: {', '.join(valid_outcomes)}",
            )

        engine.record_feedback(
            opportunity_id=request.opportunity_id,
            outcome=request.outcome,
            category=request.category,
            platform=request.platform,
            technology_tags=request.technology_tags,
            estimated_payout=request.estimated_payout,
            actual_payout=request.actual_payout,
            reasoning=request.reasoning,
        )

        return {
            "status": "ok",
            "opportunity_id": request.opportunity_id,
            "outcome": request.outcome,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to record feedback: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/summary")
def get_feedback_summary() -> dict[str, Any]:
    """Get summary statistics of all feedback data."""
    try:
        return engine.get_feedback_summary()
    except Exception as e:
        logger.error("Failed to get feedback summary: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/multipliers")
def get_feedback_multipliers(request: MultipliersRequest) -> dict[str, float]:
    """Get personalized multipliers for a specific opportunity context."""
    try:
        return engine.get_feedback_multipliers(
            category=request.category,
            platform=request.platform,
            technology_tags=request.technology_tags,
        )
    except Exception as e:
        logger.error("Failed to get feedback multipliers: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
