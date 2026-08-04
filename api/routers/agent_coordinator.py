"""Agent Coordinator API — multi-agent bounty orchestration.

Endpoints:
- POST /api/agent-coordinator/start — Start the coordinator scheduler
- POST /api/agent-coordinator/stop — Stop the coordinator scheduler
- GET /api/agent-coordinator/status — Get coordinator status
- POST /api/agent-coordinator/add-bounty — Add a bounty to the queue
"""

from __future__ import annotations

from logging import getLogger
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.agents.bounty_coordinator import CoordinatorConfig, get_bounty_coordinator

router = APIRouter(prefix="/api/agent-coordinator", tags=["agent-coordinator"])
logger = getLogger(__name__)


class BountyRequest(BaseModel):
    """Request model for adding a bounty to the queue."""

    bounty_id: str = Field(..., description="Bounty ID from platform")
    repo: str = Field(..., description="GitHub repository (owner/repo)")
    issue_number: int = Field(..., description="Issue number")
    issue_url: str = Field(..., description="Full issue URL")
    title: str = Field(..., description="Issue title")
    description: str = Field(default="", description="Issue description")
    evh: float = Field(default=0.0, description="Expected Value per Hour (for priority)")


class CoordinatorConfigRequest(BaseModel):
    """Request model for coordinator configuration."""

    max_concurrent: int = Field(default=3, ge=1, le=10, description="Max concurrent bounties")
    timeout_minutes: int = Field(default=30, ge=5, le=120, description="Timeout per bounty (minutes)")
    auto_start: bool = Field(default=False, description="Auto-start when bounties are added")
    enable_priority_queue: bool = Field(default=True, description="Use EVH-based priority queue")
    cleanup_on_failure: bool = Field(default=True, description="Auto-cleanup on failure")


@router.post("/start")
async def start_coordinator() -> dict[str, Any]:
    """Start the coordinator scheduler."""
    try:
        coordinator = get_bounty_coordinator()
        result = coordinator.start()
        return result
    except Exception as e:
        logger.error("Failed to start coordinator: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to start coordinator: {str(e)}") from e


@router.post("/stop")
async def stop_coordinator() -> dict[str, Any]:
    """Stop the coordinator scheduler."""
    try:
        coordinator = get_bounty_coordinator()
        result = coordinator.stop()
        return result
    except Exception as e:
        logger.error("Failed to stop coordinator: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to stop coordinator: {str(e)}") from e


@router.get("/status")
async def get_coordinator_status() -> dict[str, Any]:
    """Get current coordinator status."""
    try:
        coordinator = get_bounty_coordinator()
        return coordinator.get_status()
    except Exception as e:
        logger.error("Failed to get coordinator status: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}") from e


@router.post("/add-bounty")
async def add_bounty(request: BountyRequest) -> dict[str, Any]:
    """Add a bounty to the queue."""
    try:
        coordinator = get_bounty_coordinator()
        result = coordinator.add_bounty(
            bounty_id=request.bounty_id,
            repo=request.repo,
            issue_number=request.issue_number,
            issue_url=request.issue_url,
            title=request.title,
            description=request.description,
            evh=request.evh,
        )
        return result
    except Exception as e:
        logger.error("Failed to add bounty: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to add bounty: {str(e)}") from e


@router.post("/config")
async def update_coordinator_config(request: CoordinatorConfigRequest) -> dict[str, Any]:
    """Update coordinator configuration (requires restart to take effect)."""
    try:
        # Note: This creates a new instance with new config
        # In production, you might want to update the existing instance
        coordinator = get_bounty_coordinator(
            CoordinatorConfig(
                max_concurrent=request.max_concurrent,
                timeout_minutes=request.timeout_minutes,
                auto_start=request.auto_start,
                enable_priority_queue=request.enable_priority_queue,
                cleanup_on_failure=request.cleanup_on_failure,
            )
        )
        logger.info(
            "Coordinator config updated: max_concurrent=%d, timeout=%dmin",
            request.max_concurrent,
            request.timeout_minutes,
        )
        return {
            "status": "config_updated",
            "config": {
                "max_concurrent": coordinator.config.max_concurrent,
                "timeout_minutes": coordinator.config.timeout_minutes,
                "auto_start": coordinator.config.auto_start,
                "enable_priority_queue": coordinator.config.enable_priority_queue,
                "cleanup_on_failure": coordinator.config.cleanup_on_failure,
            },
        }
    except Exception as e:
        logger.error("Failed to update coordinator config: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}") from e


@router.delete("/completed/{bounty_id}")
async def remove_completed_bounty(bounty_id: str) -> dict[str, Any]:
    """Remove a completed bounty from history."""
    try:
        coordinator = get_bounty_coordinator()
        if bounty_id in coordinator._completed_tasks:
            del coordinator._completed_tasks[bounty_id]
            logger.info("Removed completed bounty %s from history", bounty_id)
            return {"status": "removed", "bounty_id": bounty_id}
        else:
            raise HTTPException(status_code=404, detail=f"Bounty {bounty_id} not found in completed tasks")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove bounty: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to remove bounty: {str(e)}") from e


@router.get("/queue")
async def get_queue_details() -> dict[str, Any]:
    """Get detailed queue information."""
    try:
        coordinator = get_bounty_coordinator()
        return {
            "queue_size": coordinator._queue.qsize(),
            "active_count": len(coordinator._active_tasks),
            "completed_count": len(coordinator._completed_tasks),
            "active_bounties": [
                {
                    "bounty_id": task.bounty_id,
                    "status": task.status,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                }
                for task in coordinator._active_tasks.values()
            ],
        }
    except Exception as e:
        logger.error("Failed to get queue details: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get queue details: {str(e)}") from e
