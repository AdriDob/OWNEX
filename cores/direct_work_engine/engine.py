"""Direct Work Engine — orchestrates discovery → scoring → recommendation → action.

The main entry point that wires UniversalDiscovery, ZeroBarrierScorer,
IntelligentRecommender, and IntelligentProfileBuilder together.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource, UniversalDiscovery
from cores.direct_work_engine.feedback import LearningRecord, apply_learning
from cores.direct_work_engine.models import (
    Opportunity,
    OpportunityCategory,
    RankedOpportunity,
    UserProfile,
    WorkPlatform,
)
from cores.direct_work_engine.profile_builder import IntelligentProfileBuilder, ProfileAssets
from cores.direct_work_engine.recommendation import IntelligentRecommender, RecommenderConfig
from cores.direct_work_engine.scoring import ZeroBarrierScorer

logger = logging.getLogger("ownex.direct_work_engine.engine")


@dataclass(slots=True)
class EngineStats:
    """Runtime statistics for the engine."""

    cycles_completed: int = 0
    total_opportunities_seen: int = 0
    total_opportunities_scored: int = 0
    total_recommendations: int = 0
    last_cycle_at: str = ""
    last_cycle_duration_s: float = 0.0
    errors: list[str] = field(default_factory=list)


class DirectWorkEngine:
    """Orchestrates the full pipeline: discover → score → recommend → act.

    Decoupled module: runs independently, publishes results to the event bus,
    and only requests user approval before submitting personal information.
    """

    def __init__(
        self,
        discovery: UniversalDiscovery | None = None,
        scorer: ZeroBarrierScorer | None = None,
        recommender: IntelligentRecommender | None = None,
        recommender_config: RecommenderConfig | None = None,
        profile_builder: IntelligentProfileBuilder | None = None,
        researcher: Any | None = None,
    ):
        self.discovery = discovery or UniversalDiscovery()
        self.scorer = scorer or ZeroBarrierScorer()
        self.recommender = recommender or IntelligentRecommender(config=recommender_config)
        self.profile_builder = profile_builder or IntelligentProfileBuilder()
        self.researcher = researcher
        self.stats = EngineStats()
        self._running = False

    def register_adapter(self, adapter: BaseDiscoveryAdapter) -> None:
        """Register a platform adapter with the discovery layer."""
        self.discovery.register_adapter(adapter)

    def register_source(self, source: DiscoverySource) -> None:
        """Register a discovery source."""
        self.discovery.register_source(source)

    async def run_cycle(
        self,
        profile: UserProfile,
        categories: list[OpportunityCategory] | None = None,
        platforms: list[WorkPlatform] | None = None,
        limit: int = 10,
    ) -> tuple[list[Opportunity], list[RankedOpportunity]]:
        """Execute one full cycle: discover, score, recommend."""
        start = datetime.now(UTC)
        logger.info("DirectWorkEngine cycle starting")

        # 1. Discover
        opportunities = await self.discovery.discover_all(categories=categories, platforms=platforms)
        self.stats.total_opportunities_seen += len(opportunities)

        # 2. Score (in-place, sorted by zero barrier score)
        scored = self.scorer.score_opportunities(opportunities)
        self.stats.total_opportunities_scored += len(scored)

        # 3. Recommend
        ranked = self.recommender.recommend(scored, profile, limit=limit)
        self.stats.total_recommendations += len(ranked)

        # 4. Update stats
        self.stats.cycles_completed += 1
        self.stats.last_cycle_at = start.isoformat()
        duration = (datetime.now(UTC) - start).total_seconds()
        self.stats.last_cycle_duration_s = round(duration, 3)

        logger.info(
            "Cycle done: %d discovered, %d scored, %d recommended in %.1fs",
            len(opportunities),
            len(scored),
            len(ranked),
            duration,
        )
        return opportunities, ranked

    async def run_continuous(
        self,
        profile: UserProfile,
        interval_seconds: int = 3600,
        categories: list[OpportunityCategory] | None = None,
        limit: int = 10,
    ) -> None:
        """Run discovery cycles continuously."""
        self._running = True
        while self._running:
            try:
                await self.run_cycle(profile, categories=categories, limit=limit)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Cycle error: %s", e)
                self.stats.errors.append(str(e))
            await asyncio.sleep(interval_seconds)

    def stop(self) -> None:
        """Stop continuous runs."""
        self._running = False

    def build_profile_assets(self, profile: UserProfile) -> ProfileAssets:
        """Generate portfolio/CV/bio assets from real user facts."""
        return self.profile_builder.build(profile)

    def learn(self, profile: UserProfile, records: list[LearningRecord]) -> UserProfile:
        """Fold verified outcomes into the profile so the recommender improves.

        Empty history is a no-op — OWNEX never invents success rates.
        """
        return apply_learning(profile, records)

    async def register_discovered_platforms(self) -> int:
        """Register newly discovered platforms from AutonomousDiscoveryEngine.

        Returns the number of new platforms registered.
        """
        if self.researcher is None:
            return 0

        # Get discovered platforms from the autonomous engine
        discovered = getattr(self.researcher, "discovered_platforms", {})
        if not discovered:
            return 0

        registered = 0
        for _url, platform_info in discovered.items():
            # Check if already registered
            adapter_name = f"dynamic_{platform_info.get('domain', '')}"
            if adapter_name not in self.discovery.sources:
                try:
                    success = self.discovery.register_discovered_platform(platform_info)
                    if success:
                        registered += 1
                except Exception as e:
                    logger.warning("Failed to register discovered platform %s: %s", adapter_name, e)

        return registered

    def get_status(self) -> dict[str, Any]:
        """Return engine status for health/UI."""
        return {
            "running": self._running,
            "stats": {
                "cycles_completed": self.stats.cycles_completed,
                "total_opportunities_seen": self.stats.total_opportunities_seen,
                "total_opportunities_scored": self.stats.total_opportunities_scored,
                "total_recommendations": self.stats.total_recommendations,
                "last_cycle_at": self.stats.last_cycle_at,
                "last_cycle_duration_s": self.stats.last_cycle_duration_s,
                "errors": self.stats.errors[-10:],
            },
            "platforms": [p.value for p in self.discovery.get_registered_platforms()],
            "sources": self.discovery.get_source_status(),
        }


def register_capabilities() -> None:
    """Register Direct Work Engine capabilities in the CapabilityRegistry (auto-integration).

    Fulfills the auto-integration rule: every new module must appear in the
    Capability Registry, Health, Metrics and Knowledge Graph automatically.
    Idempotent — safe to call multiple times.
    """
    try:
        from core.capabilities.registry import get_capability_registry

        reg = get_capability_registry()
        reg.unregister("opportunity_discovery", "direct_work_engine")
        reg.register(
            "opportunity_discovery",
            "direct_work_engine",
            {
                "capabilities": [
                    "discover_opportunities",
                    "zero_barrier_score",
                    "recommend",
                    "build_profile_assets",
                    "learn_from_outcomes",
                ]
            },
            description="Universal opportunity discovery with Zero Barrier scoring and intelligent recommendation",
        )
        logger.info("Direct Work Engine registered in CapabilityRegistry")
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not register Direct Work Engine in CapabilityRegistry: %s", exc)
