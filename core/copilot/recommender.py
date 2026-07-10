"""Recommender — next-step recommendation engine."""

from __future__ import annotations

import logging
from typing import Any

from core.copilot.context import CopilotContext

logger = logging.getLogger("orion.core.copilot.recommender")


class Recommendation:
    """A single recommendation with rationale."""

    def __init__(
        self,
        action: str,
        description: str,
        priority: int = 0,
        reason: str = "",
        risk: float = 0.0,
    ) -> None:
        self.action = action
        self.description = description
        self.priority = priority
        self.reason = reason
        self.risk = risk

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "description": self.description,
            "priority": self.priority,
            "reason": self.reason,
            "risk": self.risk,
        }


class Recommender:
    """Recommends the next action based on context."""

    def recommend(self, context: CopilotContext) -> list[Recommendation]:
        """Generate prioritized recommendations."""
        recs: list[Recommendation] = []
        finding = context.finding or {}

        # No finding → start discovery
        if not finding:
            recs.append(
                Recommendation(
                    "discover_targets",
                    "Iniciar descubrimiento de nuevos targets",
                    priority=1,
                    reason="No hay hallazgos activos para analizar",
                    risk=0.1,
                )
            )
            return recs

        # Finding without evidence
        evidence = finding.get("evidence", []) or []
        if not evidence:
            recs.append(
                Recommendation(
                    "gather_evidence",
                    "Recolectar evidencia del hallazgo",
                    priority=5,
                    reason="Hallazgo sin evidencia — no se puede verificar",
                    risk=0.2,
                )
            )

        v_type = (finding.get("vulnerability_type") or finding.get("type") or "").lower()

        # Specific recommendations per type
        type_recs: dict[str, list[Recommendation]] = {
            "idor": [
                Recommendation(
                    "verify_ownership",
                    "Verificar que otro usuario no pueda acceder al recurso",
                    priority=5,
                    reason="IDOR requiere confirmación de acceso cruzado",
                    risk=0.3,
                ),
            ],
            "ssrf": [
                Recommendation(
                    "verify_external_interaction",
                    "Confirmar interacción con servidor externo",
                    priority=5,
                    reason="SSRF necesita evidencia de callback externo",
                    risk=0.3,
                ),
            ],
            "xss": [
                Recommendation(
                    "verify_reflection",
                    "Confirmar que el payload se ejecuta en el navegador",
                    priority=5,
                    reason="XSS necesita prueba de ejecución de JS",
                    risk=0.3,
                ),
            ],
            "sqli": [
                Recommendation(
                    "verify_data_extraction",
                    "Intentar extraer datos de la base de datos",
                    priority=5,
                    reason="SQLi necesita prueba de extracción de datos",
                    risk=0.5,
                ),
            ],
        }

        for key, rec_list in type_recs.items():
            if key in v_type:
                recs.extend(rec_list)
                break

        # Confidence-based
        confidence = context._effective_confidence()
        if confidence < 0.40:
            recs.append(
                Recommendation(
                    "human_review",
                    "Solicitar revisión humana — confianza muy baja",
                    priority=4,
                    reason=f"Confianza {confidence:.0%} por debajo del umbral mínimo",
                    risk=0.1,
                )
            )
        elif confidence >= 0.85:
            recs.append(
                Recommendation(
                    "consider_report",
                    "Confianza suficiente para generar reporte",
                    priority=3,
                    reason=f"Confianza {confidence:.0%} supera umbral de reporte",
                    risk=0.6,
                )
            )

        # Sort by priority descending
        recs.sort(key=lambda r: r.priority, reverse=True)

        return recs
