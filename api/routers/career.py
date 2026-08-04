"""Career Engine API router.

Exposes continuous learning: skill-gap detection, prioritized learning
roadmap, interview prep, and a daily training plan — all derived from the
real UserProfile. Feeds Mission Control so the user can see what to learn
next and why (closes the loop between opportunities and skill gaps).
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.routers.direct_work import _profile_from_dict
from cores.career_engine import CareerEngine
from cores.direct_work_engine.models import OpportunityCategory

logger = logging.getLogger("ownex.api.career")

router = APIRouter(prefix="/career", tags=["career"])

_engine = CareerEngine()

_CATEGORIES = {c.value: c for c in OpportunityCategory}


class ProfileRequest(BaseModel):
    """Request carrying a UserProfile (same shape as /direct-work)."""

    profile: dict[str, Any]
    categories: list[str] | None = Field(None, description="OpportunityCategory values to scope analysis")


class CategoryRequest(BaseModel):
    """Request for a single category."""

    category: str = Field(..., description="OpportunityCategory value (e.g. 'bug_bounty', 'backend')")


def _resolve_categories(values: list[str] | None) -> list[OpportunityCategory] | None:
    if values is None:
        return None
    resolved: list[OpportunityCategory] = []
    for value in values:
        cat = _CATEGORIES.get(value)
        if cat is None:
            valid = ", ".join(sorted(_CATEGORIES))
            raise HTTPException(
                status_code=422,
                detail=f"Invalid category '{value}'. Valid values: {valid}",
            )
        resolved.append(cat)
    return resolved


def _gap_dict(gap) -> dict[str, Any]:
    return {
        "skill": gap.skill,
        "category": gap.category.value,
        "priority": gap.priority,
    }


def _roadmap_dict(roadmap) -> dict[str, Any]:
    return {
        "items": [_gap_dict(g) for g in roadmap.items],
        "total_gaps": roadmap.total_gaps,
        "high_priority_gaps": [_gap_dict(g) for g in roadmap.high_priority],
        "generated_at": roadmap.generated_at,
    }


@router.get("/status")
async def career_status() -> dict[str, Any]:
    """Career Engine status and available endpoints."""
    return {
        "enabled": True,
        "engine": "career_engine",
        "categories_count": len(_CATEGORIES),
        "endpoints": [
            "GET  /career/analyze",
            "POST /career/roadmap",
            "POST /career/daily-training",
            "POST /career/interview",
            "POST /career/gaps",
        ],
    }


@router.post("/analyze")
async def career_analyze(request: ProfileRequest) -> dict[str, Any]:
    """Full career analysis for a profile: gaps, high-priority skills, top categories."""
    profile = _profile_from_dict(request.profile)
    return _engine.analyze_profile(profile)


@router.post("/roadmap")
async def career_roadmap(request: ProfileRequest) -> dict[str, Any]:
    """Prioritized learning roadmap (high-priority gaps first)."""
    profile = _profile_from_dict(request.profile)
    categories = _resolve_categories(request.categories)
    return _roadmap_dict(_engine.build_roadmap(profile, categories))


@router.post("/daily-training")
async def career_daily_training(request: ProfileRequest) -> dict[str, Any]:
    """Today's training plan: focus skills, drills, and interview questions."""
    profile = _profile_from_dict(request.profile)
    categories = _resolve_categories(request.categories)
    return asdict(_engine.build_daily_training(profile, categories))


@router.post("/interview")
async def career_interview(request: CategoryRequest) -> dict[str, Any]:
    """Curated interview questions for a category."""
    cats = _resolve_categories([request.category])
    assert cats is not None  # single literal category always resolves or raises 422
    cat = cats[0]
    questions = _engine.prepare_interview(cat)
    if not questions:
        raise HTTPException(status_code=404, detail=f"No interview questions for category '{request.category}'")
    return {"category": request.category, "questions": questions}


@router.post("/gaps")
async def career_gaps(request: ProfileRequest) -> dict[str, Any]:
    """Detect skill gaps across categories, scoped to the categories provided."""
    profile = _profile_from_dict(request.profile)
    categories = _resolve_categories(request.categories)
    gaps = _engine.detect_skill_gaps(profile, categories)
    return {
        "total_gaps": len(gaps),
        "high_priority": [_gap_dict(g) for g in gaps if g.priority == "high"],
        "gaps": [_gap_dict(g) for g in gaps],
    }
