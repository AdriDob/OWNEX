"""Hermes Direct Work Adapter prototype (Fase C — Contract Verification).

Puente entre fuentes de trabajo de Hermes y el motor DWE. Hereda
OwnWorkCatalogAdapter para reutilizar el mapeo base (platform, category,
payment_method, employment_type, entry_mechanism, international_payment,
experience_requirement, rate_source, technology_tags) y agrega campos
específicos de Hermes cuando están disponibles en la fuente del catálogo.

NO afirma verificación de pago, compatibilidad Argentina, ni
FULLY_ELIGIBLE para ninguna fuente.
"""

from __future__ import annotations

from typing import Any

from api.adapters.own_work_catalog_adapter import (
    _category_for_source,
    _employment_type_for_source,
    _entry_mechanism_for_source,
    _experience_requirement_for_source,
    _has_any_known_payment_entry,
    _international_payment_for_source,
    _normalize_url,
    _payment_method_for_source,
    _platform_for_source,
    _technology_tags_for_source,
)
from cores.direct_work_engine import models as dwe_models
from cores.direct_work_engine.discovery import BaseDiscoveryAdapter


class HermesDirectWorkAdapter(BaseDiscoveryAdapter):
    """Adaptador prototipo para fuentes de trabajo de Hermes.

    Recibe un DiscoverySource en __init__ (contrato de BaseDiscoveryAdapter)
    y opcionalmente una fuente del catálogo Hermes para mapear campos
    específicos de Hermes en las oportunidades.

    NO afirma verificación de pago, compatibilidad Argentina, ni
    FULLY_ELIGIBLE para ninguna fuente.
    """

    def __init__(
        self,
        source: dwe_models.DiscoverySource,
        hermes_source: Any | None = None,
    ) -> None:
        super().__init__(source)
        self.hermes_source = hermes_source

    def load_catalog_source(self, source: Any) -> None:
        """Registra la fuente del catálogo Hermes para mapeo de campos."""
        self.hermes_source = source

    async def validate_connection(self) -> bool:
        return True

    async def fetch_opportunities(self) -> list[dwe_models.Opportunity]:
        return self._build_opportunities()

    def _build_opportunities(self) -> list[dwe_models.Opportunity]:
        source = self.hermes_source
        if source is None:
            return []

        platform = _platform_for_source(source)
        category = _category_for_source(source)
        payment_method = _payment_method_for_source(source)
        employment_type = _employment_type_for_source(source)
        source_id = getattr(source, "id", None) or getattr(source, "name", "unknown")
        url = _normalize_url(getattr(source, "url", "") or "")

        opp = self._create_opportunity(
            external_id=f"hermes-prototype-{source_id}",
            title=f"Hermes opportunity from {getattr(source, 'name', 'unknown')}",
            platform=platform,
            category=category,
            url=url,
            description=("Hermes prototype opportunity for contract verification. This is NOT a real listing and must not be used for claim."),
            company=getattr(source, "name", "") or "",
            payment=10.0 if _has_any_known_payment_entry(source) else 0.0,
            currency="USD",
            payment_method=payment_method,
            registration_required=bool(getattr(source, "requires_account", False)),
            accepts_beginner=True,
            accepts_individuals=True,
            asynchronous=True,
        )
        # Post-creation corrections, same pattern as the base adapter
        opp.employment_type = employment_type
        opp.entry_mechanism = _entry_mechanism_for_source(source)
        opp.international_payment = _international_payment_for_source(source)
        opp.rate_source = "catalog"
        opp.experience_requirement = _experience_requirement_for_source(source)
        opp.technology_tags = _technology_tags_for_source(source)

        # NOTE: Hermes-specific analysis fields (heuristics_analyzed,
        # analysis_complete, cached_analysis, analysis_revision,
        # analysis_started_at) are intentionally NOT set on the Opportunity
        # because the engine model uses __slots__ and blocks injection of
        # fields that do not exist in the model. These fields live only in
        # the catalog source object (this file's own space) and are NOT
        # transferred to the engine's Opportunity. See
        # cores/opportunity/catalog_contract.md section 9.4.

        return [opp]
