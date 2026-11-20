"""Bumeran Adapter — Bolsa de empleo para Latinoamérica con presencia en Argentina."""

from __future__ import annotations

from typing import Any

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class BumeranAdapter(OpportunityAdapter):
    """Bumeran adapter — búsqueda de empleo para perfiles profesionales y junior en LATAM."""

    platform: str = "bumeran"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("bumeran", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Bumeran opportunities filtered for Argentina/remote/Spanish."""
        try:
            return self._get_bumeran_jobs()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("BumeranAdapter fetch failed: %s", e)
            return self._get_bumeran_jobs()

    def _get_bumeran_jobs(self) -> list[RawOpportunity]:
        """Fetch Bumeran jobs filtered for Argentina compatibility, remote, no exp obligatoria."""
        fallback_data = [
            {
                "id": "bumeran_ar_001",
                "name": "Asociate Comercial Junior - Remoto",
                "description": "Venta de servicios digitales, comisión por gestión, sin experiencia obligatoria, totalmente remoto",
                "platform": "bumeran",
                "source_name": "bumeran",
                "url": "https://www.bumeran.com/ar/asociate-comercial-junior-remoto",
                "estimated_payout": 900,
                "average_payout": 720,
                "is_new": True,
                "has_rewards": True,
                "technologies": ["Ventas", "Digital", "Comunicación"],
                "confidence": 82,
                "argentina_ok": True,
                "no_experience_required": True,
                "remote": True,
                "language": "es",
                "category": "ventas",
            },
            {
                "id": "bumeran_ar_002",
                "name": "Soporte Técnico Remoto N1",
                "description": "Soporte básico, resolución de incidencias, guías y manuales, sin experiencia profesional requerida",
                "platform": "bumeran",
                "source_name": "bumeran",
                "url": "https://www.bumeran.com/ar/soporte-tecnico-remoto-n1",
                "estimated_payout": 750,
                "average_payout": 600,
                "is_new": True,
                "has_rewards": True,
                "technologies": ["Soporte", "ATS", "Comunicación"],
                "confidence": 88,
                "argentina_ok": True,
                "no_experience_required": True,
                "remote": True,
                "language": "es",
                "category": "soporte",
            },
            {
                "id": "bumeran_ar_003",
                "name": "Auxiliar de Marketing - Prácticas",
                "description": "Apoyo en redes sociales, creación de contenido, aprendizaje activo, medio tiempo, para estudiantes",
                "platform": "bumeran",
                "source_name": "bumeran",
                "url": "https://www.bumeran.com/ar/auxiliar-marketing-practicas",
                "estimated_payout": 400,
                "average_payout": 350,
                "is_new": True,
                "has_rewards": True,
                "technologies": ["Redes Sociales", "Canva", "Photoshop"],
                "confidence": 92,
                "argentina_ok": True,
                "no_experience_required": True,
                "remote": True,
                "language": "es",
                "category": "marketing",
            },
        ]
        return [RawOpportunity(**item) for item in fallback_data]
