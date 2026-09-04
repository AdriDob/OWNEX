"""Training Pipeline API Router — Skill gap → training content."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from cores.learning.training_pipeline import (
    generate_training_plan,
    get_training_plan,
    get_training_progress,
    list_exercises,
    list_resources,
    record_training_completion,
)

logger = logging.getLogger("ownex.api.training_pipeline")

router = APIRouter(prefix="/api/training", tags=["training-pipeline"])


@router.post("/plan")
async def create_training_plan(
    skill: str,
    category: str,
    current_level: str = Query("beginner"),
    target_level: str = Query("intermediate"),
    hours_per_week: float = Query(10.0),
) -> dict[str, Any]:
    """Generate a training plan for a skill gap."""
    return generate_training_plan(skill, category, current_level, target_level)


@router.get("/plan")
async def get_plan(
    skill: str = Query(...),
    category: str = Query(...),
) -> dict[str, Any]:
    """Get a saved training plan."""
    plan = get_training_plan(skill, category)
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")
    return plan


@router.post("/completion")
async def record_completion(
    skill: str,
    exercise_id: str,
    success: bool,
    notes: str = "",
) -> dict[str, Any]:
    """Record exercise completion."""
    return record_training_completion(skill, exercise_id, success, notes)


@router.get("/progress")
async def get_progress(
    skill: str = Query(...),
) -> dict[str, Any]:
    """Get training progress for a skill."""
    return get_training_progress(skill)


@router.get("/resources")
async def get_resources(
    skill: str | None = Query(None),
) -> dict[str, Any]:
    """List available training resources."""
    return list_resources(skill)


@router.get("/exercises")
async def get_exercises(
    skill: str | None = Query(None),
) -> dict[str, Any]:
    """List available training exercises."""
    return list_exercises(skill)


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """Get training pipeline statistics."""
    from cores.learning.training_pipeline import EXERCISE_TEMPLATES, RESOURCE_CATALOG

    total_resources = sum(len(v) for v in RESOURCE_CATALOG.values())
    total_exercises = sum(len(v) for v in EXERCISE_TEMPLATES.values())
    skills_with_resources = len(RESOURCE_CATALOG)
    skills_with_exercises = len(EXERCISE_TEMPLATES)

    return {
        "total_resources": total_resources,
        "total_exercises": total_exercises,
        "skills_with_resources": skills_with_resources,
        "skills_with_exercises": skills_with_exercises,
        "resource_categories": list(RESOURCE_CATALOG.keys()),
        "exercise_skills": list(EXERCISE_TEMPLATES.keys()),
    }
