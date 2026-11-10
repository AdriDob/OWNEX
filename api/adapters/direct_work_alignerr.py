"""Alignerr Direct Work Adapter — AI model evaluation and data labeling platform.

Alignerr (Labelbox-led initiative) connects subject matter experts with AI labs
for model evaluation, data labeling, and alignment tasks. This adapter maps
Alignerr sources to the Direct Work Engine opportunity format.

Key features:
- Argentina-compatible payout methods (USDC, Payoneer, AirTM, crypto)
- Beginner/junior friendly — accepts beginners and individuals
- Task-based micro-work, not professional software engineering
- Outcome-based payment (per-task, not salary)
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
logger = logging.getLogger("ownex.api.direct_work.adapters.alignerr")
# Alignerr-specific platform mapping
_ALIGNERR_PLATFORM_MAP: dict[str, WorkPlatform] = {
    "alignerr": WorkPlatform.OTHER,
    "labelbox-alignerr": WorkPlatform.OTHER,
}

# Alignerr category defaults
_ALIGNERR_CATEGORY = OpportunityCategory.DATA_ANNOTATION

# Alignerr employment type
_ALIGNERR_EMPLOYMENT = EmploymentType.FREELANCE

# Alignerr default payment methods (documented)
_ALIGNERR_PAYMENT_METHODS = ["usdc", "usdt", "payoneer", "airtm", "crypto", "btc", "eth"]


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
    """Check if an Alignerr source supports Argentina payout methods."""
    # Check documented payment methods
    methods = _documented_payment_methods_for_source(source)
    for method in methods:
        key = str(method).strip().lower()
        if key in {"usdc", "usdt", "airtm", "payoneer", "btc", "eth", "crypto", "stablecoin"}:
            return True
    # Check source name/URL for Argentina signals
    name = getattr(source, "name", "") or ""
    url = getattr(source, "url", "") or ""
    text = f"{name} {url}".lower()
    argentina_keywords = ["argentina", "ar", "ar$", "usdc", "payoneer", "airtm"]
    return any(kw in text for kw in argentina_keywords)


def _documented_payment_methods_for_source(source: Any) -> list[str]:
    """Get documented payment methods for an Alignerr source."""
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


def _alignerr_payment_method_for_source(source: Any) -> PaymentMethod:
    """Map Alignerr payment methods using extended aliases."""
    for method in _documented_payment_methods_for_source(source):
        key = str(method).strip().lower()
        if key in _PARENT_PAYMENT_METHOD_ALIASES:
            return _PARENT_PAYMENT_METHOD_ALIASES[key]
    return PaymentMethod.CRYPTO


class AlignerrDweAdapter(BaseDiscoveryAdapter):
    """Direct Work Engine adapter for Alignerr platform.

    Maps Alignerr AI model evaluation and data labeling opportunities
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
        """Validate that the Alignerr source is configured."""
        return self.source is not None

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch Alignerr opportunities from the catalog source."""
        if self._catalog_source is None:
            raise RuntimeError("no catalog source loaded")

        return [self._build_opportunity(self._catalog_source)]

    def _build_opportunity(self, source: catalog.SourceDefinition) -> Opportunity:
        """Build a single Alignerr opportunity from catalog source."""
        platform = _platform_for_source(source)
        category = _category_for_source(source)
        payment_method = _alignerr_payment_method_for_source(source)
        employment_type = _employment_type_for_source(source)
        source_id = getattr(source, "id", None) or getattr(source, "name", "unknown")
        url = _normalize_url(getattr(source, "url", "") or "")

        # Argentina compatibility check
        argentina_compatible = _is_argentina_compatible_source(source)

        # Experience requirement - always NONE for Alignerr (beginner-friendly)
        experience_requirement = ExperienceRequirement.NONE

        opp = self._create_opportunity(
            external_id=f"alignerr-{source_id}",
            title=f"Alignerr opportunity from {getattr(source, 'name', 'unknown')}",
            platform=platform,
            category=category,
            url=url,
            description=(
                "Alignerr AI model evaluation and data labeling task. "
                "Tasks include evaluating AI model responses, data annotation, "
                "and model alignment work. Beginner-friendly, remote, task-based."
            ),
            company=getattr(source, "name", "") or "",
            payment=10.0 if _has_any_known_payment_entry(source) else 0.0,
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
            estimated_time_hours=5.0,
            portfolio_required=False,
            interview_required=False,
            technical_test_required=False,
        )

        # Post-creation corrections
        opp.employment_type = employment_type
        opp.rate_source = "catalog"

        return opp

    @staticmethod
    def _resolve_alignerr_platform(source: Any) -> WorkPlatform:
        """Resolve the platform for an Alignerr source."""
        name = getattr(source, "name", "") or ""
        url = getattr(source, "url", "") or ""
        text = f"{name} {url}".lower()

        # Check known Alignerr platform names
        for key, platform in _ALIGNERR_PLATFORM_MAP.items():
            if key in text or key in name:
                return platform

        # Default: other
        return WorkPlatform.OTHER


def build_alignerr_adapter() -> AlignerrDweAdapter:
    """Build the Alignerr DWE adapter instance."""
    from cores.direct_work_engine.discovery import DiscoverySource

    source = DiscoverySource(
        name="alignerr",
        platform=WorkPlatform.OTHER,
        categories=[OpportunityCategory.DATA_ANNOTATION],
        tier=2,
        analysis_cadence_hours=24,
    )
    adapter = AlignerrDweAdapter(source=source)
    return adapter
