"""API Router for Guided Onboarding."""

from typing import Any

from fastapi import APIRouter, HTTPException

from cores.onboarding.guided_system import (
    GuidedOnboardingSystem,
    LessonStatus,
    get_guided_onboarding_system,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/start")
async def start_onboarding():
    """Start guided onboarding."""
    system = get_guided_onboarding_system()
    progress = system.start_onboarding()
    return progress.__dict__


@router.get("/current-lesson")
async def get_current_lesson():
    """Get current onboarding lesson."""
    system = get_guided_onboarding_system()
    lesson = system.get_current_lesson()

    if not lesson:
        return {
            "message": "No current lesson available",
            "onboarding_complete": system.is_onboarding_complete(),
        }

    return {
        "lesson_id": lesson.lesson_id,
        "day": lesson.day.value,
        "title": lesson.title,
        "description": lesson.description,
        "content": lesson.content,
        "duration_minutes": lesson.duration_minutes,
        "status": lesson.status.value,
    }


@router.post("/lesson/{lesson_id}/complete")
async def complete_lesson(lesson_id: str, payload: dict[str, Any]):
    """Complete an onboarding lesson."""
    system = get_guided_onboarding_system()

    notes = payload.get("notes", "")
    success = system.complete_lesson(lesson_id, notes)

    if not success:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return {
        "success": True,
        "lesson_id": lesson_id,
        "notes": notes,
    }


@router.get("/summary")
async def get_onboarding_summary():
    """Get onboarding summary."""
    system = get_guided_onboarding_system()
    summary = system.get_onboarding_summary()
    return summary


@router.get("/is-complete")
async def is_onboarding_complete():
    """Check if onboarding is complete."""
    system = get_guided_onboarding_system()
    return {
        "is_complete": system.is_onboarding_complete(),
    }
