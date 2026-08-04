"""Discovery Engine 24/7 — continuous opportunity discovery, classification, and ranking.

This is the core engine that never stops searching for work opportunities
across all platforms, classifying them, and ranking by expected value.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from core.events.event_bus import get_core_event_bus
from core.opportunity.adapters import fetch_all_opportunities
from core.opportunity.models import ScoredOpportunity
from core.sensors.observation_engine import ObservationEngine
from cores.prometheus_metrics import (
    OPPORTUNITY_EVH,
    OPPORTUNITY_SCORE,
    record_opportunity_discovered,
)

logger = logging.getLogger("ownex.discovery_engine")


class DiscoveryMode(Enum):
    """Discovery operating modes."""

    CONTINUOUS = "continuous"  # Run forever, every cycle
    SCHEDULED = "scheduled"  # Run at specific intervals
    ON_DEMAND = "on_demand"  # Trigger manually


class OpportunityStatus(Enum):
    """Status of an opportunity in the pipeline."""

    DISCOVERED = "discovered"
    CLASSIFIED = "classified"
    SCORED = "scored"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class RankedOpportunity:
    """Opportunity with ranking metadata."""

    opportunity: ScoredOpportunity
    rank: int = 0
    score: float = 0.0
    evh: float = 0.0  # Expected Value per Hour
    priority: str = "normal"  # critical, high, normal, low
    status: OpportunityStatus = OpportunityStatus.DISCOVERED
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    classified_at: datetime | None = None
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryConfig:
    """Configuration for the discovery engine."""

    mode: DiscoveryMode = DiscoveryMode.CONTINUOUS
    cycle_interval_seconds: int = 300  # 5 minutes between full cycles
    max_opportunities_per_cycle: int = 500  # Limit per cycle
    min_score_threshold: float = 0.3  # Minimum score to keep
    min_evh_threshold: float = 1.0  # Minimum EVH to queue
    deduplication_window_hours: int = 24  # Hours to keep dedup cache
    enable_classification: bool = True
    enable_scoring: bool = True
    enable_ranking: bool = True
    categories: list[str] = field(default_factory=lambda: ["security", "forge", "pulse", "freelance", "crypto"])
    max_concurrent_fetch: int = 10  # Parallel adapter fetches


@dataclass
class DiscoveryMetrics:
    """Runtime metrics for discovery engine."""

    cycles_completed: int = 0
    total_opportunities_found: int = 0
    total_opportunities_kept: int = 0
    total_opportunities_deduped: int = 0
    total_opportunities_scored: int = 0
    total_opportunities_queued: int = 0
    last_cycle_duration: float = 0.0
    last_cycle_at: datetime | None = None
    errors: list[str] = field(default_factory=list)
    adapters_queried: dict[str, int] = field(default_factory=dict)
    categories_found: dict[str, int] = field(default_factory=dict)


class DiscoveryEngine:
    """
    24/7 Discovery Engine for OWNEX.

    Continuously discovers, classifies, scores, and ranks opportunities
    from all connected platforms. Feeds the action queue for execution.
    """

    def __init__(
        self,
        config: DiscoveryConfig | None = None,
        observation_engine: ObservationEngine | None = None,
    ):
        self.config = config or DiscoveryConfig()
        self.observation_engine = observation_engine
        self.event_bus = get_core_event_bus()

        self._running = False
        self._cycle_task: asyncio.Task | None = None
        self._metrics = DiscoveryMetrics()

        # Deduplication cache (persisted across cycles)
        self._seen_cache: dict[str, float] = {}  # key -> timestamp

        # Ranked opportunity queue
        self._ranked_queue: list[RankedOpportunity] = []
        self._queue_lock = asyncio.Lock()

        # Callbacks for downstream processing
        self._on_opportunity_queued: list[Callable[[RankedOpportunity], Any]] = []
        self._on_cycle_complete: list[Callable[[DiscoveryMetrics], Any]] = []

        logger.info(
            "DiscoveryEngine initialized: mode=%s, interval=%ds",
            self.config.mode.value,
            self.config.cycle_interval_seconds,
        )

    def register_queued_callback(self, callback: Callable[[RankedOpportunity], Any]) -> None:
        """Register callback when opportunity is queued for action."""
        self._on_opportunity_queued.append(callback)

    def register_cycle_callback(self, callback: Callable[[DiscoveryMetrics], Any]) -> None:
        """Register callback when discovery cycle completes."""
        self._on_cycle_complete.append(callback)

    async def start(self) -> None:
        """Start the discovery engine."""
        if self._running:
            logger.warning("DiscoveryEngine already running")
            return

        self._running = True

        if self.config.mode == DiscoveryMode.CONTINUOUS:
            self._cycle_task = asyncio.create_task(self._continuous_loop())
        elif self.config.mode == DiscoveryMode.SCHEDULED:
            self._cycle_task = asyncio.create_task(self._scheduled_loop())

        logger.info("DiscoveryEngine started")
        self.event_bus.publish("discovery:started", mode=self.config.mode.value)

    async def stop(self) -> None:
        """Stop the discovery engine."""
        self._running = False

        if self._cycle_task:
            self._cycle_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cycle_task

        logger.info("DiscoveryEngine stopped")
        self.event_bus.publish("discovery:stopped")

    async def trigger_cycle(self) -> DiscoveryMetrics:
        """Manually trigger a discovery cycle."""
        return await self._run_discovery_cycle()

    async def _continuous_loop(self) -> None:
        """Continuous discovery loop."""
        while self._running:
            try:
                await self._run_discovery_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in discovery cycle: %s", e)
                self._metrics.errors.append(f"{datetime.now(UTC).isoformat()}: {e}")

            # Wait for next cycle
            await asyncio.sleep(self.config.cycle_interval_seconds)

    async def _scheduled_loop(self) -> None:
        """Scheduled discovery loop (e.g., at specific hours)."""
        # For now, same as continuous
        await self._continuous_loop()

    async def _run_discovery_cycle(self) -> DiscoveryMetrics:
        """Execute one full discovery cycle."""
        cycle_start = time.time()
        logger.info("Starting discovery cycle #%d", self._metrics.cycles_completed + 1)

        # Reset cycle metrics
        cycle_found = 0
        cycle_kept = 0
        cycle_deduped = 0
        cycle_scored = 0
        cycle_queued = 0
        adapters_used: dict[str, int] = {}

        # 1. FETCH: Get opportunities from all adapters
        try:
            raw_opportunities = await fetch_all_opportunities()
            logger.info("Fetched %d raw opportunities from adapters", len(raw_opportunities))

            for opp in raw_opportunities:
                adapters_used[opp.source_name] = adapters_used.get(opp.source_name, 0) + 1
        except Exception as e:
            logger.error("Failed to fetch from adapters: %s", e)
            raw_opportunities = []

        # 2. Also collect from observation engine (sensor network)
        sensor_observations = []
        if self.observation_engine:
            try:
                sensor_observations = await self.observation_engine.collect()
                logger.info("Collected %d observations from sensor network", len(sensor_observations))
            except Exception as e:
                logger.error("Failed to collect from sensor network: %s", e)

        # 3. DEDUPLICATE: Combine and deduplicate
        all_candidates = []

        # From adapters (already scored by OpportunityEngine)
        for opp in raw_opportunities:
            all_candidates.append(("adapter", opp))

        # From sensors (need scoring)
        for obs in sensor_observations:
            all_candidates.append(("sensor", obs))

        # Deduplicate
        unique_candidates = []
        for source, item in all_candidates:
            dedup_key = self._make_dedup_key(source, item)

            if self._is_duplicate(dedup_key):
                cycle_deduped += 1
                continue

            self._mark_seen(dedup_key)
            unique_candidates.append((source, item))

        logger.info("After deduplication: %d unique candidates", len(unique_candidates))

        # 4. CLASSIFY & SCORE
        ranked_opportunities = []

        for source, item in unique_candidates[: self.config.max_opportunities_per_cycle]:
            try:
                scored = item if source == "adapter" else self._observation_to_scored(item)

                if not scored:
                    continue

                # Apply minimum score threshold
                if scored.score.overall < self.config.min_score_threshold:
                    continue

                cycle_scored += 1

                # Calculate EVH
                evh = self._calculate_evh(scored)

                if evh < self.config.min_evh_threshold:
                    continue

                # Create ranked opportunity
                ranked = RankedOpportunity(
                    opportunity=scored,
                    score=scored.score.overall,
                    evh=evh,
                    priority=self._determine_priority(scored, evh),
                    status=OpportunityStatus.SCORED,
                    metadata={
                        "source": source,
                        "category": scored.cycle,
                    },
                )

                ranked_opportunities.append(ranked)
                cycle_kept += 1

                # Track categories
                cat = scored.cycle
                self._metrics.categories_found[cat] = self._metrics.categories_found.get(cat, 0) + 1

            except Exception as e:
                logger.warning("Failed to score opportunity: %s", e)

        # 5. RANK
        ranked_opportunities.sort(key=lambda x: (x.evh, x.score), reverse=True)

        for i, opp in enumerate(ranked_opportunities):
            opp.rank = i + 1
            opp.classified_at = datetime.now(UTC)

        # 6. QUEUE high-priority opportunities
        async with self._queue_lock:
            for opp in ranked_opportunities:
                if opp.priority in ("critical", "high") and opp.evh >= self.config.min_evh_threshold:
                    self._ranked_queue.append(opp)
                    opp.status = OpportunityStatus.QUEUED
                    cycle_queued += 1

                    # Trigger callbacks
                    for callback in self._on_opportunity_queued:
                        try:
                            await callback(opp)
                        except Exception as e:
                            logger.error("Queued callback failed: %s", e)

        # 7. EMIT EVENTS
        for opp in ranked_opportunities[:20]:  # Emit top 20
            self._emit_opportunity_event(opp)

            # Prometheus metrics
            record_opportunity_discovered(
                source=opp.opportunity.source_name,
                category=opp.opportunity.cycle,
                score=opp.score,
                evh=opp.evh,
            )
            OPPORTUNITY_SCORE.labels(category=opp.opportunity.cycle).observe(opp.score)
            OPPORTUNITY_EVH.labels(category=opp.opportunity.cycle).observe(opp.evh)

        # Update metrics
        cycle_duration = time.time() - cycle_start
        self._metrics.cycles_completed += 1
        self._metrics.total_opportunities_found += cycle_found
        self._metrics.total_opportunities_kept += cycle_kept
        self._metrics.total_opportunities_deduped += cycle_deduped
        self._metrics.total_opportunities_scored += cycle_scored
        self._metrics.total_opportunities_queued += cycle_queued
        self._metrics.last_cycle_duration = cycle_duration
        self._metrics.last_cycle_at = datetime.now(UTC)
        self._metrics.adapters_queried = adapters_used

        logger.info(
            "Discovery cycle #%d complete: found=%d, kept=%d, scored=%d, queued=%d, deduped=%d, duration=%.2fs",
            self._metrics.cycles_completed,
            cycle_found,
            cycle_kept,
            cycle_scored,
            cycle_queued,
            cycle_deduped,
            cycle_duration,
        )

        # Trigger cycle callbacks
        for callback in self._on_cycle_complete:
            try:
                await callback(self._metrics)
            except Exception as e:
                logger.error("Cycle callback failed: %s", e)

        self.event_bus.publish(
            "discovery:cycle_complete",
            cycle=self._metrics.cycles_completed,
            found=cycle_found,
            kept=cycle_kept,
            queued=cycle_queued,
            duration=cycle_duration,
        )

        return self._metrics

    def _make_dedup_key(self, source: str, item: Any) -> str:
        """Create deduplication key from opportunity."""
        if hasattr(item, "id"):
            return f"{source}:{item.id}"
        elif hasattr(item, "external_id"):
            return f"{source}:{item.external_id}"
        elif hasattr(item, "url") and item.url:
            return f"{source}:url:{item.url}"
        else:
            return f"{source}:{hash(str(item))}"

    def _is_duplicate(self, key: str) -> bool:
        """Check if key is in deduplication cache."""
        if key in self._seen_cache:
            # Check if expired
            age = time.time() - self._seen_cache[key]
            if age < self.config.deduplication_window_hours * 3600:
                return True
            else:
                # Expired, remove
                del self._seen_cache[key]
        return False

    def _mark_seen(self, key: str) -> None:
        """Mark key as seen."""
        self._seen_cache[key] = time.time()

        # Limit cache size
        if len(self._seen_cache) > 100000:
            # Remove oldest 10%
            sorted_items = sorted(self._seen_cache.items(), key=lambda x: x[1])
            for k, _ in sorted_items[:10000]:
                del self._seen_cache[k]

    def _observation_to_scored(self, observation: Any) -> ScoredOpportunity | None:
        """Convert sensor observation to scored opportunity."""
        try:
            # Build RawOpportunity from observation
            from core.opportunity.adapters import RawOpportunity

            raw = RawOpportunity(
                id=f"sensor:{observation.external_id}",
                name=observation.title,
                description=observation.description,
                platform=observation.source_name,
                url=observation.url,
                reward=observation.estimated_reward_max,
                effort_hours=4.0,  # Default estimate
                tags=observation.tags,
                cycle=observation.source_type,
                source_type=observation.source_type,
                source_name=observation.source_name,
                metadata={**observation.raw_data, "observation_id": observation.id},
                created_at=observation.observed_at,
            )

            # Use adapter's to_scored method
            # Need an adapter instance - use a generic one
            from core.opportunity.adapters import OpportunityAdapter

            class GenericAdapter(OpportunityAdapter):
                platform = "generic"
                cycle = observation.source_type

            adapter = GenericAdapter()
            return adapter.to_scored(raw)

        except Exception as e:
            logger.warning("Failed to convert observation to scored: %s", e)
            return None

    def _calculate_evh(self, scored: ScoredOpportunity) -> float:
        """Calculate Expected Value per Hour."""
        reward = getattr(scored, "reward", 0) or 0
        effort = getattr(scored, "effort_hours", 4) or 4

        if effort <= 0:
            return 0.0

        # Base EVH
        evh = reward / effort

        # Apply probability adjustments
        probability = scored.score.acceptance_probability
        evh *= probability

        return evh

    def _determine_priority(self, scored: ScoredOpportunity, evh: float) -> str:
        """Determine priority based on score and EVH."""
        if evh >= 100 and scored.score.overall >= 0.8:
            return "critical"
        elif evh >= 50 and scored.score.overall >= 0.7:
            return "high"
        elif evh >= 10 and scored.score.overall >= 0.5:
            return "normal"
        else:
            return "low"

    def _emit_opportunity_event(self, opp: RankedOpportunity) -> None:
        """Emit event for discovered opportunity."""
        self.event_bus.publish(
            "opportunity:discovered",
            {
                "id": opp.opportunity.id,
                "name": opp.opportunity.name,
                "category": opp.opportunity.cycle,
                "platform": opp.opportunity.source_name,
                "reward": getattr(opp.opportunity, "estimated_payout", 0),
                "evh": opp.evh,
                "score": opp.score,
                "priority": opp.priority,
                "rank": opp.rank,
                "url": getattr(opp.opportunity, "public_url", None),
                "tags": getattr(opp.opportunity, "technology_tags", []),
                "discovered_at": opp.discovered_at.isoformat(),
            },
        )

    # ── Queue Management ──────────────────────────────────────────────

    async def get_next_opportunity(self) -> RankedOpportunity | None:
        """Get the highest-priority queued opportunity."""
        async with self._queue_lock:
            if self._ranked_queue:
                return self._ranked_queue.pop(0)
        return None

    async def get_queued_opportunities(self, limit: int = 50) -> list[RankedOpportunity]:
        """Get current queued opportunities."""
        async with self._queue_lock:
            return self._ranked_queue[:limit]

    async def requeue_opportunity(self, opp: RankedOpportunity) -> None:
        """Re-queue an opportunity (e.g., after failure)."""
        opp.status = OpportunityStatus.QUEUED
        opp.rank = 0
        async with self._queue_lock:
            self._ranked_queue.insert(0, opp)  # High priority re-queue

    async def reject_opportunity(self, opp: RankedOpportunity, reason: str) -> None:
        """Mark opportunity as rejected."""
        opp.status = OpportunityStatus.REJECTED
        opp.metadata["rejection_reason"] = reason
        self.event_bus.publish(
            "opportunity:rejected",
            {
                "id": opp.opportunity.id,
                "reason": reason,
            },
        )

    # ── Status & Metrics ──────────────────────────────────────────────

    def get_metrics(self) -> DiscoveryMetrics:
        """Get current metrics."""
        return self._metrics

    def get_status(self) -> dict[str, Any]:
        """Get engine status."""
        return {
            "running": self._running,
            "mode": self.config.mode.value,
            "cycle_interval": self.config.cycle_interval_seconds,
            "metrics": {
                "cycles_completed": self._metrics.cycles_completed,
                "total_found": self._metrics.total_opportunities_found,
                "total_kept": self._metrics.total_opportunities_kept,
                "total_deduped": self._metrics.total_opportunities_deduped,
                "total_scored": self._metrics.total_opportunities_scored,
                "total_queued": self._metrics.total_opportunities_queued,
                "last_cycle_duration": self._metrics.last_cycle_duration,
                "last_cycle_at": self._metrics.last_cycle_at.isoformat() if self._metrics.last_cycle_at else None,
                "queue_size": len(self._ranked_queue),
                "dedup_cache_size": len(self._seen_cache),
                "categories": self._metrics.categories_found,
            },
            "config": {
                "min_score": self.config.min_score_threshold,
                "min_evh": self.config.min_evh_threshold,
                "max_per_cycle": self.config.max_opportunities_per_cycle,
            },
        }

    async def health_check(self) -> dict[str, Any]:
        """Health check for the engine."""
        issues = []

        if not self._running:
            issues.append("Engine not running")

        if self._metrics.last_cycle_at:
            age = (datetime.now(UTC) - self._metrics.last_cycle_at).total_seconds()
            if age > self.config.cycle_interval_seconds * 3:
                issues.append(f"Last cycle {age:.0f}s ago (expected every {self.config.cycle_interval_seconds}s)")

        if self._metrics.errors:
            issues.append(f"{len(self._metrics.errors)} recent errors")

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "status": self.get_status(),
        }


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON
# ──────────────────────────────────────────────────────────────────────────

_discovery_engine: DiscoveryEngine | None = None


def get_discovery_engine(
    config: DiscoveryConfig | None = None,
    observation_engine: ObservationEngine | None = None,
) -> DiscoveryEngine:
    """Get or create the global discovery engine."""
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = DiscoveryEngine(config, observation_engine)
    return _discovery_engine


async def initialize_discovery_engine(
    config: DiscoveryConfig | None = None,
    observation_engine: ObservationEngine | None = None,
) -> DiscoveryEngine:
    """Initialize and start the discovery engine."""
    engine = get_discovery_engine(config, observation_engine)
    await engine.start()
    return engine


async def start_discovery_system(
    config: DiscoveryConfig | None = None,
    observation_engine: ObservationEngine | None = None,
) -> DiscoveryEngine:
    """Start the complete discovery system."""
    return await initialize_discovery_engine(config, observation_engine)
