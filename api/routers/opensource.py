"""Open Source Work API Router.

Provides endpoints for open source work categories and recommendations.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.opensource import get_category_manager, get_contribution_tracker
from cores.opensource.categories import OpenSourceCategory

logger = logging.getLogger("ownex.api.opensource")

router = APIRouter(prefix="/opensource", tags=["opensource"])


class CategoryRecommendationRequest(BaseModel):
    """Request for category recommendations."""

    skills: list[str]
    platforms: list[str] | None = None


class CategoryRecommendationResponse(BaseModel):
    """Response for category recommendations."""

    category: str
    score: float
    name: str
    description: str
    skills: list[str]
    platforms: list[str]


class ContributionRequest(BaseModel):
    """Request to add a contribution."""

    project: str
    issue_id: int
    title: str
    category: str
    status: str = "completed"


@router.get("/categories")
async def list_categories() -> dict[str, Any]:
    """List all available open source work categories."""
    manager = get_category_manager()
    categories = manager.list_categories()

    return {
        "categories": [
            {
                "id": cat.value,
                "name": manager.get_category_info(cat).get("name"),
                "description": manager.get_category_info(cat).get("description"),
                "skills": manager.get_category_info(cat).get("skills"),
                "platforms": manager.get_category_info(cat).get("platforms"),
            }
            for cat in categories
        ],
    }


@router.post("/recommendations", response_model=list[CategoryRecommendationResponse])
async def get_recommendations(request: CategoryRecommendationRequest) -> list[CategoryRecommendationResponse]:
    """Get category recommendations based on skills and platform preferences."""
    manager = get_category_manager()

    try:
        # Convert category strings to enums
        recommended = manager.recommend_category(request.skills, request.platforms)

        responses = []
        for category, score in recommended:
            info = manager.get_category_info(category)
            responses.append(
                CategoryRecommendationResponse(
                    category=category.value,
                    score=score,
                    name=info.get("name"),
                    description=info.get("description"),
                    skills=info.get("skills"),
                    platforms=info.get("platforms"),
                )
            )

        return responses

    except Exception as e:
        logger.error(f"[OPENSOURCE] Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/contributions")
async def get_contributions(project: str | None = None) -> dict[str, Any]:
    """Get contributions, optionally filtered by project."""
    tracker = get_contribution_tracker()
    contributions = tracker.get_contributions(project)

    return {
        "contributions": contributions,
        "stats": tracker.get_contribution_stats(),
    }


@router.post("/contributions")
async def add_contribution(request: ContributionRequest) -> dict[str, Any]:
    """Add a contribution record."""
    tracker = get_contribution_tracker()

    try:
        # Convert category string to enum
        category = OpenSourceCategory(request.category)

        tracker.add_contribution(
            project=request.project,
            issue_id=request.issue_id,
            title=request.title,
            category=category,
            status=request.status,
        )

        return {
            "success": True,
            "message": "Contribution added successfully",
        }

    except ValueError as e:
        logger.error(f"[OPENSOURCE] Invalid category: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid category: {request.category}") from None
    except Exception as e:
        logger.error(f"[OPENSOURCE] Error adding contribution: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/stats")
async def get_contribution_stats() -> dict[str, Any]:
    """Get contribution statistics."""
    tracker = get_contribution_tracker()
    return tracker.get_contribution_stats()
