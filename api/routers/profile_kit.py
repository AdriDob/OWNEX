"""API Router para el perfil kit: generación y persistencia de textos listos para copiar."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from api.routers.direct_work import _INCOME_MAX_DEFAULT_PROFILE as _DWE_DEFAULTS
from cores.direct_work_engine.profile_kit import ProfileKitEngine

logger = logging.getLogger("api.profile_kit")

router = APIRouter(prefix="/api/profile-kit", tags=["profile-kit"])


def _get_engine() -> ProfileKitEngine:
    return ProfileKitEngine()


def _seed_profile(engine: ProfileKitEngine) -> dict[str, Any]:
    """Perfil de arranque: el guardado si existe, sino los defaults reales del DWE."""
    saved = engine.get()
    if saved:
        return saved
    return {**_DWE_DEFAULTS, "experience_level": "none", "availability_hours": 40}


@router.get("/")
async def profile_kit_status() -> dict[str, Any]:
    """Retorna el estado actual del perfil kit: guardado, plataformas disponibles, perfil."""
    engine = _get_engine()
    saved = engine.get()
    return {
        "saved": bool(saved),
        "available_platforms": engine.platforms(),
        "profile": saved or _seed_profile(engine),
    }


@router.post("/")
async def profile_kit_save(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Guarda los datos del perfil kit (persistencia real en data/profile_kit.json)."""
    engine = _get_engine()
    saved = engine.save(payload or {})
    return {"success": True, "saved": saved}


@router.post("/generate")
async def profile_kit_generate(profile_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Genera textos listos para copiar por plataforma, a partir de los datos del perfil."""
    engine = _get_engine()
    if profile_data:
        profile = engine.profile_from_dict(profile_data)
    else:
        profile = engine.profile_from_dict(_seed_profile(engine))
    return {"kits": engine.generate(profile)}
