"""API Router for Enhanced Personalization."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from cores.setup.steps.enhanced_personalization import (
    EnhancedPersonalizationSystem,
    get_enhanced_personalization_system,
    reset_enhanced_personalization_system,
)

router = APIRouter(prefix="/enhanced-personalization", tags=["enhanced-personalization"])


@router.get("/steps")
async def get_wizard_steps():
    """Get all wizard steps."""
    system = get_enhanced_personalization_system()
    steps = system.get_onboarding_steps()

    return {
        "steps": [
            {
                "step_id": step.step_id,
                "title": step.title,
                "description": step.description,
                "questions": step.questions,
                "is_required": step.is_required,
                "can_skip": step.can_skip,
            }
            for step in steps
        ]
    }


@router.post("/step")
async def process_step(payload: dict[str, Any]):
    """Process a wizard step."""
    system = get_enhanced_personalization_system()

    step_id = payload.get("step_id")
    answers = payload.get("answers", {})

    if not step_id:
        raise HTTPException(status_code=400, detail="step_id is required")

    success = system.process_step_answers(step_id, answers)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to process step")

    return {
        "success": True,
        "step_id": step_id,
        "profile": system.profile.__dict__,
    }


@router.post("/complete")
async def complete_wizard():
    """Complete the wizard and initialize the system."""
    system = get_enhanced_personalization_system()

    if not system.profile.completed_onboarding:
        raise HTTPException(status_code=400, detail="Wizard not completed")

    # Initialize system based on profile
    # This would trigger various initializations
    # - Obsidian integration
    # - Voice commands setup
    # - Daily planning system
    # - Onboarding completion

    return {
        "success": True,
        "message": "Wizard completed successfully",
        "profile": system.profile.__dict__,
        "next_steps": [
            "Review your daily plan",
            "Explore the dashboard",
            "Check voice commands",
            "Review Obsidian integration",
        ],
    }


@router.get("/profile")
async def get_profile():
    """Get current user profile."""
    system = get_enhanced_personalization_system()
    return system.profile.__dict__


@router.get("/greeting")
async def get_greeting():
    """Get personalized greeting."""
    system = get_enhanced_personalization_system()
    return {
        "greeting": system.get_greeting(),
        "daily_plan_prompt": system.get_daily_plan_prompt(),
    }


@router.get("/obsidian-config")
async def get_obsidian_config():
    """Get Obsidian configuration."""
    system = get_enhanced_personalization_system()
    return system.get_obsidian_config()


@router.get("/daily-plan")
async def get_daily_plan():
    """Get daily plan based on profile."""
    system = get_enhanced_personalization_system()

    return {
        "prompt": system.get_daily_plan_prompt(),
        "work_hours": {
            "start": system.profile.work_hours_start,
            "end": system.profile.work_hours_end,
        },
        "work_days": system.profile.work_days,
        "daily_planning_enabled": system.profile.daily_planning_enabled,
        "daily_tasks_enabled": system.profile.daily_tasks_enabled,
    }


@router.post("/reset")
async def reset_personalization():
    """Reset personalization (for testing or re-onboarding)."""
    reset_enhanced_personalization_system()
    return {
        "success": True,
        "message": "Personalization reset successfully",
    }


@router.get("/is-first-time")
async def is_first_time_user():
    """Check if user is first-time user."""
    system = get_enhanced_personalization_system()
    return {
        "is_first_time": system.is_first_time_user(),
        "days_using": system.profile.days_using,
    }


@router.post("/increment-usage")
async def increment_usage_days():
    """Increment usage days counter."""
    system = get_enhanced_personalization_system()
    system.increment_usage_days()
    return {
        "success": True,
        "days_using": system.profile.days_using,
    }
