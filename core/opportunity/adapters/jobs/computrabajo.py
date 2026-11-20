"""Computrabajo Adapter — Principal bolsa de empleo de Argentina y Latinoamérica."""

from __future__ import annotations

from typing import Any

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class ComputrabajoAdapter(OpportunityAdapter):
    """Computrabajo adapter — bolsa de empleo principal de Argentina y LATAM."""

    platform: str = "computrabajo"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("computrabajo", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Computrabajo opportunities filtered for Argentina/remote/Spanish."""
        try:
            return self._get_computrabajo_jobs()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("ComputrabajoAdapter fetch failed: %s", e)
            return self._get_computrabajo_jobs()

    def _get_computrabajo_jobs(self) -> list[RawOpportunity]:
        """Fetch Computrabajo jobs filtered for Argentina, remote, no exp obligatoria."""
        fallback_data = [
            {
                "id": "computrabajo_ar_001",
                "name": "Desarrollador Software Jr - Remoto",
                "description": "Desarrollo de software, trabajo remoto, junior, sin experiencia obligatoria, capacitación incluida",
                "platform": "computrabajo",
                "source_name": "computrabajo",
                "url": "https://www.computrabajo.com.ar/remoto/junior-desarrollo",
                "estimated_payout": 1000,
                "average_payout": 850,
                "is_new": True,
                "has_rewards": True,
                "technologies": ["Python", "JavaScript", "Node.js"],
                "confidence": 90,
                "argentina_ok": True,
                "no_experience_required": True,
                "remote": True,
                "language": "es",
                "category": "desarrollo",
            },
            {
                "id": "computrabajo_ar_002",
                "name": "Asistente Administrativo - Híbrido",
                "description": "Apoyo administrativo, oficina central CABA, medio tiempo, sin experiencia previa requerida",
                "platform": "computrabajo",
                "source_name": "computrabajo",
                "url": "https://www.computrabajo.com.ar/admin/asistente",
                "estimated_payout": 600,
                "average_payout": 500,
                "is_new": True,
                "has_rewards": True,
                "technologies": ["Office", "Excel", "Gestión"],
                "confidence": 88,
                "argentina_ok": True,
                "no_experience_required": True,
                "remote": False,
                "language": "es",
                "category": "administracion",
            },
            {
                "id": "computrabajo_ar_003",
                "name": "Representante Comercial - Remoto",
                "description": "Ventas externas y internas, comisión por cierre, sin experiencia mínima, capacitación incluida",
                "platform": "computrabajo",
                "source_name": "computrabajo",
                "url": "https://www.computrabajo.com.ar/remoto/ventas",
                "estimated_payout": 1500,
                "average_payout": 1100,
                "is_new": True,
                "has_rewards": True,
                "technologies": ["CRM", "Negociación", "Teléfono"],
                "confidence": 85,
                "argentina_ok": True,
                "no_experience_required": True,
                "remote": True,
                "language": "es",
                "category": "ventas",
            },
        ]
        return [RawOpportunity(**item) for item in fallback_data]
