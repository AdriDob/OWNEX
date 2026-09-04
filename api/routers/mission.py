"""API Router for Mission Controller."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.mission.controller import (
    MissionController,
    MissionType,
    get_mission_controller,
)

router = APIRouter(prefix="/api/mission", tags=["mission"])


# ── Request/Response Models ──────────────────────────────────────


class MissionCreateRequest(BaseModel):
    """Request to create a new mission."""

    mission_type: str = Field(..., description="Type of mission (security_pipeline, dev_bounty, direct_work, etc.)")
    opportunity_id: str | None = Field(None, description="Associated opportunity ID")
    workflow_id: str | None = Field(None, description="Associated workflow ID")
    priority: int = Field(0, description="Mission priority")
    expected_value_usd: float = Field(0.0, description="Expected revenue in USD")
    payload: dict | None = Field(None, description="Mission payload data")
    context: dict | None = Field(None, description="Mission context data")
    total_stages: int = Field(0, description="Total number of stages")
    max_retries: int = Field(3, description="Maximum retry attempts")


class MissionAdvanceRequest(BaseModel):
    """Request to advance mission stage."""

    stage: str = Field(..., description="Stage name")
    stage_order: int = Field(..., description="Stage order number")
    result: dict | None = Field(None, description="Stage result data")
    context_update: dict | None = Field(None, description="Context update data")


class MissionCheckpointRequest(BaseModel):
    """Request to save checkpoint."""

    stage: str = Field(..., description="Stage name")
    stage_order: int = Field(..., description="Stage order number")
    result: dict = Field(..., description="Stage result data")
    context: dict = Field(..., description="Context data")


class MissionCompleteRequest(BaseModel):
    """Request to complete a mission."""

    actual_value_usd: float = Field(0.0, description="Actual revenue in USD")
    result: dict | None = Field(None, description="Final result data")


class MissionFailRequest(BaseModel):
    """Request to fail a mission."""

    error_message: str = Field(..., description="Error message")
    error_state: str = Field("execution", description="Error state/category")


class MissionBlockRequest(BaseModel):
    """Request to block a mission."""

    reason: str = Field(..., description="Reason for blocking")


class MissionResponse(BaseModel):
    """Response for mission operations."""

    success: bool
    mission: dict | None = None
    message: str = ""
    error: str | None = None


# ── Dependency ───────────────────────────────────────────────────


def get_controller() -> MissionController:
    return get_mission_controller()


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/create", response_model=MissionResponse, status_code=status.HTTP_201_CREATED)
async def create_mission(
    request: MissionCreateRequest, controller: MissionController = Depends(get_controller)
) -> MissionResponse:
    """Create a new mission."""
    try:
        mission_type = MissionType(request.mission_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mission type: {request.mission_type}")

    result = controller.create_mission(
        mission_type=mission_type,
        opportunity_id=request.opportunity_id,
        workflow_id=request.workflow_id,
        priority=request.priority,
        expected_value_usd=request.expected_value_usd,
        payload=request.payload,
        context=request.context,
        total_stages=request.total_stages,
        max_retries=request.max_retries,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error or result.message)

    return MissionResponse(
        success=True,
        mission=result.mission.to_dict() if result.mission else None,
        message=result.message,
    )


@router.get("/summary")
async def get_mission_summary(controller: MissionController = Depends(get_controller)):
    """Get mission summary for dashboard."""
    return controller.get_mission_summary()


@router.get("/active")
async def get_active_missions(controller: MissionController = Depends(get_controller)):
    """Get all active missions."""
    missions = controller.get_active_missions()
    return {"missions": [m.to_dict() for m in missions]}


@router.get("/blocked")
async def get_blocked_missions(controller: MissionController = Depends(get_controller)):
    """Get blocked missions."""
    missions = controller.get_blocked_missions()
    return {"missions": [m.to_dict() for m in missions]}


@router.get("/waiting-human")
async def get_waiting_human_missions(controller: MissionController = Depends(get_controller)):
    """Get missions waiting for human approval."""
    missions = controller.get_waiting_human_missions()
    return {"missions": [m.to_dict() for m in missions]}


@router.get("/stale")
async def get_stale_missions(max_age_hours: float = 2.0, controller: MissionController = Depends(get_controller)):
    """Get stale missions (no heartbeat)."""
    missions = controller.get_stale_missions(max_age_hours)
    return {"missions": [m.to_dict() for m in missions]}


@router.get("/{mission_id}")
async def get_mission(mission_id: str, controller: MissionController = Depends(get_controller)):
    """Get mission by ID."""
    result = controller.get_status(mission_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"mission": result.mission.to_dict()}


@router.post("/{mission_id}/start")
async def start_mission(mission_id: str, controller: MissionController = Depends(get_controller)):
    """Start a mission."""
    result = controller.start_mission(mission_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"success": True, "mission": result.mission.to_dict()}


@router.post("/{mission_id}/advance")
async def advance_stage(
    mission_id: str, request: MissionAdvanceRequest, controller: MissionController = Depends(get_controller)
):
    """Advance mission to next stage."""
    result = controller.advance_stage(
        mission_id,
        request.stage,
        request.stage_order,
        request.result,
        request.context_update,
    )
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"success": True, "mission": result.mission.to_dict()}


@router.post("/{mission_id}/checkpoint")
async def checkpoint(
    mission_id: str, request: MissionCheckpointRequest, controller: MissionController = Depends(get_controller)
):
    """Save checkpoint for mission."""
    result = controller.checkpoint(
        mission_id,
        request.stage,
        request.stage_order,
        request.result,
        request.context,
    )
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"success": True, "mission": result.mission.to_dict()}


@router.post("/{mission_id}/complete")
async def complete_mission(
    mission_id: str, request: MissionCompleteRequest, controller: MissionController = Depends(get_controller)
):
    """Complete a mission."""
    result = controller.complete_mission(mission_id, request.actual_value_usd, request.result)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"success": True, "mission": result.mission.to_dict()}


@router.post("/{mission_id}/fail")
async def fail_mission(
    mission_id: str, request: MissionFailRequest, controller: MissionController = Depends(get_controller)
):
    """Fail a mission."""
    result = controller.fail_mission(mission_id, request.error_message, request.error_state)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"success": True, "mission": result.mission.to_dict()}


@router.post("/{mission_id}/block")
async def block_mission(
    mission_id: str, request: MissionBlockRequest, controller: MissionController = Depends(get_controller)
):
    """Block a mission (waiting for human/external)."""
    result = controller.block_mission(mission_id, request.reason)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"success": True, "mission": result.mission.to_dict()}


@router.post("/{mission_id}/unblock")
async def unblock_mission(mission_id: str, controller: MissionController = Depends(get_controller)):
    """Unblock a mission."""
    result = controller.unblock_mission(mission_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"success": True, "mission": result.mission.to_dict()}


@router.post("/{mission_id}/checkpoint")
async def save_checkpoint(
    mission_id: str, request: MissionCheckpointRequest, controller: MissionController = Depends(get_controller)
):
    """Save checkpoint for mission."""
    result = controller.checkpoint(
        mission_id,
        request.stage,
        request.stage_order,
        request.result,
        request.context,
    )
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"success": True, "mission": result.mission.to_dict()}


@router.post("/{mission_id}/restore")
async def restore_from_checkpoint(mission_id: str, controller: MissionController = Depends(get_controller)):
    """Restore mission from latest checkpoint."""
    result = controller.restore_from_checkpoint(mission_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found or no checkpoint")
    return {"success": True, "mission": result.mission.to_dict()}


@router.post("/{mission_id}/heartbeat")
async def heartbeat(mission_id: str, controller: MissionController = Depends(get_controller)):
    """Update mission heartbeat."""
    result = controller.heartbeat(mission_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Mission not found")
    return {"success": True, "mission": result.mission.to_dict()}


@router.get("/stale")
async def get_stale(max_age_hours: float = 2.0, controller: MissionController = Depends(get_controller)):
    """Get stale missions."""
    missions = controller.get_stale_missions(max_age_hours)
    return {"missions": [m.to_dict() for m in missions]}


@router.post("/recover-stale")
async def recover_stale(max_age_hours: float = 2.0, controller: MissionController = Depends(get_controller)):
    """Recover stale missions."""
    recovered = controller.recover_stale_missions(max_age_hours)
    return {"recovered": len(recovered), "missions": [m.to_dict() for m in recovered]}
