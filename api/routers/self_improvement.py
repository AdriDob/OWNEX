"""Self-Improvement API — Auto-reflection and continuous learning system."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.self_improvement.plan_generator import get_plan_generator
from core.self_improvement.reflection import (
    IssueType,
    Severity,
    get_reflection_engine,
)

logger = logging.getLogger("ownex.api.self_improvement")

router = APIRouter(prefix="/api/self-improvement", tags=["self-improvement"])


class ReflectionRequest(BaseModel):
    context: str
    failure: str
    issue_type: str  # IssueType value
    severity: str  # Severity value
    metadata: dict[str, Any] | None = None


class ActionStatusRequest(BaseModel):
    action_id: str
    new_status: str


@router.post("/reflect")
def create_reflection(request: ReflectionRequest):
    """Create a new reflection about a failure/limitation."""
    try:
        engine = get_reflection_engine()
        reflection = engine.reflect(
            context=request.context,
            failure=request.failure,
            issue_type=IssueType(request.issue_type),
            severity=Severity(request.severity),
            metadata=request.metadata,
        )
        return {
            "success": True,
            "reflection": reflection.to_dict(),
        }
    except Exception as e:
        logger.error(f"Failed to create reflection: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/reflections")
def get_reflections(status: str | None = None):
    """Get all reflections, optionally filtered by status."""
    try:
        engine = get_reflection_engine()
        reflections = [r for r in engine._reflections if r.status == status] if status else engine._reflections
        return {
            "success": True,
            "reflections": [r.to_dict() for r in reflections],
            "total": len(reflections),
        }
    except Exception as e:
        logger.error(f"Failed to get reflections: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/reflections/pending")
def get_pending_reflections():
    """Get all pending reflections (not completed)."""
    try:
        engine = get_reflection_engine()
        pending = engine.get_pending_reflections()
        return {
            "success": True,
            "reflections": [r.to_dict() for r in pending],
            "total": len(pending),
        }
    except Exception as e:
        logger.error(f"Failed to get pending reflections: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/reflections/high-priority")
def get_high_priority_reflections(limit: int = 10):
    """Get highest priority pending reflections."""
    try:
        engine = get_reflection_engine()
        high_priority = engine.get_high_priority_reflections(limit)
        return {
            "success": True,
            "reflections": [r.to_dict() for r in high_priority],
            "total": len(high_priority),
        }
    except Exception as e:
        logger.error(f"Failed to get high priority reflections: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/reflections/{reflection_id}/status")
def update_reflection_status(reflection_id: str, new_status: str):
    """Update status of a reflection."""
    try:
        engine = get_reflection_engine()
        success = engine.update_reflection_status(reflection_id, new_status)
        if not success:
            raise HTTPException(status_code=404, detail="Reflection not found")
        return {
            "success": True,
            "reflection_id": reflection_id,
            "new_status": new_status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update reflection status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/plan")
def get_improvement_plan():
    """Get the current improvement plan."""
    try:
        engine = get_reflection_engine()
        plan = engine.generate_improvement_plan()
        return {
            "success": True,
            "plan": plan,
        }
    except Exception as e:
        logger.error(f"Failed to get improvement plan: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/plan/auto-generate")
def auto_generate_plan():
    """Auto-generate improvement plan from all pending reflections."""
    try:
        generator = get_plan_generator()
        result = generator.auto_generate_plan()
        return {
            "success": True,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Failed to auto-generate plan: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/actions")
def get_actions(status: str | None = None):
    """Get all improvement actions, optionally filtered by status."""
    try:
        generator = get_plan_generator()
        actions = [a for a in generator._actions if a.status == status] if status else generator._actions
        return {
            "success": True,
            "actions": [a.to_dict() for a in actions],
            "total": len(actions),
        }
    except Exception as e:
        logger.error(f"Failed to get actions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/actions/pending")
def get_pending_actions():
    """Get all pending improvement actions."""
    try:
        generator = get_plan_generator()
        pending = generator.get_pending_actions()
        return {
            "success": True,
            "actions": [a.to_dict() for a in pending],
            "total": len(pending),
        }
    except Exception as e:
        logger.error(f"Failed to get pending actions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/actions/high-priority")
def get_high_priority_actions(limit: int = 10):
    """Get highest priority pending actions."""
    try:
        generator = get_plan_generator()
        high_priority = generator.get_high_priority_actions(limit)
        return {
            "success": True,
            "actions": [a.to_dict() for a in high_priority],
            "total": len(high_priority),
        }
    except Exception as e:
        logger.error(f"Failed to get high priority actions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/actions/status")
def update_action_status(request: ActionStatusRequest):
    """Update status of an improvement action."""
    try:
        generator = get_plan_generator()
        success = generator.update_action_status(request.action_id, request.new_status)
        if not success:
            raise HTTPException(status_code=404, detail="Action not found")
        return {
            "success": True,
            "action_id": request.action_id,
            "new_status": request.new_status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update action status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/dashboard")
def get_dashboard():
    """Get self-improvement dashboard summary."""
    try:
        engine = get_reflection_engine()
        generator = get_plan_generator()

        plan = engine.generate_improvement_plan()
        pending_actions = generator.get_pending_actions()

        return {
            "success": True,
            "reflections": {
                "total": len(engine._reflections),
                "pending": len(engine.get_pending_reflections()),
                "high_priority": len(engine.get_high_priority_reflections()),
            },
            "plan": plan,
            "actions": {
                "total": len(generator._actions),
                "pending": len(pending_actions),
                "high_priority": len(generator.get_high_priority_actions()),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None
