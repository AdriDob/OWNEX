"""Proprietary work-source catalog adapter for the direct_work discovery engine (prototype).

Own Work Catalog bridge (Phase C prototype):
- This adapter is the FIRST cut only.
- It converts ONE ProprietarySourceDefinition into ONE OPORPORTUNITY format accepted by the direct_work engine.
- It exists SOLELY as a compatibility probe for the contract: it does NOT register real world sources.

Contract:
- SourceDefinition is the rich metadata source model for the OWNEX catalog.
- DiscoverySource and Opportunity are the direct_work engine models.
- adapters must subclass BaseDiscoveryAdapter and implement fetch_opportunities() -> list[Opportunity] and validate_connection() -> None.

Limitations on mapping (claims of payment eligibility are NOT made here):
- platform: maps only recognized OWNEX catalog sources that are a subtype of source.type values that have a known platform in DWE.
- category: processes categories to what the engine accepts; if a category is not recognized, logs it as "unknown" and uses DEV_BOUNTY as fallback.
- payment_method: uses documented payment methods from the source records or payment docs ONLY. If a source has no documented payment method, the source is annotated as "undocumented" with platform_credit as a placeholder.
- payment_verified, payout_verified, argentina_compatible, withdrawal_verified, min_payment_usd, max_payment_usd, PaymentMethod.UNKNOWN are NOT set here: they remain UNKNOWN row in the adapter output.
- the existing Unknown sources will NOT be converted to false, verified, or FULLY_ELIGIBLE — they remain in the proprietary catalog only, linked by stable ID.

Current sources supported (prototype single-source): algora.

Excluded from prototype: all other 18 base sources + 5 extension sources from own_work_sources_extensions. They remain in the catalog until this contract is fully verified.

Reference: API contracts: api/routers/direct_work.py, api/adapters/__init__.py, api/adapters/direct_work_bugbounty.py, api/adapters/direct_work_opire.py
"""

from __future__ import annotations

import logging
from typing import Any

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    EmploymentType,
    EntryMechanism,
    ExperienceRequirement,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)
from cores.opportunity import global_sources as catalog
from cores.opportunity.source_families import SourceFamily, canonical_for_family
from cores.opportunity.source_payment_docs import KNOWN_PAYMENT_METHODS
from cores.work_taxonomy import to_canonical

try:
    from cores.opportunity.own_work_sources import SOURCE_PLATFORM_MAP
except ImportError:
    SOURCE_PLATFORM_MAP = {}


def _platform_from_name(name: str) -> WorkPlatform | None:
    """Resolve a platform from a source name using the catalog-side map.

    The map stores platform *values* (lowercase identifiers), not member names,
    so we resolve by value.
    """
    platform_key = SOURCE_PLATFORM_MAP.get(name)
    if not platform_key:
        return None
    for member in WorkPlatform:
        if member.value == platform_key:
            return member
    return None


logger = logging.getLogger("ownwork.api.adapters.catalog")


def _platform_for_source(source: Any) -> WorkPlatform | None:
    """Map a proprietary source to a WorkPlatform the engine knows.

    Only mapped when a source has a known platform in engine; otherwise
    the source remains in catalog and is NOT injected into the engine.
    """
    platform_str = getattr(source, "platform", None)
    if platform_str is not None:
        platform_value = (platform_str.value if hasattr(platform_str, "value") else str(platform_str)).strip().lower()
        mapping: dict[str, WorkPlatform] = {
            "hackerone": WorkPlatform.HACKERONE,
            "immunefi": WorkPlatform.IMMUNEFI,
            "algora": WorkPlatform.ALGORA,
            "superteam": WorkPlatform.SUPER_TEAM,
            "opire": WorkPlatform.OPIRE,
            "issuehunt": WorkPlatform.ISSUE_HUNT,
        }
        if platform_value in mapping:
            return mapping[platform_value]
    name = getattr(source, "name", None)
    if name:
        return _platform_from_name(str(name))
    return None


def _category_for_source(source: Any) -> OpportunityCategory:
    """Map source.category to an engine-accepted category."""
    category = getattr(source, "category", None)
    family_raw = getattr(source, "source_family", "")
    if family_raw:
        try:
            return canonical_for_family(SourceFamily(str(family_raw)))
        except ValueError:
            pass
    if isinstance(category, OpportunityCategory):
        return category
    if isinstance(category, catalog.OpportunityCategory):
        return to_canonical(category)
    category_str = str(category).strip().lower() if category is not None else ""
    mapping: dict[str, OpportunityCategory] = {
        "bug_bounty": OpportunityCategory.BUG_BOUNTY,
        "dev_bounty": OpportunityCategory.DEV_BOUNTY,
        "data_entry": OpportunityCategory.DATA_ANNOTATION,
        "security_research": OpportunityCategory.SECURITY_RESEARCH,
        "oss_bounties": OpportunityCategory.OSS_BOUNTIES,
        "ai_evaluation": OpportunityCategory.AI_EVALUATION,
        "data_annotation": OpportunityCategory.DATA_ANNOTATION,
        "software_engineering": OpportunityCategory.SOFTWARE_ENGINEERING,
    }
    if category_str in mapping:
        return mapping[category_str]
    logger.info("Unknown category for source %s: %s", getattr(source, "name", "unknown"), category_str)
    return OpportunityCategory.DEV_BOUNTY


_PAYMENT_METHOD_ALIASES: dict[str, PaymentMethod] = {
    "crypto": PaymentMethod.CRYPTO,
    "stablecoin": PaymentMethod.STABLECOIN,
    "paypal": PaymentMethod.PAYPAL,
    "payoneer": PaymentMethod.PAYONEER,
    "wise": PaymentMethod.WISE,
    "bank_transfer": PaymentMethod.BANK_WIRE,
    "bank_wire": PaymentMethod.BANK_WIRE,
    "bank": PaymentMethod.BANK_WIRE,
    "gift_card": PaymentMethod.GIFT_CARD,
    "platform_credit": PaymentMethod.PLATFORM_CREDIT,
}


def _documented_payment_methods_for_source(source: Any) -> list[str]:
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


def _payment_method_for_source(source: Any) -> PaymentMethod:
    """Map documented payment methods.

    Explicit ``source.payment_methods`` win; otherwise fall back to the curated
    payment documentation by source name. Unknown/undocumented sources stay
    ``PLATFORM_CREDIT`` and remain catalog-only.
    """
    for method in _documented_payment_methods_for_source(source):
        key = str(method).strip().lower()
        if key in _PAYMENT_METHOD_ALIASES:
            return _PAYMENT_METHOD_ALIASES[key]
    return PaymentMethod.PLATFORM_CREDIT


def _employment_type_for_source(source: Any) -> EmploymentType:
    etype = getattr(source, "employment_type", None)
    if isinstance(etype, EmploymentType):
        return etype
    raw = str(etype).strip().lower() if etype is not None else ""
    mapping: dict[str, EmploymentType] = {
        "bounty": EmploymentType.BOUNTY,
        "microtask": EmploymentType.MICROTASK,
        "contract": EmploymentType.CONTRACT,
        "freelance": EmploymentType.FREELANCE,
        "full_time": EmploymentType.FULL_TIME,
        "challenge": EmploymentType.CHALLENGE,
        "prize": EmploymentType.PRIZE,
        "open_call": EmploymentType.OPEN_CALL,
    }
    if raw in mapping:
        return mapping[raw]
    logger.info("Unknown employment_type for source %s: %s", getattr(source, "name", "unknown"), raw)
    return EmploymentType.BOUNTY


def _has_any_known_payment_entry(source: Any) -> bool:
    return any(str(method).strip().lower() in _PAYMENT_METHOD_ALIASES for method in _documented_payment_methods_for_source(source))


def _entry_mechanism_for_source(source: Any) -> EntryMechanism:
    apply_method = getattr(source, "apply_method", None)
    raw = str(apply_method).strip().lower() if apply_method is not None else ""
    mapping: dict[str, EntryMechanism] = {
        "apply_on_platform": EntryMechanism.REGISTRATION,
        "apply": EntryMechanism.REGISTRATION,
        "registration": EntryMechanism.REGISTRATION,
        "direct": EntryMechanism.DIRECT,
        "assessment": EntryMechanism.ASSESSMENT,
        "test": EntryMechanism.TEST,
        "interview": EntryMechanism.INTERVIEW,
        "portfolio": EntryMechanism.PORTFOLIO,
        "invitation": EntryMechanism.INVITATION,
        "training": EntryMechanism.TRAINING,
        "experience_review": EntryMechanism.EXPERIENCE_REVIEW,
    }
    if raw in mapping:
        return mapping[raw]
    logger.info("Unknown apply_method for source %s: %s", getattr(source, "name", "unknown"), raw)
    return EntryMechanism.DIRECT


def _international_payment_for_source(source: Any) -> bool | None:
    explicit = getattr(source, "international_payment", None)
    if isinstance(explicit, bool):
        return explicit
    if isinstance(explicit, str):
        normalized = explicit.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    region = getattr(source, "region", None)
    if region and str(region).strip().lower() not in ("", "argentina", "ar"):
        return True
    return None


def _experience_requirement_for_source(source: Any) -> ExperienceRequirement:
    requires_experience = getattr(source, "requires_experience", None)
    if requires_experience in (True, "true", "1", 1):
        return ExperienceRequirement.REQUIRED
    if requires_experience in (False, "false", "0", 0):
        return ExperienceRequirement.NONE
    raw = str(requires_experience).strip().lower()
    mapping: dict[str, ExperienceRequirement] = {
        "optional": ExperienceRequirement.OPTIONAL,
        "preferred": ExperienceRequirement.PREFERRED,
        "required": ExperienceRequirement.REQUIRED,
        "none": ExperienceRequirement.NONE,
    }
    if raw in mapping:
        return mapping[raw]
    logger.info("Unknown requires_experience for source %s: %s", getattr(source, "name", "unknown"), raw)
    return ExperienceRequirement.NONE


def _technology_tags_for_source(source: Any) -> list[str]:
    tags: list[str] = []
    for attr in ("technology_tags", "tags"):
        value = getattr(source, attr, None)
        values = value if isinstance(value, (list, tuple, set)) else [value]
        for item in values:
            if not isinstance(item, str):
                continue
            tag = item.strip()
            if tag and tag not in tags:
                tags.append(tag)
    return tags


def _normalize_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    if not raw_url.startswith(("http://", "https://")):
        raw_url = "https://" + raw_url
    return raw_url


class OwnWorkCatalogAdapter(BaseDiscoveryAdapter):
    """Prototype adapter bridging OWNEX proprietary work sources to the DWE.

    This is ONE source from the start so we can verify the format exchange contract.
    No production registrations. The adapter is intentionally NOT registered in
    the engine's registry from this prototype file.
    """

    def __init__(self, source: DiscoverySource) -> None:
        super().__init__(source)
        self._catalog_source: catalog.SourceDefinition | None = None

    def load_catalog_source(self, source: catalog.SourceDefinition) -> None:
        self._catalog_source = source

    async def validate_connection(self) -> bool:
        """Validate that the engine source is configured."""
        return self.source is not None

    async def fetch_opportunities(self) -> list[Opportunity]:
        if self._catalog_source is None:
            raise RuntimeError("no catalog source loaded")
        return [self._build_opportunity(self._catalog_source)]

    def _build_opportunity(self, source: catalog.SourceDefinition) -> Opportunity:
        """Build ONE sample opportunity from a source.

        Static fixture for contract verification only; not a live fetch.
        """
        platform = _platform_for_source(source)
        category = _category_for_source(source)
        payment_method = _payment_method_for_source(source)
        employment_type = _employment_type_for_source(source)
        source_id = getattr(source, "id", None) or getattr(source, "name", "unknown")
        url = _normalize_url(getattr(source, "url", "") or "")
        opp = self._create_opportunity(
            external_id=f"ownwork-prototype-{source_id}",
            title=f"Prototype opportunity from {getattr(source, 'name', 'unknown')}",
            platform=platform,
            category=category,
            url=url,
            description=("Static prototype opportunity for contract verification. This is NOT a real listing and must not be used for claim."),
            company=getattr(source, "name", "") or "",
            payment=10.0 if _has_any_known_payment_entry(source) else 0.0,
            currency="USD",
            payment_method=payment_method,
            registration_required=bool(getattr(source, "requires_account", False)),
            accepts_beginner=True,
            accepts_individuals=True,
            asynchronous=True,
        )
        opp.employment_type = employment_type
        opp.entry_mechanism = _entry_mechanism_for_source(source)
        opp.international_payment = _international_payment_for_source(source)
        opp.rate_source = "catalog"
        opp.experience_requirement = _experience_requirement_for_source(source)
        opp.technology_tags = _technology_tags_for_source(source)
        return opp
