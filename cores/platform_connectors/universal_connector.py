"""
Universal Platform Connector — bridges existing adapters to Sensor Network.

This is the main entry point for platform integration in OWNEX v6.
Each platform category maps to existing adapter cycles.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from core.events.event_bus import get_event_bus
from core.opportunity.adapters import get_adapters
from core.sensors.adapters.generic_adapter import GenericAdapterSensor
from core.sensors.base import SensorRegistry

logger = logging.getLogger("ownex.platform_connectors")


class PlatformCategory(Enum):
    """Platform categories matching OWNEX Work Cycles."""

    BUG_BOUNTY = "security"  # Security cycle
    DEV_BOUNTY = "forge"  # Forge cycle
    AI_WORK_DATA = "pulse"  # Pulse cycle
    FREELANCE = "freelance"  # Freelance cycle


@dataclass
class PlatformConfig:
    """Configuration for a platform connector."""

    name: str
    category: PlatformCategory
    adapter_platform: str  # Name used in adapter registry
    enabled: bool = True
    cadence_seconds: int = 3600  # Default 1 hour
    config: dict[str, Any] = field(default_factory=dict)
    last_run: datetime | None = None
    error_count: int = 0


@dataclass
class PlatformOpportunity:
    """Unified opportunity from any platform."""

    id: str
    platform: str
    category: PlatformCategory
    title: str
    description: str
    url: str | None
    reward: float
    currency: str
    difficulty: float
    estimated_hours: float
    tags: list[str]
    metadata: dict[str, Any]
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class UniversalPlatformConnector:
    """
    Universal connector that wraps existing adapters as sensors.

    This eliminates the need for separate PlatformConnector classes.
    All platforms are handled through the existing adapter registry.
    """

    def __init__(self):
        self.event_bus = get_event_bus()
        self.sensor_registry = SensorRegistry()
        self.configs: dict[str, PlatformConfig] = {}
        self._running = False
        self._monitor_tasks: list[asyncio.Task] = []

    def register_platform(self, config: PlatformConfig) -> None:
        """Register a platform connector."""
        self.configs[config.name] = config
        logger.info(f"Registered platform: {config.name} ({config.category.value})")

        # Create sensor from adapter
        adapters = get_adapters()
        adapter = adapters.get(config.adapter_platform)
        if adapter:
            sensor = GenericAdapterSensor(
                adapter=adapter,
                sensor_id=f"platform:{config.name}",
                cadence_seconds=config.cadence_seconds,
            )
            self.sensor_registry.register(sensor)
            logger.info(f"Created sensor for {config.name} -> {config.adapter_platform}")
        else:
            logger.warning(f"No adapter found for platform: {config.adapter_platform}")

    async def start_all(self) -> None:
        """Start monitoring all registered platforms."""
        self._running = True
        logger.info(f"Starting UniversalPlatformConnector with {len(self.configs)} platforms")

        # Start sensor registry background loop
        self._monitor_tasks.append(asyncio.create_task(self.sensor_registry.run_all()))

        # Start opportunity processing loop
        self._monitor_tasks.append(asyncio.create_task(self._process_opportunities_loop()))

        # Wait for all tasks
        await asyncio.gather(*self._monitor_tasks, return_exceptions=True)

    async def stop_all(self) -> None:
        """Stop all monitoring."""
        self._running = False
        for task in self._monitor_tasks:
            task.cancel()
        await asyncio.gather(*self._monitor_tasks, return_exceptions=True)
        self._monitor_tasks.clear()
        logger.info("Stopped UniversalPlatformConnector")

    async def _process_opportunities_loop(self) -> None:
        """Process observations from sensors into ranked opportunities."""
        while self._running:
            try:
                await self._collect_and_rank()
            except Exception as e:
                logger.error(f"Error in opportunity processing: {e}")
            await asyncio.sleep(60)  # Process every minute

    async def _collect_and_rank(self) -> None:
        """Collect observations from all sensors and rank them."""
        all_observations = []

        for sensor in self.sensor_registry.get_all():
            try:
                observations = await sensor.observe()
                all_observations.extend(observations)
            except Exception as e:
                logger.error(f"Sensor {sensor.id} failed: {e}")

        if all_observations:
            # Deduplicate
            unique = self._deduplicate(all_observations)

            # Emit to EventBus for downstream processing
            for obs in unique:
                await self.event_bus.publish(
                    "observation.new",
                    {
                        "id": obs.id,
                        "sensor_id": obs.sensor_id,
                        "title": obs.title,
                        "description": obs.description,
                        "source_type": obs.source_type,
                        "source_name": obs.source_name,
                        "url": obs.url,
                        "estimated_reward_min": obs.estimated_reward_min,
                        "estimated_reward_max": obs.estimated_reward_max,
                        "tags": obs.tags,
                        "observed_at": obs.observed_at,
                        "raw_data": obs.raw_data,
                    },
                )

            logger.info(f"Processed {len(unique)} unique observations from {len(all_observations)} total")

    def _deduplicate(self, observations: list[Any]) -> list[Any]:
        """Remove duplicate observations by external_id + sensor."""
        seen = set()
        unique = []
        for obs in observations:
            key = (obs.sensor_id, obs.external_id)
            if key not in seen:
                seen.add(key)
                unique.append(obs)
        return unique

    def get_status(self) -> dict[str, Any]:
        """Get status of all platform connectors."""
        return {
            "running": self._running,
            "platforms": {
                name: {
                    "category": config.category.value,
                    "adapter": config.adapter_platform,
                    "enabled": config.enabled,
                    "cadence": config.cadence_seconds,
                    "last_run": config.last_run.isoformat() if config.last_run else None,
                    "errors": config.error_count,
                }
                for name, config in self.configs.items()
            },
            "sensors": len(self.sensor_registry.get_all()),
        }


# ──────────────────────────────────────────────────────────────────────────
# DEFAULT PLATFORM CONFIGURATIONS
# ──────────────────────────────────────────────────────────────────────────

DEFAULT_PLATFORMS = [
    # BUG BOUNTY (Security Cycle)
    PlatformConfig(
        name="rastro",
        category=PlatformCategory.BUG_BOUNTY,
        adapter_platform="rastro",
        cadence_seconds=300,  # 5 min
    ),
    PlatformConfig(
        name="aegis",
        category=PlatformCategory.BUG_BOUNTY,
        adapter_platform="aegis",
        cadence_seconds=600,  # 10 min
    ),
    PlatformConfig(
        name="hackerone",
        category=PlatformCategory.BUG_BOUNTY,
        adapter_platform="hackerone",
        cadence_seconds=900,  # 15 min
    ),
    PlatformConfig(
        name="bugcrowd",
        category=PlatformCategory.BUG_BOUNTY,
        adapter_platform="bugcrowd",
        cadence_seconds=900,
    ),
    PlatformConfig(
        name="intigriti",
        category=PlatformCategory.BUG_BOUNTY,
        adapter_platform="intigriti",
        cadence_seconds=900,
    ),
    # DEV BOUNTY (Forge Cycle)
    PlatformConfig(
        name="superteam",
        category=PlatformCategory.DEV_BOUNTY,
        adapter_platform="superteam",
        cadence_seconds=1800,  # 30 min
    ),
    PlatformConfig(
        name="opire",
        category=PlatformCategory.DEV_BOUNTY,
        adapter_platform="opire",
        cadence_seconds=1800,
    ),
    PlatformConfig(
        name="algora",
        category=PlatformCategory.DEV_BOUNTY,
        adapter_platform="algora",
        cadence_seconds=1800,
    ),
    PlatformConfig(
        name="issuehunt",
        category=PlatformCategory.DEV_BOUNTY,
        adapter_platform="issuehunt",
        cadence_seconds=1800,
    ),
    PlatformConfig(
        name="gitcoin",
        category=PlatformCategory.DEV_BOUNTY,
        adapter_platform="gitcoin",
        cadence_seconds=3600,
    ),
    PlatformConfig(
        name="github_sponsors",
        category=PlatformCategory.DEV_BOUNTY,
        adapter_platform="github_sponsors",
        cadence_seconds=3600,
    ),
    PlatformConfig(
        name="opencollective",
        category=PlatformCategory.DEV_BOUNTY,
        adapter_platform="opencollective",
        cadence_seconds=3600,
    ),
    # AI WORK / DATA TASKS (Pulse Cycle)
    PlatformConfig(
        name="outlier",
        category=PlatformCategory.AI_WORK_DATA,
        adapter_platform="outlier",
        cadence_seconds=3600,
    ),
    PlatformConfig(
        name="dataannotation",
        category=PlatformCategory.AI_WORK_DATA,
        adapter_platform="dataannotation",
        cadence_seconds=3600,
    ),
    PlatformConfig(
        name="mindrift",
        category=PlatformCategory.AI_WORK_DATA,
        adapter_platform="mindrift",
        cadence_seconds=3600,
    ),
    PlatformConfig(
        name="remotasks",
        category=PlatformCategory.AI_WORK_DATA,
        adapter_platform="remotasks",
        cadence_seconds=3600,
    ),
    PlatformConfig(
        name="opyre_microtask",
        category=PlatformCategory.AI_WORK_DATA,
        adapter_platform="opyre_microtask",
        cadence_seconds=3600,
    ),
    PlatformConfig(
        name="linkedin_easyapply",
        category=PlatformCategory.AI_WORK_DATA,
        adapter_platform="linkedin_easyapply",
        cadence_seconds=7200,
    ),
    # FREELANCE (Freelance Cycle)
    PlatformConfig(
        name="freelancer",
        category=PlatformCategory.FREELANCE,
        adapter_platform="freelancer",
        cadence_seconds=3600,
    ),
    PlatformConfig(
        name="freelancer_microtask",
        category=PlatformCategory.FREELANCE,
        adapter_platform="freelancer_microtask",
        cadence_seconds=3600,
    ),
    PlatformConfig(
        name="linkedin",
        category=PlatformCategory.FREELANCE,
        adapter_platform="linkedin",
        cadence_seconds=7200,
    ),
    PlatformConfig(
        name="upwork",
        category=PlatformCategory.FREELANCE,
        adapter_platform="upwork",
        cadence_seconds=3600,
    ),
]


def create_default_connector() -> UniversalPlatformConnector:
    """Create connector with all default platforms."""
    connector = UniversalPlatformConnector()
    for config in DEFAULT_PLATFORMS:
        connector.register_platform(config)
    return connector


async def main():
    """Run the universal platform connector."""
    logging.basicConfig(level=logging.INFO)

    connector = create_default_connector()

    try:
        await connector.start_all()
    except KeyboardInterrupt:
        await connector.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
