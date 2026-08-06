"""Ultra Fast Income API — Endpoints for Phase 0 survival mode.

Endpoints:
- GET /api/ultra-fast-income/status — Current mode and status
- POST /api/ultra-fast-income/set-mode — Set income mode (ultra_fast/balanced/scaling)
- GET /api/ultra-fast-income/plan — Generate ultra fast income plan
- POST /api/ultra-fast-income/generate-plan — Generate plan with custom opportunities
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.financial_intelligence.ultra_fast_income import (
    IncomeMode,
    UltraFastIncomeEngine,
    get_ultra_fast_income_engine,
)

router = APIRouter(prefix="/api/ultra-fast-income", tags=["ultra-fast-income"])
logger = logging.getLogger(__name__)


class SetModeRequest(BaseModel):
    """Request model for setting income mode."""

    mode: str = Field(..., description="Income mode: ultra_fast, balanced, or scaling")


@router.get("/status")
async def get_ultra_fast_status() -> dict[str, Any]:
    """Get current ultra fast income mode status."""
    try:
        engine = get_ultra_fast_income_engine()
        return engine.get_status()
    except Exception as e:
        logger.error(f"Failed to get ultra fast status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ultra fast status: {str(e)}") from e


@router.post("/set-mode")
async def set_income_mode(request: SetModeRequest) -> dict[str, Any]:
    """Set the current income generation mode."""
    try:
        engine = get_ultra_fast_income_engine()
        try:
            mode = IncomeMode(request.mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {request.mode}. Must be one of: ultra_fast, balanced, scaling"
            )

        engine.set_mode(mode)
        return {
            "status": "mode_set",
            "current_mode": mode.value,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set income mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set income mode: {str(e)}") from e


@router.get("/plan")
async def get_ultra_fast_plan() -> dict[str, Any]:
    """Generate ultra fast income plan for current mode."""
    try:
        engine = get_ultra_fast_income_engine()
        plan = engine.generate_plan()
        return plan.to_dict()
    except Exception as e:
        logger.error(f"Failed to generate ultra fast plan: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate ultra fast plan: {str(e)}") from e


@router.post("/generate-plan")
async def generate_ultra_fast_plan(opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate ultra fast income plan with custom opportunities."""
    try:
        engine = get_ultra_fast_income_engine()
        plan = engine.generate_plan(opportunities=opportunities)
        return plan.to_dict()
    except Exception as e:
        logger.error(f"Failed to generate ultra fast plan: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate ultra fast plan: {str(e)}") from e


@router.get("/config")
async def get_ultra_fast_config() -> dict[str, Any]:
    """Get ultra fast income configuration."""
    try:
        engine = get_ultra_fast_income_engine()
        return {
            "min_cash_speed": engine.config.min_cash_speed,
            "priority_categories": engine.config.priority_categories,
            "max_daily_target_usd": engine.config.max_daily_target_usd,
            "max_weekly_target_usd": engine.config.max_weekly_target_usd,
            "min_acceptance_probability": engine.config.min_acceptance_probability,
            "max_hours_per_day": engine.config.max_hours_per_day,
        }
    except Exception as e:
        logger.error(f"Failed to get ultra fast config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ultra fast config: {str(e)}") from e
