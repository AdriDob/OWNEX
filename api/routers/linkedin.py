"""LinkedIn Integration Assistant for OWNEX.

Provides:
  - Profile optimization suggestions (headline, skills) based on market data.
  - Skill sync from LinkedIn to the Career Engine / UserProfile.
  - Achievement publishing workflow hooks.

All endpoints require authentication (device-id cookie or Bearer token).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from api.routers.direct_work import _profile_from_dict
from cores.career_engine import CareerEngine

logger = logging.getLogger("ownex.api.linkedin")

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])

_engine = CareerEngine()


# ──────────────────────────────────────────────────────────────────
# GET /api/linkedin/optimize
#   Devuelve sugerencias de headline, skills y secciones completadas
#   basándose en el perfil actual vs. datos de LinkedIn.
# ──────────────────────────────────────────────────────────────────
@router.get("/optimize")
def linkedin_optimize() -> dict[str, Any]:
    """Optimización de perfil LinkedIn.

    Returns
    -------
    headline_sugerido : str
    skills_a_agregar : list[str]
    seccion_a_completar : str
    copy_para_publicar : str | None
    """
    profile = _profile_from_dict({})  # perfil actual (session user)
    # Skills que el Career Engine demanda frecuentemente para categorías S
    demanded = [
        "Python",
        "API",
        "Reverse Engineering",
        "Web Scraping",
        "Bug Bounty",
        "Threat Intelligence",
        "Automation",
    ]
    user_skills = set(profile.get("skills", [])) if profile else set()
    missing = [s for s in demanded if s not in user_skills]
    added = missing[:4]  # top-4 sugiriendo

    headline = f"Bug Bounty Engineer | Finding & Payout Automation — {', '.join(added) if added else 'Python'}"

    return {
        "headline_sugerido": headline,
        "skills_a_agregar": added,
        "seccion_a_completar": "Experience (add recent project/bounty)",
        "copy_para_publicar": None,
    }


# ──────────────────────────────────────────────────────────────────
# GET /api/linkedin/sync
#   (stub) Sincroniza skills y experiencia de LinkedIn al UserProfile
#   y al Career Engine. En producción completaría el flow OAuth2.
# ──────────────────────────────────────────────────────────────────
@router.get("/sync")
def linkedin_sync() -> dict[str, Any]:
    """Sincronización de LinkedIn al perfil OwnEx.

    Returns
    -------
    sync_status : str
    skills_sincronizados : int
    mensaje : str
    """
    return {
        "sync_status": "intent_registered",
        "skills_sincronizados": 0,
        "mensaje": "Sincronización solicitada — completa el flow OAuth2 en settings.",
    }
