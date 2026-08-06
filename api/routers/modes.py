"""Mode Manager API — Endpoints for centralized mode management.

Endpoints:
- GET /api/modes/status — Current mode manager status
- GET /api/modes/active — Get all active modes
- GET /api/modes/available — Get all available modes with status
- POST /api/modes/set — Set a mode with conflict detection
- POST /api/modes/set-force — Set a mode and force resolve conflicts
- GET /api/modes/compatibility — Get compatibility matrix
- GET /api/modes/history — Get mode change history
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.financial_intelligence.mode_manager import get_mode_manager

router = APIRouter(prefix="/api/modes", tags=["modes"])
logger = logging.getLogger(__name__)


class SetModeRequest(BaseModel):
    """Request model for setting a mode."""

    mode_key: str = Field(..., description="Mode key to activate (e.g., 'income_ultra_fast')")
    force: bool = Field(default=False, description="Force activate and auto-resolve conflicts")


@router.get("/status")
async def get_mode_status() -> dict[str, Any]:
    """Get current mode manager status."""
    try:
        mode_manager = get_mode_manager()
        return mode_manager.get_status()
    except Exception as e:
        logger.error(f"Failed to get mode status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get mode status: {str(e)}") from e


@router.get("/active")
async def get_active_modes() -> dict[str, Any]:
    """Get all currently active modes."""
    try:
        mode_manager = get_mode_manager()
        return {
            "active_modes": mode_manager.get_active_modes(),
            "total": len(mode_manager.get_active_modes()),
        }
    except Exception as e:
        logger.error(f"Failed to get active modes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active modes: {str(e)}") from e


@router.get("/available")
async def get_available_modes() -> dict[str, Any]:
    """Get all available modes with their current status."""
    try:
        mode_manager = get_mode_manager()
        return mode_manager.get_available_modes()
    except Exception as e:
        logger.error(f"Failed to get available modes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available modes: {str(e)}") from e


@router.post("/set")
async def set_mode(request: SetModeRequest) -> dict[str, Any]:
    """Set a mode with conflict detection."""
    try:
        mode_manager = get_mode_manager()
        result = mode_manager.set_mode(request.mode_key, force=request.force)
        return result
    except Exception as e:
        logger.error(f"Failed to set mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set mode: {str(e)}") from e


@router.post("/set-force")
async def set_mode_force(request: SetModeRequest) -> dict[str, Any]:
    """Set a mode and force resolve conflicts."""
    try:
        mode_manager = get_mode_manager()
        result = mode_manager.set_mode(request.mode_key, force=True)
        return result
    except Exception as e:
        logger.error(f"Failed to set mode with force: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set mode with force: {str(e)}") from e


@router.get("/compatibility")
async def get_compatibility_matrix() -> dict[str, Any]:
    """Get compatibility matrix for all modes."""
    try:
        mode_manager = get_mode_manager()
        return mode_manager.get_compatibility_matrix()
    except Exception as e:
        logger.error(f"Failed to get compatibility matrix: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get compatibility matrix: {str(e)}") from e


@router.get("/history")
async def get_mode_history(limit: int = 20) -> dict[str, Any]:
    """Get mode change history."""
    try:
        mode_manager = get_mode_manager()
        return {
            "history": mode_manager.get_history(limit=limit),
            "total": len(mode_manager._history),
        }
    except Exception as e:
        logger.error(f"Failed to get mode history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get mode history: {str(e)}") from e
