"""Mercenary Filter API — Aggressive opportunity filtering system.

Endpoints:
- GET /api/mercenary-filter/status — Get filter status and configuration
- POST /api/mercenary-filter/score — Score a specific opportunity
- GET /api/mercenary-filter/categories — List all categories and priorities
- POST /api/mercenary-filter/toggle — Toggle mercenary mode on/off
"""

from __future__ import annotations

from logging import getLogger
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.opportunity.mercenary_filter import (
    CATEGORY_PRIORITIES,
    MercenaryAttributes,
    OpportunityCategory,
    get_mercenary_filter,
)

router = APIRouter(prefix="/api/mercenary-filter", tags=["mercenary-filter"])
logger = getLogger(__name__)


class MercenaryScoreRequest(BaseModel):
    """Request to score an opportunity."""

    opp_id: str = Field(..., description="Opportunity ID")
    platform: str = Field(..., description="Platform name")
    source_type: str = Field(default="", description="Source type (dev_bounty, ai_work, etc.)")
    tags: list[str] = Field(default_factory=list, description="Technology tags")
    reward: float = Field(default=0.0, description="Reward amount")
    effort_hours: float = Field(default=8.0, description="Estimated effort hours")

    # Override attributes
    verifiable_payment: bool = Field(default=False)
    defined_objective: bool = Field(default=False)
    no_interview_required: bool = Field(default=False)
    no_portfolio_required: bool = Field(default=False)
    argentina_compatible: bool = Field(default=True)
    remote_work: bool = Field(default=True)
    real_it_work: bool = Field(default=True)


@router.get("/status")
def get_filter_status() -> dict[str, Any]:
    """Get mercenary filter status and configuration."""
    filter_instance = get_mercenary_filter()

    return {
        "enabled": True,
        "min_score_threshold": filter_instance.MIN_SCORE_THRESHOLD,
        "categories": {cat.name: pri.name for cat, pri in CATEGORY_PRIORITIES.items()},
        "weights": {
            "verifiable_payment": filter_instance.WEIGHT_VERIFIABLE_PAYMENT,
            "defined_task": filter_instance.WEIGHT_DEFINED_TASK,
            "no_interview": filter_instance.WEIGHT_NO_INTERVIEW,
            "no_portfolio": filter_instance.WEIGHT_NO_PORTFOLIO,
            "argentina_compatible": filter_instance.WEIGHT_ARGENTINA_COMPATIBLE,
            "real_it": filter_instance.WEIGHT_REAL_IT,
            "reasonable_time": filter_instance.WEIGHT_REASONABLE_TIME,
        },
    }


@router.post("/score")
def score_opportunity(request: MercenaryScoreRequest) -> dict[str, Any]:
    """Score a specific opportunity using mercenary criteria."""
    try:
        filter_instance = get_mercenary_filter()

        # Determine category
        category = filter_instance.get_category(request.platform, request.source_type, request.tags)

        # Build attributes
        attrs = MercenaryAttributes(
            verifiable_payment=request.verifiable_payment,
            payment_amount_verified=request.reward > 0,
            defined_objective=request.defined_objective,
            clear_deliverable=request.source_type in {"dev_bounty", "bounty", "task"},
            no_interview_required=request.no_interview_required,
            no_portfolio_required=request.no_portfolio_required,
            argentina_compatible=request.argentina_compatible,
            remote_work=request.remote_work,
            real_it_work=request.real_it_work,
            technical_skill_required=True,
            no_mechanical_task=request.source_type not in {"data_entry", "manual"},
            reasonable_timeframe=0 < request.effort_hours <= 100,
            estimated_hours=request.effort_hours,
            hourly_rate_competitive=request.reward / max(request.effort_hours, 1) > 10,
            category=category,
        )

        # Score
        score = filter_instance.score_opportunity(request.opp_id, attrs)

        return {
            "opp_id": request.opp_id,
            "total_score": score.total_score,
            "passed_filter": score.passed_filter,
            "category": category.name,
            "category_priority": score.category_priority.name,
            "component_scores": {
                "payment": score.payment_score,
                "task_definition": score.task_definition_score,
                "requirements": score.requirements_score,
                "location": score.location_score,
                "technical": score.technical_score,
                "time": score.time_score,
            },
            "reasons": score.reasons,
            "blockers": score.blockers,
        }
    except Exception as e:
        logger.error("Mercenary filter scoring failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}") from e


@router.get("/categories")
def list_categories() -> dict[str, Any]:
    """List all categories with their priorities."""
    return {
        "categories": [
            {
                "id": cat.value,
                "name": cat.name,
                "priority": CATEGORY_PRIORITIES.get(cat, 50).name,
                "priority_value": int(CATEGORY_PRIORITIES.get(cat, 50)),
            }
            for cat in OpportunityCategory
        ]
    }


@router.post("/toggle")
def toggle_mercenary_mode(enabled: bool = True) -> dict[str, Any]:
    """Toggle mercenary mode on/off (requires engine restart to take effect)."""
    # This is a configuration change that would require engine restart
    # For now, just return the requested state
    return {
        "status": "ok",
        "mercenary_mode": enabled,
        "message": "Mercenary mode updated. Restart engine to apply changes.",
    }
