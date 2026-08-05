"""Universal Discovery — intelligent opportunity discovery across all platforms and categories."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cores.direct_work_engine.models import (
    DifficultyLevel,
    ExperienceLevel,
    GameDevSpecialization,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)

logger = logging.getLogger("ownex.direct_work_engine.discovery")


@dataclass(slots=True)
class DiscoverySource:
    """A source of opportunities (platform, API, website, etc.).

    ``tier`` classifies how much of the cycle is autonomous for that source:
    1 = public + fully autonomous (discover, prepare, deliver). 2 = needs an
    API key to be configured. 3 = requires a manual setup or long-cycle
    proposal. ``analysis_cadence_hours`` is how often OWNEX should re-analyze
    this source — public sources on Tier 1 check several times a day, manual
    ones far less.
    """

    name: str
    platform: WorkPlatform
    categories: list[OpportunityCategory]
    enabled: bool = True
    rate_limit_per_minute: int = 60
    requires_auth: bool = False
    auth_config: dict[str, Any] = field(default_factory=dict)
    last_fetched: datetime | None = None
    last_error: str | None = None
    consecutive_errors: int = 0
    tier: int = 2
    analysis_cadence_hours: int = 24


class BaseDiscoveryAdapter(ABC):
    """Base class for platform-specific discovery adapters."""

    def __init__(self, source: DiscoverySource):
        self.source = source
        self.logger = logging.getLogger(f"ownex.discovery.{source.name}")

    @abstractmethod
    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch opportunities from this source."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate that the adapter can connect to its source."""
        pass

    def _create_opportunity(
        self,
        external_id: str,
        title: str,
        category: OpportunityCategory,
        url: str = "",
        description: str = "",
        company: str = "",
        country: str = "",
        payment: float = 0.0,
        currency: str = "USD",
        payment_method: PaymentMethod = PaymentMethod.OTHER,
        difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
        language_required: str = "english",
        estimated_time_hours: float = 0.0,
        experience_required: ExperienceLevel = ExperienceLevel.NONE,
        portfolio_required: bool = False,
        interview_required: bool = False,
        technical_test_required: bool = False,
        registration_required: bool = True,
        time_to_payout_days: float | None = None,
        reputation: float = 0.5,
        risk: float = 0.5,
        payment_proven: bool = False,
        stability: float = 0.5,
        accepts_beginner: bool = True,
        accepts_freelancers: bool = True,
        accepts_individuals: bool = True,
        accepts_ai_tools: bool = True,
        asynchronous: bool = True,
        specialization: GameDevSpecialization | None = None,
        **kwargs: Any,
    ) -> Opportunity:
        """Helper to create a normalized Opportunity with defaults."""
        return Opportunity(
            id=f"{self.source.platform.value}_{external_id}",
            title=title,
            platform=self.source.platform,
            category=category,
            url=url,
            description=description,
            company=company,
            country=country,
            remote=True,
            payment=payment,
            currency=currency,
            payment_method=payment_method,
            difficulty=difficulty,
            language_required=language_required,
            estimated_time_hours=estimated_time_hours,
            experience_required=experience_required,
            portfolio_required=portfolio_required,
            interview_required=interview_required,
            technical_test_required=technical_test_required,
            registration_required=registration_required,
            time_to_payout_days=time_to_payout_days,
            reputation=reputation,
            risk=risk,
            payment_proven=payment_proven,
            stability=stability,
            accepts_beginner=accepts_beginner,
            accepts_freelancers=accepts_freelancers,
            accepts_individuals=accepts_individuals,
            accepts_ai_tools=accepts_ai_tools,
            asynchronous=asynchronous,
            specialization=specialization,
        )


class UniversalDiscovery:
    """Universal opportunity discovery across all supported platforms."""

    def __init__(self):
        self.adapters: dict[WorkPlatform, BaseDiscoveryAdapter] = {}
        self.sources: dict[str, DiscoverySource] = {}
        self._running = False

    def register_adapter(self, adapter: BaseDiscoveryAdapter) -> None:
        """Register a discovery adapter for a platform."""
        self.adapters[adapter.source.platform] = adapter
        self.sources[adapter.source.name] = adapter.source
        logger.info("Registered discovery adapter: %s (%s)", adapter.source.name, adapter.source.platform)

    def register_source(self, source: DiscoverySource) -> None:
        """Register a discovery source (may not have adapter yet)."""
        self.sources[source.name] = source

    def register_discovered_platform(self, platform_info: dict[str, Any]) -> bool:
        """Register a dynamically discovered platform from the WebResearcher.

        Auto-creates a generic adapter for the discovered URL so the engine
        can evaluate it on the next discovery cycle. Returns True if a new
        adapter was registered.
        """
        from cores.direct_work_engine.autonomous_discovery import DynamicPlatformAdapter
        from cores.direct_work_engine.models import (
            OpportunityCategory,
        )

        domain = platform_info.get("domain", "")
        url = platform_info.get("url", "")
        platform = WorkPlatform.OTHER

        # Try to match by domain to a known WorkPlatform
        for wp in WorkPlatform:
            if wp.value and wp.value in domain:
                platform = wp
                break

        adapter_name = f"dynamic_{domain}"
        if adapter_name in self.sources:
            return False

        adapter = DynamicPlatformAdapter(
            DiscoverySource(
                name=adapter_name,
                platform=platform,
                categories=[OpportunityCategory.SOFTWARE_ENGINEERING],
                tier=3,  # manual setup tier
                analysis_cadence_hours=168,
            ),
            platform_url=url,
            domain=domain,
            zero_barrier_signals=platform_info.get("zero_barrier_signals", 0),
        )
        self.register_adapter(adapter)
        return True

    async def discover_all(
        self,
        categories: list[OpportunityCategory] | None = None,
        platforms: list[WorkPlatform] | None = None,
    ) -> list[Opportunity]:
        """Discover opportunities from all registered adapters."""
        all_opportunities: list[Opportunity] = []

        for platform, adapter in self.adapters.items():
            if platforms and platform not in platforms:
                continue

            if not adapter.source.enabled:
                continue

            try:
                logger.info("Fetching from %s...", adapter.source.name)
                opportunities = await adapter.fetch_opportunities()

                # Filter by category if specified
                if categories:
                    opportunities = [o for o in opportunities if o.category in categories]

                all_opportunities.extend(opportunities)
                adapter.source.last_fetched = datetime.now(UTC)
                adapter.source.consecutive_errors = 0

            except Exception as e:
                adapter.source.consecutive_errors += 1
                adapter.source.last_error = str(e)
                logger.error("Error fetching from %s: %s", adapter.source.name, e)

        logger.info("Total opportunities discovered: %d", len(all_opportunities))
        return all_opportunities

    async def discover_from_platform(
        self,
        platform: WorkPlatform,
        categories: list[OpportunityCategory] | None = None,
    ) -> list[Opportunity]:
        """Discover from a specific platform."""
        adapter = self.adapters.get(platform)
        if not adapter:
            logger.warning("No adapter registered for platform: %s", platform)
            return []

        try:
            opportunities = await adapter.fetch_opportunities()
            if categories:
                opportunities = [o for o in opportunities if o.category in categories]
            return opportunities
        except Exception as e:
            logger.error("Error fetching from %s: %s", platform, e)
            return []

    def get_registered_platforms(self) -> list[WorkPlatform]:
        """Get list of platforms with registered adapters."""
        return list(self.adapters.keys())

    def get_source_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all registered sources."""
        return {
            name: {
                "platform": source.platform.value,
                "enabled": source.enabled,
                "last_fetched": source.last_fetched.isoformat() if source.last_fetched else None,
                "last_error": source.last_error,
                "consecutive_errors": source.consecutive_errors,
                "categories": [c.value for c in source.categories],
                "tier": source.tier,
                "analysis_cadence_hours": source.analysis_cadence_hours,
            }
            for name, source in self.sources.items()
        }

    def get_sources_by_tier(self) -> dict[int, list[DiscoverySource]]:
        """Group registered sources by autonomous tier (1=public, 2=key, 3=manual)."""
        grouped: dict[int, list[DiscoverySource]] = {1: [], 2: [], 3: []}
        for source in self.sources.values():
            grouped.setdefault(source.tier, []).append(source)
        return grouped
