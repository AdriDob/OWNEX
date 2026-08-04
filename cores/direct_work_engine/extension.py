"""Extension Evaluator — reasons about whether OWNEX should acquire a new capability.

The user (or the copilot) can propose any extension in the OWNEX terminal. OWNEX
does not install blindly: it evaluates whether the capability is aligned with its
mission (income, automation, learning), whether it duplicates something that
already exists, and explains the reasoning so the user can approve or decline —
always with a logical, auditable basis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("ownex.direct_work_engine.extension")

# Existing capabilities — proposing these is a duplicate, not an extension.
_KNOWN_CAPABILITIES: list[str] = [
    "discover",
    "recommend",
    "score",
    "negotiate",
    "skill gap",
    "learn",
    "work bank",
    "voice assistant",
    "zero barrier",
    "opportunity",
    "bounty",
    "profile",
    "feedback",
    "scanner",
    "platform adapter",
]

# Keywords that align a proposal with the OWNEX mission.
_ALIGNED_KEYWORDS: list[str] = [
    "ingreso",
    "income",
    "oportunidad",
    "opportunity",
    "bounty",
    "automat",
    "automation",
    "aprend",
    "learn",
    "pago",
    "payment",
    "cobrar",
    "scan",
    "plataforma",
    "platform",
    "perfil",
    "profile",
    "entrega",
    "deliver",
    "adaptador",
    "adapter",
    "work",
    "empleo",
    "remote",
    "api",
]

# Keywords that suggest high effort or risk (need stronger value to approve).
_RISK_KEYWORDS: list[str] = [
    "completo",
    "full",
    "entero",
    "masivo",
    "masive",
    "gpu",
    "modelo",
    "model",
    "browser",
    "navegador",
]


@dataclass(slots=True)
class ExtensionProposal:
    """Verdict for a proposed capability extension."""

    name: str
    description: str
    proposed_by: str
    recommendation: str = "decline"  # approve | decline
    value_score: float = 0.0
    duplicates_existing: bool = False
    high_risk: bool = False
    reasoning: list[str] = field(default_factory=list)


class ExtensionEvaluator:
    """Decides whether a capability extension is convenient for OWNEX."""

    def evaluate(self, name: str, description: str, proposed_by: str = "user") -> ExtensionProposal:
        text = f"{name} {description}".lower()

        aligned = sum(1 for kw in _ALIGNED_KEYWORDS if kw in text)
        duplicated = any(kw in text for kw in _KNOWN_CAPABILITIES)
        high_risk = any(kw in text for kw in _RISK_KEYWORDS)

        value_score = 0.3 + min(0.4, aligned * 0.1)
        if duplicated:
            value_score -= 0.35
        if high_risk:
            value_score -= 0.1
        value_score = max(0.0, min(1.0, value_score))

        recommend_approve = value_score >= 0.45 and (aligned >= 2 or not duplicated)
        recommendation = "approve" if recommend_approve else "decline"

        reasoning = self._build_reasoning(name, aligned, duplicated, high_risk, value_score, recommendation)

        return ExtensionProposal(
            name=name,
            description=description,
            proposed_by=proposed_by,
            recommendation=recommendation,
            value_score=round(value_score, 2),
            duplicates_existing=duplicated,
            high_risk=high_risk,
            reasoning=reasoning,
        )

    @staticmethod
    def _build_reasoning(
        name: str,
        aligned: int,
        duplicated: bool,
        high_risk: bool,
        value_score: float,
        recommendation: str,
    ) -> list[str]:
        reasons = []
        if aligned >= 2:
            reasons.append(f"Está alineada con la misión ({aligned} señales de ingresos/automatización/aprendizaje).")
        else:
            reasons.append("No está claramente alineada con ingresos, automatización o aprendizaje.")
        if duplicated:
            reasons.append("Duplica una capacidad que ya existe en OWNEX — revisar antes de agregar.")
        if high_risk:
            reasons.append("Implica esfuerzo o riesgo alto; solo justifica si el valor es claro.")
        reasons.append(f"Score de valor: {value_score:.0%}.")
        reasons.append(
            f"Recomendación: {'aprobada, se puede adquirir' if recommendation == 'approve' else 'rechazada por ahora'}. "
            "OWNEX nunca instala una extensión sin tu aprobación."
        )
        return reasons
