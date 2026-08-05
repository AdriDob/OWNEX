"""OWNEX Result-Based Opportunity Model — API router.

Exposes the Level S/A/B/C classification and the First-Day Guide so Mission
Control can steer a user toward result-based work (value proven by delivery).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from cores.result_based import FirstDayGuide, ResultBasedClassifier

logger = logging.getLogger("ownex.api.result_based")

router = APIRouter(prefix="/result-based", tags=["result-based"])

_guide: FirstDayGuide | None = None


def _first_day() -> FirstDayGuide:
    global _guide
    if _guide is None:
        _guide = FirstDayGuide()
    return _guide


class ClassifyRequest(BaseModel):
    opportunity: dict[str, Any]


@router.post("/classify")
async def classify(req: ClassifyRequest) -> dict[str, Any]:
    """Classify an opportunity into a result-based level (S/A/B/C)."""
    return ResultBasedClassifier().classify(req.opportunity).to_dict()


@router.get("/levels")
async def levels() -> dict[str, Any]:
    """The model's level legend (S/A/B/C definitions)."""
    return {
        "S": "Direct Result — publico, pago por resultado, sin entrevista/portfolio/prueba.",
        "A": "Low Friction — registro simple, pago por trabajo completado (AI eval, data).",
        "B": "Skill-Proof — sin entrevista, tu trabajo entregado es la prueba (OSS bounty).",
        "C": "Traditional — proceso de contratación; despriorizado para trabajo por resultado.",
        "principle": "Sin entrevista no es sin competencia: la competencia se mueve del CV al resultado entregado.",
        "objective": "Recompensa esperada x probabilidad de éxito / tiempo invertido.",
    }


@router.get("/first-day")
async def first_day() -> dict[str, Any]:
    """Step-by-step first-day path to real rewards for a beginner with no experience."""
    return {
        "guide": _first_day().guidance(),
        "progress": _first_day().progress(),
    }


@router.post("/first-day/step")
async def first_day_step(step: int) -> dict[str, Any]:
    """Mark a first-day step as completed (tracks your journey)."""
    _first_day().save_step_complete(step)
    return _first_day().progress()
