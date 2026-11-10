"""datannotation Direct Work Adapter — Data annotation and AI training platform.

datannotation provides data annotation, labeling, and AI training tasks for
machine learning model development. This adapter maps datannotation sources
to the Direct Work Engine opportunity format.

Key features:
- Argentina-compatible payout methods (USDC, Payoneer, AirTM, crypto)
- Beginner/junior friendly — explicitly accepts beginners
- Image, video, text, and audio annotation tasks
- Per-task payment, not salary-based
"""

from __future__ import annotations

import logging
from typing import Any

from api.adapters.own_work_catalog_adapter import (
    _category_for_source,
    _employment_type_for_source,
    _entry_mechanism_for_source,
    _has_any_known_payment_entry,
    _international_payment_for_source,
    _normalize_url,
    _platform_for_source,
    _technology_tags_for_source,
)
from core.opportunity import global_sources as catalog
from core.opportunity.adapter_payment_docs import KNOWN_PAYMENT_METHODS
from cores.direct_work_engine.discovery import BaseDiscoveryAdapter
from cores.direct_work_engine.models import (
    EmploymentType,
    ExperienceRequirement,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)

try:
    from core.opportunity.own_work_sources import SOURCE_PLATFORM_MAP
except ImportError:
    SOURCE_PLATFORM_MAP = {}
logger = logging.getLogger("ownex.api.direct_work.adapters.datannotation")
# datannotation platform mapping
_DATANNOTATION_PLATFORM_MAP: dict[str, WorkPlatform] = {
    "datannotation": WorkPlatform.OTHER,
    "datannotation-platform": WorkPlatform.OTHER,
    "data-annotation": WorkPlatform.OTHER,
}

# datannotation category defaults
_DATANNOTATION_CATEGORY = OpportunityCategory.DATA_ANNOTATION

# datannotation employment type
_DATANNOTATION_EMPLOYMENT = EmploymentType.FREELANCE


def _platform_from_name(name: str) -> WorkPlatform | None:
    """Resolve platform from source name using the catalog map."""
    platform_key = SOURCE_PLATFORM_MAP.get(name)
    if not platform_key:
        return None
    for member in WorkPlatform:
        if member.value == platform_key:
            return member
    return None


def _is_argentina_compatible_source(source: Any) -> bool:
    """Check if a datannotation source supports Argentina payout methods."""
    methods = _documented_payment_methods_for_source(source)
    for method in methods:
        key = str(method).strip().lower()
        if key in {"usdc", "usdt", "airtm", "payoneer", "btc", "eth", "crypto", "stablecoin"}:
            return True
    name = getattr(source, "name", "") or ""
    url = getattr(source, "url", "") or ""
    text = f"{name} {url}".lower()
    argentina_keywords = ["argentina", "ar", "usdc", "payoneer", "airtm"]
    return any(kw in text for kw in argentina_keywords)


def _documented_payment_methods_for_source(source: Any) -> list[str]:
    """Get documented payment methods for a datannotation source."""
    methods = getattr(source, "payment_methods", None)
    if isinstance(methods, (list, tuple, set)) and methods:
        return [str(method) for method in methods]
    name = getattr(source, "name", None)
    if name:
        doc = KNOWN_PAYMENT_METHODS.get(str(name))
        if doc:
            raw = doc.get("methods")
            if isinstance(raw, list):
                return [str(method) for method in raw]
    return []


_PARENT_PAYMENT_METHOD_ALIASES: dict[str, PaymentMethod] = {
    "crypto": PaymentMethod.CRYPTO,
    "stablecoin": PaymentMethod.STABLECOIN,
    "usdc": PaymentMethod.STABLECOIN,
    "usdt": PaymentMethod.STABLECOIN,
    "paypal": PaymentMethod.PAYPAL,
    "payoneer": PaymentMethod.PAYONEER,
    "wise": PaymentMethod.WISE,
    "bank_transfer": PaymentMethod.BANK_WIRE,
    "bank_wire": PaymentMethod.BANK_WIRE,
    "bank": PaymentMethod.BANK_WIRE,
    "gift_card": PaymentMethod.GIFT_CARD,
    "platform_credit": PaymentMethod.PLATFORM_CREDIT,
}


def _datannotation_payment_method_for_source(source: Any) -> PaymentMethod:
    """Map datannotation payment methods using extended aliases."""
    for method in _documented_payment_methods_for_source(source):
        key = str(method).strip().lower()
        if key in _PARENT_PAYMENT_METHOD_ALIASES:
            return _PARENT_PAYMENT_METHOD_ALIASES[key]
    return PaymentMethod.STABLECOIN


class DatannotationDweAdapter(BaseDiscoveryAdapter):
    """Direct Work Engine adapter for datannotation platform.

    Maps datannotation data annotation and AI training opportunities
    to the DWE opportunity format. Supports Argentina-compatible payouts
    and beginner-friendly experience requirements.
    """

    def __init__(self, source: Any | None = None) -> None:
        super().__init__(source)
        self._catalog_source: catalog.SourceDefinition | None = None

    def load_catalog_source(self, source: catalog.SourceDefinition) -> None:
        """Load the proprietary catalog source definition."""
        self._catalog_source = source

    async def validate_connection(self) -> bool:
        """Validate that the datannotation source is configured."""
        return self.source is not None

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch datannotation opportunities from the catalog source."""
        if self._catalog_source is None:
            raise RuntimeError("no catalog source loaded")

        return [self._build_opportunity(self._catalog_source)]

    def _build_opportunity(self, source: catalog.SourceDefinition) -> Opportunity:
        """Build a single datannotation opportunity from catalog source."""
        platform = _platform_for_source(source)
        category = _category_for_source(source)
        payment_method = _datannotation_payment_method_for_source(source)
        employment_type = _employment_type_for_source(source)
        source_id = getattr(source, "id", None) or getattr(source, "name", "unknown")
        url = _normalize_url(getattr(source, "url", "") or "")

        # Argentina compatibility check
        argentina_compatible = _is_argentina_compatible_source(source)

        # Experience requirement - always NONE for datannotation (beginner-friendly)
        experience_requirement = ExperienceRequirement.NONE

        opp = self._create_opportunity(
            external_id=f"datannotation-{source_id}",
            title=f"datannotation opportunity from {getattr(source, 'name', 'unknown')}",
            platform=platform,
            category=category,
            url=url,
            description=(
                "datannotation data annotation and AI training task opportunity. "
                "Tasks include image/video/text/audio annotation, model labeling, "
                "and dataset creation for machine learning. Beginner-friendly, "
                "remote, per-task payment."
            ),
            company=getattr(source, "name", "") or "",
            payment=8.0 if _has_any_known_payment_entry(source) else 0.0,
            currency="USD",
            payment_method=payment_method,
            registration_required=bool(getattr(source, "requires_account", False)),
            accepts_beginner=True,
            accepts_individuals=True,
            asynchronous=True,
            argentina_compatible=argentina_compatible,
            experience_requirement=experience_requirement,
            entry_mechanism=_entry_mechanism_for_source(source),
            international_payment=_international_payment_for_source(source),
            technology_tags=_technology_tags_for_source(source),
            difficulty="beginner",
            estimated_time_hours=4.0,
            portfolio_required=False,
            interview_required=False,
            technical_test_required=False,
        )

        # Post-creation corrections
        opp.employment_type = employment_type
        opp.rate_source = "catalog"

        return opp

    @staticmethod
    def _resolve_datannotation_platform(source: Any) -> WorkPlatform:
        """Resolve the platform for a datannotation source."""
        name = getattr(source, "name", "") or ""
        url = getattr(source, "url", "") or ""
        text = f"{name} {url}".lower()

        # Check known datannotation platform names
        for key, platform in _DATANNOTATION_PLATFORM_MAP.items():
            if key in text or key in name:
                return platform

        # Default: other
        return WorkPlatform.OTHER


def build_datannotation_adapter() -> DatannotationDweAdapter:
    """Build the datannotation DWE adapter instance."""
    from cores.direct_work_engine.discovery import DiscoverySource
    from cores.direct_work_engine.models import OpportunityCategory, WorkPlatform

    source = DiscoverySource(
        name="datannotation",
        platform=WorkPlatform.OTHER,
        categories=[OpportunityCategory.DATA_ANNOTATION],
        tier=2,
        analysis_cadence_hours=24,
    )
    adapter = DatannotationDweAdapter(source=source)
    return adapter
