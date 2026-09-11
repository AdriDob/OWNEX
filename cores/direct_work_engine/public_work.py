"""Public Work Ladder — capa de clasificación/presentación sobre el ranking existente.

La escalera NO es otro motor de ranking: consume ``RankedOpportunity`` tal cual
lo devuelve ``IntelligentRecommender.recommend()`` y solo agrega peldaño (rung)
+ bloque de validación honesta. Una sola inteligencia, una sola verdad.

Peldaños (enums estables en inglés, etiquetas ES para UI):
- OSS_VALIDATION (Etapa 0): trabajo público SIN recompensa — docs/tests/bugs.
  Objetivo: PR merged = primera validación pública, sin experiencia formal.
- BEGINNER / INTERMEDIATE / ADVANCED / EXPERT: con recompensa, ordenados por
  índice de dificultad (reward + barrera + competencia + aceptación).
  Los rangos monetarios ($100–$500, $500–$2k) son orientativos, NUNCA reglas:
  un bounty de $100 puede ser más difícil que uno de $500.

Regla de honestidad: inputs desconocidos ⇒ banda UNKNOWN / rung por lo conocido,
jamás números inventados.
"""

from __future__ import annotations

import logging
import math
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.direct_work_engine.public_work")


class PublicWorkRung(StrEnum):
    """Estable en inglés — la UI traduce vía RUNG_LABEL_ES."""

    OSS_VALIDATION = "oss_validation"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


RUNG_ORDER: tuple[PublicWorkRung, ...] = (
    PublicWorkRung.OSS_VALIDATION,
    PublicWorkRung.BEGINNER,
    PublicWorkRung.INTERMEDIATE,
    PublicWorkRung.ADVANCED,
    PublicWorkRung.EXPERT,
)

RUNG_LABEL_ES: dict[PublicWorkRung, str] = {
    PublicWorkRung.OSS_VALIDATION: "Etapa 0 · Validación OSS",
    PublicWorkRung.BEGINNER: "Principiante",
    PublicWorkRung.INTERMEDIATE: "Intermedio",
    PublicWorkRung.ADVANCED: "Avanzado",
    PublicWorkRung.EXPERT: "Experto",
}

RUNG_GOAL_ES: dict[PublicWorkRung, str] = {
    PublicWorkRung.OSS_VALIDATION: "Conseguir PR merged (docs/tests/bugs pequeños)",
    PublicWorkRung.BEGINNER: "Primer trabajo recompensado",
    PublicWorkRung.INTERMEDIATE: "Bounties medios: backend / AI / tooling / testing",
    PublicWorkRung.ADVANCED: "Infraestructura / DevOps / security / AI de mayor valor",
    PublicWorkRung.EXPERT: "Grandes recompensas: blockchain / security / sistemas complejos",
}

_RUNG_PROOF_ES: dict[PublicWorkRung, str] = {
    PublicWorkRung.OSS_VALIDATION: "PR MERGED",
    PublicWorkRung.BEGINNER: "PR ACEPTADO + PAGO",
    PublicWorkRung.INTERMEDIATE: "PR ACEPTADO + PAGO",
    PublicWorkRung.ADVANCED: "PR ACEPTADO + PAGO",
    PublicWorkRung.EXPERT: "PR ACEPTADO + PAGO",
}


def _clamp01(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def difficulty_index(
    payment: float,
    barrier_total: float | None,
    acceptance: float | None,
    competition: float | None,
) -> tuple[float, bool]:
    """Índice de dificultad 0–1 + flag de inputs incompletos.

    Ponderación: reward 0.30 (escala log — $10k satura), barrera invertida
    0.25, competencia 0.25, aceptación invertida 0.20. Desconocidos ⇒ 0.5
    neutral con flag (no fingen precisión).
    """
    unknown = False
    reward_norm = _clamp01(math.log10(1.0 + max(float(payment or 0.0), 0.0)) / 4.0)
    if barrier_total is None:
        barrier_inv, unknown = 0.5, True
    else:
        barrier_inv = 1.0 - _clamp01(barrier_total / 100.0)
    if competition is None:
        comp, unknown = 0.5, True
    else:
        comp = _clamp01(competition)
    if acceptance is None:
        accept_inv, unknown = 0.5, True
    else:
        accept_inv = 1.0 - _clamp01(acceptance)
    score = 0.30 * reward_norm + 0.25 * barrier_inv + 0.25 * comp + 0.20 * accept_inv
    return round(_clamp01(score), 3), unknown


def classify_rung(
    payment: float | None,
    barrier_total: float | None = None,
    acceptance: float | None = None,
    competition: float | None = None,
) -> tuple[PublicWorkRung, float, bool]:
    """Clasifica (rung, difficulty, inputs_unknown).

    payment <= 0 o ausente ⇒ OSS_VALIDATION (Etapa 0): no hay recompensa que
    rankear, hay validación pública que ganar.
    """
    try:
        amount = float(payment or 0.0)
    except (TypeError, ValueError):
        amount = 0.0
    if amount <= 0:
        return PublicWorkRung.OSS_VALIDATION, 0.0, False
    score, unknown = difficulty_index(amount, barrier_total, acceptance, competition)
    if score < 0.30:
        return PublicWorkRung.BEGINNER, score, unknown
    if score < 0.50:
        return PublicWorkRung.INTERMEDIATE, score, unknown
    if score < 0.70:
        return PublicWorkRung.ADVANCED, score, unknown
    return PublicWorkRung.EXPERT, score, unknown


def validation_block(rung: PublicWorkRung, requires_formal_experience: bool = False) -> dict[str, Any]:
    """Bloque VALIDACIÓN PÚBLICA en español para la UI."""
    checks = [
        "No requiere experiencia profesional formal"
        if not requires_formal_experience
        else "Puede requerir historial demostrable",
        "Requisitos técnicos compatibles (ver fit)",
        "Trabajo público verificable",
        "Ruta de entrega conocida (PR / reporte / entrega)",
    ]
    return {
        "checks": checks,
        "proof": _RUNG_PROOF_ES[rung],
        "rung": rung.value,
        "rung_label_es": RUNG_LABEL_ES[rung],
        "rung_goal_es": RUNG_GOAL_ES[rung],
    }


def enrich_ranked(ranked: Any) -> dict[str, Any]:
    """Enriquece un RankedOpportunity con rung + validación (nunca raisea)."""
    try:
        opp = ranked.opportunity
        payment = float(getattr(opp, "payment", 0.0) or 0.0)
        zb = getattr(ranked, "zero_barrier_score", None) or getattr(opp, "zero_barrier_score", None)
        barrier = float(zb.total) if zb is not None and getattr(zb, "total", None) is not None else None
        acceptance = getattr(ranked, "acceptance_probability", None)
        competition = getattr(ranked, "competition_level", None)
        if isinstance(competition, str):
            competition = None
        rung, difficulty, unknown = classify_rung(payment, barrier, acceptance, competition)
        block = validation_block(rung)
        block["difficulty"] = difficulty
        block["difficulty_unknown_inputs"] = unknown
        return block
    except Exception as exc:  # nunca romper el ranking por presentar
        logger.warning("public_work enrich falló: %s", exc)
        block = validation_block(PublicWorkRung.BEGINNER)
        block["difficulty"] = 0.5
        block["difficulty_unknown_inputs"] = True
        return block
