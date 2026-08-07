"""Auto-Apply API — Endpoints for automatic job application.

Endpoints:
- GET /api/auto-apply/status — Current auto-apply status
- POST /api/auto-apply/apply — Auto-apply to an opportunity
- GET /api/auto-apply/applications — Get application history
- GET /api/auto-apply/config — Get auto-apply configuration
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.financial_intelligence.auto_apply import get_auto_apply_system

router = APIRouter(prefix="/api/auto-apply", tags=["auto-apply"])
logger = logging.getLogger(__name__)


class ApplyRequest(BaseModel):
    """Request model for auto-apply."""

    opportunity: dict[str, Any] = Field(..., description="Opportunity to apply to")


@router.get("/status")
async def get_auto_apply_status() -> dict[str, Any]:
    """Get current auto-apply system status."""
    try:
        auto_apply = get_auto_apply_system()
        return auto_apply.get_status()
    except Exception as e:
        logger.error(f"Failed to get auto-apply status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get auto-apply status: {str(e)}") from e


@router.post("/apply")
async def auto_apply(request: ApplyRequest) -> dict[str, Any]:
    """Auto-apply to an opportunity."""
    try:
        auto_apply = get_auto_apply_system()
        record = auto_apply.auto_apply(request.opportunity)
        return {
            "status": "application_submitted",
            "application": record.to_dict(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to auto-apply: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to auto-apply: {str(e)}") from e


@router.get("/applications")
async def get_applications() -> dict[str, Any]:
    """Get all auto-application records."""
    try:
        auto_apply = get_auto_apply_system()
        return {
            "total_applications": len(auto_apply._applications),
            "applications": [app.to_dict() for app in auto_apply._applications],
        }
    except Exception as e:
        logger.error(f"Failed to get applications: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get applications: {str(e)}") from e


@router.get("/config")
async def get_auto_apply_config() -> dict[str, Any]:
    """Get auto-apply configuration."""
    try:
        auto_apply = get_auto_apply_system()
        return {
            "max_applications_per_hour": auto_apply.config.max_applications_per_hour,
            "min_delay_between_applications": auto_apply.config.min_delay_between_applications,
            "max_delay_between_applications": auto_apply.config.max_delay_between_applications,
            "enabled_platforms": auto_apply.config.enabled_platforms,
        }
    except Exception as e:
        logger.error(f"Failed to get auto-apply config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get auto-apply config: {str(e)}") from e
