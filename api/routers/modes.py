"""Modes API — LITE/FULL/CAPITAL mode endpoints.

Endpoints for mode switching, adaptive recommendations, and mode-specific data.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/modes", tags=["modes"])


class SetModeRequest(BaseModel):
    mode: str  # lite, full, capital


class RecommendModeRequest(BaseModel):
    monthly_income: float = 0
    monthly_target: float = 5000
    capital: float = 0
    capital_target: float = 1_000_000
    pending_findings: int = 0
    active_agents: int = 0
    pending_approvals: int = 0


@router.get("/current")
async def get_current_mode():
    """Get current mode and configuration."""
    from cores.modes.engine import get_mode_engine

    engine = get_mode_engine()
    return engine.to_dict()


@router.post("/set")
async def set_mode(request: SetModeRequest):
    """Switch to a new mode."""
    from cores.modes.engine import OwnexMode, get_mode_engine

    engine = get_mode_engine()
    try:
        mode = OwnexMode(request.mode)
    except ValueError:
        return {"error": f"Invalid mode: {request.mode}. Use: lite, full, capital"}

    config = engine.set_mode(mode)
    return {
        "status": "ok",
        "mode": config.name,
        "tagline": config.tagline,
        "question": config.question,
        "nav_items": config.nav_items,
        "ui_density": config.ui_density,
    }


@router.get("/available")
async def get_available_modes():
    """Get all available modes."""
    from cores.modes.engine import get_mode_engine

    engine = get_mode_engine()
    modes = []
    for mode, config in engine.configs.items():
        modes.append(
            {
                "mode": mode.value,
                "name": config.name,
                "tagline": config.tagline,
                "question": config.question,
            }
        )
    return {"modes": modes}


@router.post("/recommend")
async def recommend_mode(request: RecommendModeRequest):
    """Get adaptive mode recommendation based on current state."""
    from cores.modes.engine import get_mode_engine

    engine = get_mode_engine()
    rec = engine.recommend_mode(
        monthly_income=request.monthly_income,
        monthly_target=request.monthly_target,
        capital=request.capital,
        capital_target=request.capital_target,
        pending_findings=request.pending_findings,
        active_agents=request.active_agents,
        pending_approvals=request.pending_approvals,
    )
    return {
        "recommended_mode": rec.recommended_mode.value,
        "reason": rec.reason,
        "confidence": rec.confidence,
        "income_gap": rec.income_gap,
        "capital_gap": rec.capital_gap,
        "operational_load": rec.operational_load,
    }


@router.get("/nav")
async def get_nav_items():
    """Get navigation items for current mode."""
    from cores.modes.engine import get_mode_engine

    engine = get_mode_engine()
    return {"nav_items": engine.get_nav_items()}
