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


class RewardKind(StrEnum):
    """TASK_REWARD = pago por tarea individual; PROJECT_FUNDING = financiación de proyecto."""

    TASK_REWARD = "task_reward"
    PROJECT_FUNDING = "project_funding"


class MarketSegment(StrEnum):
    """Segmento económico — determina techo observado y naturaleza del pago."""

    OSS = "oss"
    DEV_BOUNTY = "dev_bounty"
    SECURITY_OSS = "security_oss"
    BUG_BOUNTY = "bug_bounty"
    CHALLENGE = "challenge"
    HACKATHON = "hackathon"
    GRANTS = "grants"
    RETROACTIVE = "retroactive"
    ECOSYSTEM_FUNDING = "ecosystem_funding"


REWARD_KIND_FOR_SEGMENT: dict[MarketSegment, RewardKind] = {
    MarketSegment.OSS: RewardKind.TASK_REWARD,
    MarketSegment.DEV_BOUNTY: RewardKind.TASK_REWARD,
    MarketSegment.SECURITY_OSS: RewardKind.TASK_REWARD,
    MarketSegment.BUG_BOUNTY: RewardKind.TASK_REWARD,
    MarketSegment.CHALLENGE: RewardKind.TASK_REWARD,
    MarketSegment.HACKATHON: RewardKind.TASK_REWARD,
    MarketSegment.GRANTS: RewardKind.PROJECT_FUNDING,
    MarketSegment.RETROACTIVE: RewardKind.PROJECT_FUNDING,
    MarketSegment.ECOSYSTEM_FUNDING: RewardKind.PROJECT_FUNDING,
}

# Techos observados (no promesas) — del análisis del owner 2026-09-13.
# Rango (min_usd, max_observado_usd) + nota honesta sobre tipicidad.
MARKET_CEILINGS: dict[MarketSegment, dict[str, Any]] = {
    MarketSegment.OSS: {
        "min_usd": 0,
        "max_observed_usd": 0,
        "typical": "$0",
        "note": "Validación pública, sin pago directo",
    },
    MarketSegment.DEV_BOUNTY: {
        "min_usd": 20,
        "max_observed_usd": 10_000,
        "typical": "$20–$500",
        "note": "Excepcional $5k–$10k+; mayoría $3–$245 fuera de 3 repos concentrados",
    },
    MarketSegment.SECURITY_OSS: {
        "min_usd": 50,
        "max_observed_usd": 10_000,
        "typical": "$50–$1k",
        "note": "Security OSS (huntr.dev etc.), no bug bounty de programa",
    },
    MarketSegment.BUG_BOUNTY: {
        "min_usd": 100,
        "max_observed_usd": 10_000_000,
        "typical": "$100–$50k",
        "note": "Web2 ~$50k, Web3 hasta $10M crítico excepcional; distribución salvaje",
    },
    MarketSegment.CHALLENGE: {
        "min_usd": 100,
        "max_observed_usd": 30_000,
        "typical": "$100–$5k",
        "note": "Coding challenges competitivos (ej. Apify $30k 1er puesto)",
    },
    MarketSegment.HACKATHON: {
        "min_usd": 100,
        "max_observed_usd": 100_000,
        "typical": "$500–$10k",
        "note": "Premios por equipo/proyecto, no tarea individual garantizada",
    },
    MarketSegment.GRANTS: {
        "min_usd": 1_000,
        "max_observed_usd": 500_000,
        "typical": "$5k–$50k",
        "note": "Financiación de proyecto/propuesta, no pago por issue",
    },
    MarketSegment.RETROACTIVE: {
        "min_usd": 1_000,
        "max_observed_usd": 500_000,
        "typical": "$1k–$100k",
        "note": "RetroPGF / impacto pasado, selección por jurado",
    },
    MarketSegment.ECOSYSTEM_FUNDING: {
        "min_usd": 5_000,
        "max_observed_usd": 1_000_000,
        "typical": "$5k–$200k",
        "note": "Ecosystem funding (Uniswap/Solana), proyecto no tarea",
    },
}


def classify_market_segment(
    category: str | None = None,
    employment_type: str | None = None,
    platform: str | None = None,
    payment: float | None = None,
    title: str | None = None,
) -> MarketSegment:
    """Heurística determinista category+employment_type→segment (nunca raisea)."""
    cat = (category or "").lower()
    emp = (employment_type or "").lower()
    plat = (platform or "").lower()
    ttl = (title or "").lower()
    amt = float(payment or 0.0)

    # Project funding: contract/project/retainer + grant-like platforms/titles
    grant_platforms = {"gitcoin", "optimism", "uniswap", "solana", "base", "coinbase"}
    if emp in ("project", "retainer") or plat in grant_platforms or "grant" in ttl or "retropgf" in ttl:
        if "retro" in ttl:
            return MarketSegment.RETROACTIVE
        if "ecosystem" in ttl or plat in {"uniswap", "solana"}:
            return MarketSegment.ECOSYSTEM_FUNDING
        return MarketSegment.GRANTS

    if cat == "open_source" and amt <= 0:
        return MarketSegment.OSS
    if cat == "bug_bounty":
        return MarketSegment.BUG_BOUNTY
    if cat in ("security_research", "smart_contracts", "reverse_engineering", "malware_analysis"):
        # BUG_BOUNTY sólo si plataforma es programa bug bounty puro
        if plat in {"hackerone", "bugcrowd", "intigriti", "yeswehack", "immunefi", "hackenproof", "code4rena"}:
            return MarketSegment.BUG_BOUNTY
        return MarketSegment.SECURITY_OSS
    if cat == "competitions":
        if "hackathon" in ttl or amt >= 50_000:
            return MarketSegment.HACKATHON
        return MarketSegment.CHALLENGE
    if emp in ("challenge", "prize"):
        if "hackathon" in ttl:
            return MarketSegment.HACKATHON
        return MarketSegment.CHALLENGE

    return MarketSegment.DEV_BOUNTY


def classify_reward_kind(segment: MarketSegment) -> RewardKind:
    return REWARD_KIND_FOR_SEGMENT.get(segment, RewardKind.TASK_REWARD)


def get_ceiling(segment: MarketSegment) -> dict[str, Any]:
    base = MARKET_CEILINGS.get(segment, MARKET_CEILINGS[MarketSegment.DEV_BOUNTY])
    return {"segment": segment.value, "reward_kind": classify_reward_kind(segment).value, **base}


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
    """Enriquece un RankedOpportunity con rung + validación + techo económico (nunca raisea)."""
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
        # Segmento económico + techo observado (TASK_REWARD vs PROJECT_FUNDING)
        try:
            cat_val = getattr(getattr(opp, "category", ""), "value", getattr(opp, "category", ""))
            emp_val = getattr(getattr(opp, "employment_type", ""), "value", getattr(opp, "employment_type", ""))
            plat_val = getattr(getattr(opp, "platform", ""), "value", getattr(opp, "platform", ""))
            title_val = getattr(opp, "title", "") or ""
            seg = classify_market_segment(
                category=str(cat_val) if cat_val else None,
                employment_type=str(emp_val) if emp_val else None,
                platform=str(plat_val) if plat_val else None,
                payment=payment,
                title=str(title_val),
            )
            block["market_segment"] = seg.value
            block["reward_kind"] = classify_reward_kind(seg).value
            block["is_task_reward"] = classify_reward_kind(seg) == RewardKind.TASK_REWARD
            block["is_project_funding"] = classify_reward_kind(seg) == RewardKind.PROJECT_FUNDING
            ceiling = get_ceiling(seg)
            block["ceiling"] = ceiling
            block["ceiling_note"] = ceiling.get("note", "")
        except Exception:
            pass
        return block
    except Exception as exc:  # nunca romper el ranking por presentar
        logger.warning("public_work enrich falló: %s", exc)
        block = validation_block(PublicWorkRung.BEGINNER)
        block["difficulty"] = 0.5
        block["difficulty_unknown_inputs"] = True
        return block
