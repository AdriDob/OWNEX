"""Source adaptation levels for the curated OWNEX catalog.

This module answers a different question than eligibility or payout
verification: *how far has a source actually been adapted by OWNEX?*

Levels are intentionally conservative. A source reaches ``ADAPTER_READY``
when OWNEX has a programmed adapter/executor for it, or when it has both a
known ``WorkPlatform`` mapping and a publicly documented payout method from
the owner's preferred set. Higher levels are reserved for live evidence and
stay empty until that evidence exists.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Any

from cores.opportunity.global_sources import get_sources
from cores.opportunity.own_work_sources import (
    CRYPTO_DEV_SOURCES,
    SOURCE_PLATFORM_MAP,
    WEB_DEV_SOURCES,
)
from cores.opportunity.own_work_sources_extensions import (
    build_fifth_wave_dev_extension,
    build_fourth_wave_bounty_extension,
    build_fourth_wave_dev_extension,
    build_second_wave_extension,
    build_sixth_wave_dev_extension,
    build_sixth_wave_security_extension,
    build_third_wave_extension,
)
from cores.opportunity.source_payment_docs import KNOWN_PAYMENT_METHODS


class SourceAdaptationLevel(StrEnum):
    """How far OWNEX has adapted a catalog source."""

    CATALOG_ONLY = "catalog_only"
    DISCOVERABLE = "discoverable"
    ADAPTER_READY = "adapter_ready"
    INTEGRATION_VERIFIED = "integration_verified"
    ARGENTINA_VERIFIED = "argentina_verified"
    PRODUCTION_ACTIVE = "production_active"


# Reserved for live evidence. Keep empty until a source has been verified
# end-to-end; catalog metadata alone must never populate these sets.
PRODUCTION_ACTIVE_SOURCES: frozenset[str] = frozenset()
ARGENTINA_VERIFIED_SOURCES: frozenset[str] = frozenset()
INTEGRATION_VERIFIED_SOURCES: frozenset[str] = frozenset()

_KNOWN_PAYOUT_ALIASES = frozenset({"paypal", "payoneer", "wise", "bank_transfer", "crypto", "stablecoin"})

# Connection manager platform keys — these are the external platforms
# managed by useExternalConnectionManager (Fiverr, Freelancer, Direct Work).
# When a source is mapped to one of these platforms via the connection manager,
# it receives at least DISCOVERABLE adaptation level since the connection
# is actively maintained.
_CONNECTION_MANAGER_PLATFORMS = frozenset({"fiverr", "freelancer", "direct_work"})

# Runtime adapter registry platform keys → catalog source names. Keep this
# mapping explicit: a registered adapter only upgrades the catalog sources it
# actually represents, not every source on the same platform.
_ADAPTER_PLATFORM_TO_SOURCE_NAMES: dict[str, tuple[str, ...]] = {
    "algora": ("Algora",),
    "bugcrowd": ("Bugcrowd",),
    "dataannotation": ("Data Annotation Tech",),
    "freelancer": ("Freelancer (coding)",),
    "freelancer_microtask": ("Freelancer (coding)",),
    "hackerone": ("HackerOne",),
    "intigriti": ("Intigriti",),
    "issuehand": ("IssueHunt",),
    "issuehunt": ("IssueHunt",),
    "linkedin": ("LinkedIn (Easy Apply)",),
    "linkedin_easyapply": ("LinkedIn (Easy Apply)",),
    "mindrift": ("Mindrift",),
    "opencollective": ("Open Collective",),
    "opire": ("Opire",),
    "opyre": ("Opyre",),
    "opyre_microtask": ("Opyre",),
    "outlier": ("Outlier",),
    "remotasks": ("Remotasks",),
    "superteam": ("Superteam Earn",),
    "yeswehack": ("YesWeHack",),
}


@lru_cache(maxsize=1)
def _own_work_source_names() -> frozenset[str]:
    names = {source.name for source in WEB_DEV_SOURCES + CRYPTO_DEV_SOURCES}
    for builder in (
        build_second_wave_extension,
        build_third_wave_extension,
        build_fourth_wave_bounty_extension,
        build_fourth_wave_dev_extension,
        build_fifth_wave_dev_extension,
        build_sixth_wave_security_extension,
        build_sixth_wave_dev_extension,
    ):
        names.update(source.name for source in builder().sources)
    return frozenset(names)


@lru_cache(maxsize=1)
def _catalog_source_names() -> frozenset[str]:
    return frozenset(source.name for source in get_sources()) | _own_work_source_names()


@lru_cache(maxsize=1)
def _adapter_backed_source_names() -> frozenset[str]:
    """Catalog sources with a registered runtime adapter/executor."""
    try:
        from core.opportunity.adapters import get_adapter_registry

        platform_keys = set(get_adapter_registry().all())
    except Exception:
        platform_keys = set()
    names: set[str] = set()
    for key in platform_keys:
        names.update(_ADAPTER_PLATFORM_TO_SOURCE_NAMES.get(key, ()))
    return frozenset(names)


def _has_known_payment_method(name: str) -> bool:
    methods = KNOWN_PAYMENT_METHODS.get(name, {}).get("methods", [])
    return any(method in _KNOWN_PAYOUT_ALIASES for method in methods)


def adaptation_level_for_source(name: str) -> SourceAdaptationLevel:
    """Return the highest evidence-backed adaptation level for ``name``."""
    normalized = name.strip()
    # Connection manager platforms: Fiverr, Freelancer, Direct Work
    # These sources have active external connections, so they receive at
    # least DISCOVERABLE adaptation level.
    if normalized in _CONNECTION_MANAGER_PLATFORMS:
        return SourceAdaptationLevel.DISCOVERABLE
    if normalized in PRODUCTION_ACTIVE_SOURCES:
        return SourceAdaptationLevel.PRODUCTION_ACTIVE
    if normalized in ARGENTINA_VERIFIED_SOURCES:
        return SourceAdaptationLevel.ARGENTINA_VERIFIED
    if normalized in INTEGRATION_VERIFIED_SOURCES:
        return SourceAdaptationLevel.INTEGRATION_VERIFIED
    if normalized in _adapter_backed_source_names():
        return SourceAdaptationLevel.ADAPTER_READY
    if SOURCE_PLATFORM_MAP.get(normalized) is not None and _has_known_payment_method(normalized):
        return SourceAdaptationLevel.ADAPTER_READY
    if normalized in _own_work_source_names():
        return SourceAdaptationLevel.DISCOVERABLE
    return SourceAdaptationLevel.CATALOG_ONLY


def catalog_adaptation_summary() -> dict[str, Any]:
    """Summarize adaptation levels across the deduplicated catalog union."""
    levels = {level.value: 0 for level in SourceAdaptationLevel}
    adapter_ready: list[str] = []
    for name in sorted(_catalog_source_names()):
        level = adaptation_level_for_source(name)
        levels[level.value] += 1
        if level is SourceAdaptationLevel.ADAPTER_READY:
            adapter_ready.append(name)
    return {
        "total_sources": len(_catalog_source_names()),
        "levels": levels,
        "adapter_ready_sources": adapter_ready,
    }


def adapter_ready_source_names() -> frozenset[str]:
    """Names that are ready for a prototype adapter (not verified live)."""
    return frozenset(name for name in _catalog_source_names() if adaptation_level_for_source(name) is SourceAdaptationLevel.ADAPTER_READY)


def platform_for_source(name: str) -> str | None:
    """Return the catalog-side platform key for a source, if mapped."""
    return SOURCE_PLATFORM_MAP.get(name.strip())
