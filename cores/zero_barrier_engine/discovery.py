"""Public Opportunity Discovery - Zero-Barrier Public Opportunity Discovery.

Discovers public, zero-barrier opportunities across all supported platforms.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class DiscoverySource:
    """Configuration for a discovery source."""

    def __init__(
        self,
        name: str,
        source: str,
        source_type: str,
        platform: str,
        categories: list[str],
        enabled: bool = True,
        rate_limit_per_minute: int = 60,
        requires_auth: bool = False,
        auth_config: dict | None = None,
        zero_barrier_only: bool = True,
        analysis_cadence_hours: int = 24,
    ):
        self.name = name
        self.source = source
        self.source_type = source_type
        self.platform = platform
        self.categories = categories
        self.enabled = enabled
        self.rate_limit_per_minute = rate_limit_per_minute
        self.requires_auth = requires_auth
        self.auth_config = auth_config or {}
        self.zero_barrier_only = zero_barrier_only
        self.analysis_cadence_hours = analysis_cadence_hours
        self.last_fetched: datetime | None = None
        self.last_error: str | None = None
        self.consecutive_errors: int = 0


class BaseDiscoveryAdapter(ABC):
    """Base class for platform-specific discovery adapters."""

    def __init__(self, source_config: dict | None = None):
        self.source_config = source_config or {}
        self.logger = logging.getLogger(f"ownex.discovery.{self.source_config.get('name', 'unknown')}")

    @abstractmethod
    async def fetch_opportunities(self) -> list[dict]:
        """Fetch opportunities from this source."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate that the adapter can connect to its source."""
        pass

    def _create_opportunity(self, raw_data: dict) -> dict:
        """Convert raw platform data to standardized opportunity dict."""
        return {
            "id": raw_data.get("id", ""),
            "title": raw_data.get("title", ""),
            "description": raw_data.get("description", ""),
            "url": raw_data.get("url", ""),
            "source": self.source_config.get("name", ""),
            "platform": self.source_config.get("platform", ""),
            "category": raw_data.get("category", ""),
            "reward_min": raw_data.get("reward_min", 0),
            "reward_max": raw_data.get("reward_max", 0),
            "reward_typical": raw_data.get("reward_typical", 0),
            "currency": raw_data.get("currency", "USD"),
            "payment_methods": raw_data.get("payment_methods", []),
            "zero_barrier_level": raw_data.get("zero_barrier_level", "high"),
            "estimated_hours": raw_data.get("estimated_hours", 0),
            "difficulty": raw_data.get("difficulty", "intermediate"),
            "skills_required": raw_data.get("skills_required", []),
            "experience_required": raw_data.get("experience_required", "none"),
            "acceptance_probability": raw_data.get("acceptance_probability", 0.5),
            "duplicate_risk": raw_data.get("duplicate_risk", 0.3),
            "competition_level": raw_data.get("competition_level", "medium"),
            "verification_status": raw_data.get("verification_status", "unverified"),
            "remote": raw_data.get("remote", True),
            "async_work": raw_data.get("async_work", True),
            "time_to_payment_days": raw_data.get("time_to_payment_days", 30),
        }


class PublicOpportunityDiscovery:
    """Universal discovery across all public zero-barrier sources."""

    def __init__(self):
        self.adapters: dict[str, BaseDiscoveryAdapter] = {}
        self.sources: dict[str, dict] = {}
        self.logger = logging.getLogger("ownex.zero_barrier.discovery")
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        """Register all default public zero-barrier adapters."""
        # Bug Bounty Platforms
        self._register_bug_bounty_adapters()

        # Dev Bounty Platforms
        self._register_dev_bounty_adapters()

        # AI/Technical Work Platforms
        self._register_ai_technical_adapters()

        # Competition Platforms
        self._register_competition_adapters()

        # Direct Public Programs
        self._register_direct_programs()

    def _register_bug_bounty_adapters(self) -> None:
        """Register bug bounty platform adapters."""
        # Placeholder for real implementations
        pass

    def _register_dev_bounty_adapters(self) -> None:
        """Register dev bounty platform adapters."""
        pass

    def _register_ai_technical_adapters(self) -> None:
        """Register AI/technical work platform adapters."""
        pass

    def _register_competition_adapters(self) -> None:
        """Register competition platform adapters."""
        pass

    def _register_direct_programs(self) -> None:
        """Register direct public programs."""
        pass

    def register_adapter(self, adapter: Any) -> None:
        """Register a discovery adapter."""
        platform_name = getattr(adapter, "source_config", {}).get("platform", "unknown")
        self.adapters[platform_name] = adapter
        self.logger.info(f"Registered discovery adapter: {platform_name}")

    async def discover_all(
        self,
        categories: list[str] | None = None,
        platforms: list[str] | None = None,
        max_per_source: int = 50,
        zero_barrier_only: bool = True,
    ) -> list[dict]:
        """Discover opportunities from all registered sources."""
        all_opportunities = []

        for platform_name, adapter in self.adapters.items():
            if platforms and platform_name not in platforms:
                continue

            try:
                opportunities = await adapter.fetch_opportunities()

                for opp in opportunities[:max_per_source]:
                    opp_data = adapter._create_opportunity(opp)

                    # Filter zero-barrier if requested
                    if self._should_include(opp_data, zero_barrier_only):
                        all_opportunities.append(opp_data)

            except Exception as e:
                logging.getLogger(__name__).error(f"Discovery failed for {platform_name}: {e}")

        return all_opportunities

    def _should_include(self, opportunity: dict, zero_barrier_only: bool) -> bool:
        """Filter opportunities based on zero-barrier requirements."""
        if not zero_barrier_only:
            return True

        # Filter: must be zero or very low barrier
        barrier = opportunity.get("zero_barrier_level", "high")
        return barrier in ("zero", "very_low", "low")

    def get_registered_platforms(self) -> list[str]:
        """Get list of registered platform names."""
        return list(self.adapters.keys())

    def get_source_status(self) -> dict:
        """Get status of all discovery sources."""
        return {
            "total_adapters": len(self.adapters),
            "platforms": list(self.adapters.keys()),
        }


class ZeroBarrierIncomeEngine:
    """Main engine for zero-barrier maximum income."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.discovery = PublicOpportunityDiscovery()
        self.logger = logging.getLogger("ownex.zero_barrier.engine")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the engine."""
        self.logger.info("Initializing Zero-Barrier Income Engine...")
        self._initialized = True
        self.logger.info("Zero-Barrier Income Engine initialized")

    async def discover_opportunities(
        self,
        categories: list[str] | None = None,
        platforms: list[str] | None = None,
        zero_barrier_only: bool = True,
    ) -> list[dict]:
        """Discover all public zero-barrier opportunities."""
        if not self._initialized:
            await self.initialize()

        return await self.discovery.discover_all(
            categories=categories,
            platforms=platforms,
            zero_barrier_only=zero_barrier_only,
        )

    def get_status(self) -> dict:
        """Get engine status."""
        return {
            "initialized": self._initialized,
            "adapters": self.discovery.get_source_status(),
        }
