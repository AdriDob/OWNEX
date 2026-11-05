"""Source Registry — Canonical catalog of work sources.

Single Source of Truth for all work sources OwnEX can discover and integrate.
Each source has canonical metadata, eligibility rules, and verification state.

The registry is the foundation for the Universal Source Adapter layer.
It stores source configuration, adaptation rules, and verification results.

Design principles:
- One entry per source (no duplicates)
- All metadata derived from verified reality, not assumptions
- Eligibility rules explicit and testable
- Versioned for backwards compatibility
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class SourceCategory(Enum):
    """Categories of work sources."""

    BUG_BOUNTY = auto()
    DEV_BOUNTY = auto()
    AI_EVALUATION = auto()
    DATA_ANNOTATION = auto()
    FREELANCE = auto()
    COMPETITIONS = auto()
    CONTENT = auto()
    RESEARCH = auto()
    OTHER = auto()


class SourceStatus(Enum):
    """Verification state of a source."""

    ACTIVE = "active"
    DEGRADED = "degraded"  # APIs changed, but still functional
    INACTIVE = "inactive"  # Down or blocked
    RETIRED = "retired"  # Removed deliberately
    UNKNOWN = "unknown"  # Never tested


@dataclass
class EligibilityRules:
    """Rules determining if a user can access this source."""

    min_experience: str = "nonenone", "beginner", "intermediate", "advanced", "expert"
    max_experience: str | None = None  # None = no limit
    requires_interview: bool = False
    requires_portfolio: bool = False
    requires_degree: bool = False
    requires_citizenship: list[str] | None = None  # Country codes, None = any
    requires_residency: list[str] | None = None  # Country codes, None = any
    requires_location: list[str] | None = None  # City/region, None = any
    requires_timezone: list[str] | None = None  # UTC offsets, None = any
    requires_min_hours: float | None = None  # Hours per week, None = any
    requires_exclusivity: bool = False
    any_other_restrictions: list[str] = field(default_factory=list)


@dataclass
class PaymentRules:
    """Rules for how payments are handled."""

    supported_methods: list[str] = field(default_factory=list)  # e.g., ["crypto", "paypal", "wire"]
    min_payout: float = 0.0
    max_payout: float | None = None
    default_currency: str = "USD"
    supported_countries: list[str] = field(default_factory=list)  # ISO country codes
    requires_verification: bool = True
    withdrawal_timing: str = "24-48h"  # Estimated withdrawal time


@dataclass
class SourceInfo:
    """Canonical information about a work source."""

    source_id: str  # Unique identifier (e.g., "outlier", "mindrift", "hackerone")
    name: str  # Human-readable name
    category: SourceCategory
    url: str  # Base URL / API endpoint
    description: str

    # Eligibility
    eligibility: EligibilityRules = field(default_factory=EligibilityRules)

    # Payment
    payment: PaymentRules = field(default_factory=PaymentRules)

    # Integration
    adapter_type: str = "rest"  # rest, graphql, rpc, browser, sdk, git, email, custom
    api_spec: dict[str, Any] | None = None  # OpenAPI/Swagger spec if applicable
    auth_type: str = "api_key"  # api_key, oauth2, none, custom
    requires_credentials: bool = True
    credential_fields: list[str] = field(default_factory=list)  # e.g., ["api_key", "username"]

    # Discovery
    discoverable: bool = True
    searchable: bool = True
    rss_feed: str | None = None  # RSS feed for new opportunities
    web_scrape_selectors: dict[str, str] | None = None

    # Status & Metrics
    status: SourceStatus = SourceStatus.UNKNOWN
    last_verified: str | None = None  # ISO timestamp
    verification_score: float = 0.0  # 0-100, from verification pipeline
    success_rate: float = 0.0  # Historical success rate (0-1)
    avg_payout_usd: float = 0.0
    avg_time_to_payout_days: float = 30.0

    # Metadata
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    # Version for tracking changes
    schema_version: str = "1.0"


class SourceRegistry:
    """Singleton registry of all known work sources.

    This is the Single Source of Truth for source metadata.
    In production, this would be persisted in a database.
    For now, it's initialized with the known sources and can be extended.
    """

    def __init__(self):
        self._sources: dict[str, SourceInfo] = {}
        self._initialized = False

    def initialize(self, sources: list[SourceInfo] | None = None) -> None:
        """Initialize the registry with known sources.

        Args:
            sources: List of SourceInfo to register. If None, uses built-in defaults.
        """
        if sources:
            for source in sources:
                self._sources[source.source_id] = source
        else:
            # Initialize with known sources from the existing adapter system
            self._initialize_known_sources()
        self._initialized = True

    def _initialize_known_sources(self) -> None:
        """Initialize with sources from the existing adapter system.

        This pulls source metadata from the opportunity adapters that already exist,
        ensuring consistency between the adapter layer and the source intelligence layer.
        """

        # We'll populate this from the actual adapters in the system
        # For now, set up the structure with empty sources that can be filled in
        pass

    def register(self, source: SourceInfo) -> None:
        """Register a new source.

        Args:
            source: SourceInfo to register
        """
        if not self._initialized:
            raise RuntimeError("Registry not initialized. Call initialize() first.")
        self._sources[source.source_id] = source

    def unregister(self, source_id: str) -> None:
        """Unregister a source."""
        if source_id in self._sources:
            del self._sources[source_id]

    def get(self, source_id: str) -> SourceInfo | None:
        """Get source info by ID."""
        return self._sources.get(source_id)

    def all_sources(self) -> list[SourceInfo]:
        """Get all registered sources."""
        return list(self._sources.values())

    def filter_by_category(self, category: SourceCategory) -> list[SourceInfo]:
        """Filter sources by category."""
        return [s for s in self._sources.values() if s.category == category]

    def filter_by_eligibility(self, country: str = "AR", has_experience: bool = False, min_age: int = 18) -> list[SourceInfo]:
        """Filter sources eligible for a user from a given country.

        Args:
            country: ISO country code (default: "AR" for Argentina)
            has_experience: Whether the user has professional experience
            min_age: Minimum age requirement

        Returns:
            List of sources that pass the eligibility filters
        """
        results = []
        for source in self._sources.values():
            rules = source.eligibility

            # Check citizenship requirement
            if rules.requires_citizenship and country not in rules.requires_citizenship:
                continue

            # Check residency requirement
            if rules.requires_residency and country not in rules.requires_residency:
                continue

            # Check experience requirement
            if not has_experience and rules.min_experience != "none":
                continue

            # Check interview requirement
            if rules.requires_interview:
                continue

            # Check portfolio requirement
            if rules.requires_portfolio:
                continue

            # Check degree requirement
            if rules.requires_degree:
                continue

            # Check timezone requirement
            if rules.requires_timezone:
                # Simple check - in production would validate actual timezone
                pass

            # Check min hours
            if rules.requires_min_hours:
                pass  # Would validate actual hours

            # Check exclusivity
            if rules.any_other_restrictions:
                # Check if any restriction applies
                restricted = any(r in source.notes.lower() for r in rules.any_other_restrictions)
                if restricted:
                    continue

            results.append(source)

        return results

    def count_by_status(self) -> dict[str, int]:
        """Count sources by status."""
        counts: dict[str, int] = {}
        for source in self._sources.values():
            s = source.status.value
            counts[s] = counts.get(s, 0) + 1
        return counts

    def active_sources(self) -> list[SourceInfo]:
        """Get only ACTIVE sources."""
        return [s for s in self._sources.values() if s.status == SourceStatus.ACTIVE]

    def sources_need_verification(self) -> list[SourceInfo]:
        """Get sources whose verification is stale or pending."""
        from datetime import datetime, timedelta

        now = datetime.now()
        results = []
        for source in self._sources.values():
            if source.last_verified is None:
                results.append(source)
            elif now - source.last_verified > timedelta(days=7):
                results.append(source)  # Stale verification (> 7 days)
        return results
