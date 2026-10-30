from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from cores.financial_intelligence.mode_manager import ModeType, get_mode_manager
from cores.settings.service import (
    OWNEXMode as CATEYEMode,
)
from cores.settings.service import (
    get_all_settings,
    get_mode,
    get_platform_config,
    set_mode,
    set_platform_config,
)

router = APIRouter(prefix="/api/settings/runtime", tags=["settings"])


@router.get("")
def get_runtime_settings() -> dict[str, Any]:
    return get_all_settings()


@router.get("/mode")
def get_mode_setting() -> dict[str, str]:
    return {"mode": get_mode().value}


@router.put("/mode")
def set_mode_setting(body: dict[str, str]) -> dict[str, str]:
    mode = body.get("mode", "manual")
    try:
        validated = CATEYEMode(mode)
    except ValueError:
        validated = CATEYEMode.MANUAL
    set_mode(validated)
    return {"mode": validated.value, "status": "ok"}


@router.get("/mode/primary")
def get_primary_mode() -> dict[str, str]:
    """Get the primary operational mode (LITE/FULL/CAPITAL)."""
    mm = get_mode_manager()
    primary = mm.get_mode(ModeType.PRIMARY)
    return {"mode": primary or "lite"}


@router.put("/mode/primary")
def set_primary_mode(body: dict[str, str]) -> dict[str, Any]:
    """Set the primary operational mode (LITE/FULL/CAPITAL)."""
    mm = get_mode_manager()
    mode = body.get("mode", "lite")
    valid_modes = ["lite", "full", "capital"]
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid primary mode. Must be one of: {valid_modes}")
    result = mm.set_mode(f"primary_{mode}")
    return result


@router.get("/mode/all")
def get_all_modes() -> dict[str, Any]:
    """Get all active modes."""
    mm = get_mode_manager()
    return {"active_modes": mm.get_active_modes(), "available": mm.get_available_modes()}


@router.get("/platforms")
def get_platform_settings() -> dict[str, dict[str, Any]]:
    from cores.settings.service import get_all_platform_configs

    return get_all_platform_configs()


@router.get("/platforms/{platform_id}")
def get_single_platform(platform_id: str) -> dict[str, Any]:
    return get_platform_config(platform_id)


@router.put("/platforms/{platform_id}")
def update_platform(platform_id: str, body: dict[str, Any]) -> dict[str, Any]:
    set_platform_config(platform_id, body)
    return {**get_platform_config(platform_id), "status": "ok"}
