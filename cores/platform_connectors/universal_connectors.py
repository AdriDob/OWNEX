"""Universal Platform Connectors — integrates all platform adapters into OWNEX.

This module provides the high-level connector interface that wraps the
existing OpportunityAdapter system via the Universal Sensor Network.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from core.events.event_bus import get_core_event_bus
from core.opportunity.adapters import (
    get_adapter_registry,
)
from core.sensors.adapters.generic_adapter import GenericAdapterSensor
from core.sensors.base import Sensor
from core.sensors.observation import Observation
from core.sensors.observation_engine import ObservationEngine, get_observation_engine
from cores.prometheus_metrics import (
    OPPORTUNITY_PROVIDER_HEALTH,
    OPPORTUNITY_PROVIDERS_ACTIVE,
    record_opportunity_discovered,
)

logger = logging.getLogger("ownex.platform_connectors")


class PlatformCategory(Enum):
    """Categories of work platforms."""

    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    DATA_ANNOTATION = "data_annotation"
    FREELANCE = "freelance"
    CRYPTO = "crypto"
    SOCIAL = "social"


class PlatformStatus(Enum):
    """Platform connector status."""

    IDLE = "idle"
    CONNECTING = "connecting"
    ACTIVE = "active"
    DEGRADED = "degraded"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PlatformConfig:
    """Configuration for a platform connector."""

    platform_id: str
    name: str
    category: PlatformCategory
    adapter_name: str  # Name in AdapterRegistry
    enabled: bool = True
    cadence_seconds: int = 3600  # How often to poll
    config: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    # Auth is handled by the adapter via credentials vault
    # No secrets stored here


@dataclass
class PlatformMetrics:
    """Runtime metrics for a platform."""

    status: PlatformStatus = PlatformStatus.IDLE
    last_run: datetime | None = None
    last_success: datetime | None = None
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    opportunities_found: int = 0
    last_error: str | None = None
    next_run: datetime | None = None


class UniversalPlatformConnector:
    """
    Universal connector for any work platform.

    Wraps an OpportunityAdapter as a Sensor in the Universal Sensor Network.
    Provides unified interface for discovery, monitoring, and management.
    """

    def __init__(self, config: PlatformConfig):
        self.config = config
        self.metrics = PlatformMetrics()
        self._sensor: Sensor | None = None
        self._engine: ObservationEngine | None = None
        self._task: asyncio.Task | None = None
        self._running = False
        self._event_bus = get_core_event_bus()

    async def initialize(self) -> bool:
        """Initialize the connector and its sensor."""
        try:
            # Get the adapter from registry
            registry = get_adapter_registry()
            adapter_class = registry.get(self.config.adapter_name)

            if not adapter_class:
                logger.error("Adapter not found: %s", self.config.adapter_name)
                self.metrics.status = PlatformStatus.ERROR
                self.metrics.last_error = f"Adapter not found: {self.config.adapter_name}"
                return False

            # Create adapter instance
            adapter = adapter_class(config={"enabled": self.config.enabled, **self.config.config})

            if not adapter.is_enabled():
                logger.info("Adapter %s is disabled", self.config.adapter_name)
                self.metrics.status = PlatformStatus.DISABLED
                return True

            # Wrap as sensor
            self._sensor = GenericAdapterSensor(
                adapter=adapter,
                sensor_id=f"platform:{self.config.platform_id}",
                cadence_seconds=self.config.cadence_seconds,
            )

            # Initialize sensor
            self._sensor.id = f"platform:{self.config.platform_id}"
            self._sensor.name = self.config.name
            self._sensor.source_type = self.config.category.value
            self._sensor.source_name = self.config.adapter_name

            # Get observation engine
            self._engine = get_observation_engine()

            # Register sensor with engine
            self._engine.register_sensor(self._sensor)

            # Update Prometheus
            OPPORTUNITY_PROVIDERS_ACTIVE.labels(category=self.config.category.value).inc()
            OPPORTUNITY_PROVIDER_HEALTH.labels(
                provider=self.config.platform_id, category=self.config.category.value
            ).set(1)

            self.metrics.status = PlatformStatus.ACTIVE
            logger.info("Initialized platform connector: %s (%s)", self.config.name, self.config.platform_id)
            return True

        except Exception as e:
            logger.exception("Failed to initialize platform connector %s", self.config.platform_id)
            self.metrics.status = PlatformStatus.ERROR
            self.metrics.last_error = str(e)
            OPPORTUNITY_PROVIDER_HEALTH.labels(
                provider=self.config.platform_id, category=self.config.category.value
            ).set(-1)
            return False

    async def start_monitoring(self) -> None:
        """Start continuous monitoring."""
        if self._running:
            return

        if not self._sensor or self.metrics.status != PlatformStatus.ACTIVE:
            logger.warning("Cannot start monitoring for %s: not initialized", self.config.platform_id)
            return

        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started monitoring for platform: %s", self.config.platform_id)

        # Emit event
        self._event_bus.publish("platform:started", platform_id=self.config.platform_id)

    async def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Stopped monitoring for platform: %s", self.config.platform_id)

        # Emit event
        self._event_bus.publish("platform:stopped", platform_id=self.config.platform_id)

    async def _monitoring_loop(self) -> None:
        """Continuous monitoring loop."""
        while self._running:
            try:
                await self._run_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in monitoring loop for %s", self.config.platform_id)
                self.metrics.failed_runs += 1
                self.metrics.last_error = str(e)
                self.metrics.status = PlatformStatus.DEGRADED

            # Wait for next cadence
            await asyncio.sleep(self.config.cadence_seconds)

    async def _run_once(self) -> None:
        """Single monitoring cycle."""
        self.metrics.total_runs += 1
        self.metrics.last_run = datetime.now(UTC)
        self.metrics.status = PlatformStatus.ACTIVE

        if self._engine and self._sensor:
            # Run sensor through engine
            observations = await self._engine.collect_from_sensor(self._sensor.id)

            # Process observations
            count = len(observations)
            self.metrics.opportunities_found += count
            self.metrics.successful_runs += 1
            self.metrics.last_success = datetime.now(UTC)
            self.metrics.status = PlatformStatus.ACTIVE

            # Record Prometheus metrics
            for obs in observations:
                record_opportunity_discovered(
                    source=obs.source_name,
                    category=obs.source_type,
                    score=0.5,  # Will be scored downstream
                    evh=0.0,
                )

            # Emit event for new opportunities
            if observations:
                self._event_bus.publish(
                    "platform:opportunities_found",
                    platform_id=self.config.platform_id,
                    platform_name=self.config.name,
                    category=self.config.category.value,
                    count=count,
                    observations=[obs.to_dict() for obs in observations],
                )

            logger.debug("Platform %s: found %d opportunities", self.config.platform_id, count)

        # Calculate next run
        self.metrics.next_run = datetime.now(UTC)

    async def trigger_discovery(self) -> list[Observation]:
        """Manually trigger a discovery cycle."""
        if not self._engine or not self._sensor:
            return []
        return await self._engine.collect_from_sensor(self._sensor.id)

    def get_status(self) -> dict[str, Any]:
        """Get connector status."""
        return {
            "platform_id": self.config.platform_id,
            "name": self.config.name,
            "category": self.config.category.value,
            "adapter": self.config.adapter_name,
            "status": self.metrics.status.value,
            "enabled": self.config.enabled,
            "cadence_seconds": self.config.cadence_seconds,
            "metrics": {
                "total_runs": self.metrics.total_runs,
                "successful_runs": self.metrics.successful_runs,
                "failed_runs": self.metrics.failed_runs,
                "opportunities_found": self.metrics.opportunities_found,
                "last_run": self.metrics.last_run.isoformat() if self.metrics.last_run else None,
                "last_success": self.metrics.last_success.isoformat() if self.metrics.last_success else None,
                "last_error": self.metrics.last_error,
                "next_run": self.metrics.next_run.isoformat() if self.metrics.next_run else None,
            },
            "sensor_health": self._sensor.health() if self._sensor else None,
        }


class PlatformConnectorManager:
    """
    Manages all platform connectors.

    Provides unified control, monitoring, and discovery across all platforms.
    """

    def __init__(self):
        self.connectors: dict[str, UniversalPlatformConnector] = {}
        self._event_bus = get_core_event_bus()
        self._running = False

    def add_platform(self, config: PlatformConfig) -> UniversalPlatformConnector:
        """Add a new platform connector."""
        connector = UniversalPlatformConnector(config)
        self.connectors[config.platform_id] = connector
        logger.info("Added platform connector: %s", config.platform_id)
        return connector

    def remove_platform(self, platform_id: str) -> bool:
        """Remove a platform connector."""
        if platform_id in self.connectors:
            connector = self.connectors.pop(platform_id)
            if connector._running:
                asyncio.create_task(connector.stop_monitoring())
            logger.info("Removed platform connector: %s", platform_id)
            return True
        return False

    def get_connector(self, platform_id: str) -> UniversalPlatformConnector | None:
        """Get a connector by ID."""
        return self.connectors.get(platform_id)

    def get_all_connectors(self) -> list[UniversalPlatformConnector]:
        """Get all connectors."""
        return list(self.connectors.values())

    def get_connectors_by_category(self, category: PlatformCategory) -> list[UniversalPlatformConnector]:
        """Get connectors by category."""
        return [c for c in self.connectors.values() if c.config.category == category]

    async def initialize_all(self) -> dict[str, bool]:
        """Initialize all connectors."""
        results = {}
        for platform_id, connector in self.connectors.items():
            results[platform_id] = await connector.initialize()
        return results

    async def start_all(self) -> None:
        """Start monitoring for all active connectors."""
        self._running = True
        for connector in self.connectors.values():
            if connector.metrics.status == PlatformStatus.ACTIVE:
                await connector.start_monitoring()
        logger.info("Started all platform connectors")
        self._event_bus.publish("platforms:all_started")

    async def stop_all(self) -> None:
        """Stop all monitoring."""
        self._running = False
        for connector in self.connectors.values():
            await connector.stop_monitoring()
        logger.info("Stopped all platform connectors")
        self._event_bus.publish("platforms:all_stopped")

    async def trigger_discovery(self, platform_id: str | None = None) -> dict[str, list[Observation]]:
        """Trigger discovery on specific or all platforms."""
        results = {}

        if platform_id:
            connector = self.connectors.get(platform_id)
            if connector:
                results[platform_id] = await connector.trigger_discovery()
        else:
            for pid, connector in self.connectors.items():
                results[pid] = await connector.trigger_discovery()

        return results

    def get_system_status(self) -> dict[str, Any]:
        """Get overall system status."""
        active = sum(1 for c in self.connectors.values() if c.metrics.status == PlatformStatus.ACTIVE)
        degraded = sum(1 for c in self.connectors.values() if c.metrics.status == PlatformStatus.DEGRADED)
        error = sum(1 for c in self.connectors.values() if c.metrics.status == PlatformStatus.ERROR)
        disabled = sum(1 for c in self.connectors.values() if c.metrics.status == PlatformStatus.DISABLED)
        total_opps = sum(c.metrics.opportunities_found for c in self.connectors.values())

        return {
            "total_platforms": len(self.connectors),
            "active": active,
            "degraded": degraded,
            "error": error,
            "disabled": disabled,
            "total_opportunities_found": total_opps,
            "platforms": {pid: connector.get_status() for pid, connector in self.connectors.items()},
        }

    def get_opportunity_summary(self) -> dict[str, Any]:
        """Get summary of opportunities by category."""
        summary = {}
        for connector in self.connectors.values():
            cat = connector.config.category.value
            if cat not in summary:
                summary[cat] = {"platforms": 0, "opportunities": 0}
            summary[cat]["platforms"] += 1
            summary[cat]["opportunities"] += connector.metrics.opportunities_found
        return summary


# ──────────────────────────────────────────────────────────────────────────
# DEFAULT PLATFORM CONFIGURATIONS
# ──────────────────────────────────────────────────────────────────────────


def get_default_platform_configs() -> list[PlatformConfig]:
    """Get default platform configurations for all supported categories."""
    return [
        # ── Bug Bounty ──
        PlatformConfig(
            platform_id="hackerone",
            name="HackerOne",
            category=PlatformCategory.BUG_BOUNTY,
            adapter_name="rastro",  # Uses security adapter
            cadence_seconds=300,  # 5 minutes
            config={"enabled": True},
            tags=["security", "bug_bounty"],
        ),
        PlatformConfig(
            platform_id="bugcrowd",
            name="Bugcrowd",
            category=PlatformCategory.BUG_BOUNTY,
            adapter_name="rastro",
            cadence_seconds=300,
            config={"enabled": True},
            tags=["security", "bug_bounty"],
        ),
        PlatformConfig(
            platform_id="intigriti",
            name="Intigriti",
            category=PlatformCategory.BUG_BOUNTY,
            adapter_name="rastro",
            cadence_seconds=300,
            config={"enabled": True},
            tags=["security", "bug_bounty"],
        ),
        # ── Dev Bounty ──
        PlatformConfig(
            platform_id="superteam",
            name="Superteam",
            category=PlatformCategory.DEV_BOUNTY,
            adapter_name="superteam",
            cadence_seconds=600,  # 10 minutes
            config={"enabled": True},
            tags=["web3", "solana", "dev_bounty"],
        ),
        PlatformConfig(
            platform_id="opire",
            name="Opire",
            category=PlatformCategory.DEV_BOUNTY,
            adapter_name="opire",
            cadence_seconds=600,
            config={"enabled": True},
            tags=["oss", "github", "dev_bounty"],
        ),
        PlatformConfig(
            platform_id="algora",
            name="Algora",
            category=PlatformCategory.DEV_BOUNTY,
            adapter_name="algora",
            cadence_seconds=600,
            config={"enabled": True},
            tags=["oss", "github", "dev_bounty"],
        ),
        PlatformConfig(
            platform_id="issuehunt",
            name="IssueHunt",
            category=PlatformCategory.DEV_BOUNTY,
            adapter_name="issuehunt",
            cadence_seconds=600,
            config={"enabled": True},
            tags=["oss", "github", "dev_bounty"],
        ),
        PlatformConfig(
            platform_id="bountysource",
            name="Bountysource",
            category=PlatformCategory.DEV_BOUNTY,
            adapter_name="forge",  # Legacy forge adapter
            cadence_seconds=900,
            config={"enabled": True},
            tags=["oss", "dev_bounty"],
        ),
        PlatformConfig(
            platform_id="gitcoin",
            name="Gitcoin",
            category=PlatformCategory.DEV_BOUNTY,
            adapter_name="forge",
            cadence_seconds=900,
            config={"enabled": True},
            tags=["web3", "crypto", "dev_bounty"],
        ),
        # ── Data Annotation / AI Work ──
        PlatformConfig(
            platform_id="outlier",
            name="Outlier",
            category=PlatformCategory.DATA_ANNOTATION,
            adapter_name="outlier",
            cadence_seconds=1800,  # 30 minutes
            config={"enabled": True},
            tags=["ai", "data", "annotation"],
        ),
        PlatformConfig(
            platform_id="dataannotation",
            name="DataAnnotation.tech",
            category=PlatformCategory.DATA_ANNOTATION,
            adapter_name="dataannotation",
            cadence_seconds=1800,
            config={"enabled": True},
            tags=["ai", "data", "annotation"],
        ),
        PlatformConfig(
            platform_id="mindrift",
            name="Mindrift",
            category=PlatformCategory.DATA_ANNOTATION,
            adapter_name="mindrift",
            cadence_seconds=1800,
            config={"enabled": True},
            tags=["ai", "data", "annotation"],
        ),
        PlatformConfig(
            platform_id="remotasks",
            name="Remotasks",
            category=PlatformCategory.DATA_ANNOTATION,
            adapter_name="remotasks",
            cadence_seconds=1800,
            config={"enabled": True},
            tags=["ai", "data", "annotation"],
        ),
        PlatformConfig(
            platform_id="opyre_microtask",
            name="Opire Microtask",
            category=PlatformCategory.DATA_ANNOTATION,
            adapter_name="opyre_microtask",
            cadence_seconds=1800,
            config={"enabled": True},
            tags=["ai", "microtask"],
        ),
        PlatformConfig(
            platform_id="freelancer_microtask",
            name="Freelancer Microtask",
            category=PlatformCategory.DATA_ANNOTATION,
            adapter_name="freelancer_microtask",
            cadence_seconds=1800,
            config={"enabled": True},
            tags=["freelance", "microtask"],
        ),
        # ── Freelance ──
        PlatformConfig(
            platform_id="linkedin_jobs",
            name="LinkedIn Jobs",
            category=PlatformCategory.FREELANCE,
            adapter_name="linkedin",
            cadence_seconds=3600,  # 1 hour
            config={"enabled": True},
            tags=["freelance", "jobs"],
        ),
        PlatformConfig(
            platform_id="linkedin_easyapply",
            name="LinkedIn Easy Apply",
            category=PlatformCategory.FREELANCE,
            adapter_name="linkedin_easyapply",
            cadence_seconds=3600,
            config={"enabled": True},
            tags=["freelance", "easy_apply"],
        ),
        PlatformConfig(
            platform_id="freelancer",
            name="Freelancer.com",
            category=PlatformCategory.FREELANCE,
            adapter_name="freelancer",
            cadence_seconds=3600,
            config={"enabled": True},
            tags=["freelance", "projects"],
        ),
        # ── Crypto ──
        PlatformConfig(
            platform_id="coingecko",
            name="CoinGecko",
            category=PlatformCategory.CRYPTO,
            adapter_name="coingecko",
            cadence_seconds=300,
            config={"enabled": True},
            tags=["crypto", "prices"],
        ),
        PlatformConfig(
            platform_id="firefly",
            name="Firefly III",
            category=PlatformCategory.CRYPTO,
            adapter_name="firefly",
            cadence_seconds=3600,
            config={"enabled": True},
            tags=["finance", "budget"],
        ),
        # ── Atlas (OSINT/CVE) ──
        PlatformConfig(
            platform_id="cve",
            name="CVE Database",
            category=PlatformCategory.BUG_BOUNTY,
            adapter_name="cve",
            cadence_seconds=3600,
            config={"enabled": True},
            tags=["cve", "vulnerabilities", "osint"],
        ),
        PlatformConfig(
            platform_id="osint",
            name="OSINT Atlas",
            category=PlatformCategory.BUG_BOUNTY,
            adapter_name="osint",
            cadence_seconds=3600,
            config={"enabled": True},
            tags=["osint", "recon"],
        ),
    ]


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON MANAGER
# ──────────────────────────────────────────────────────────────────────────

_manager: PlatformConnectorManager | None = None


def get_platform_manager() -> PlatformConnectorManager:
    """Get or create the global platform connector manager."""
    global _manager
    if _manager is None:
        _manager = PlatformConnectorManager()
        # Initialize with defaults
        for config in get_default_platform_configs():
            _manager.add_platform(config)
    return _manager


async def initialize_platform_system() -> PlatformConnectorManager:
    """Initialize the complete platform system."""
    manager = get_platform_manager()
    await manager.initialize_all()
    return manager


async def start_platform_system() -> PlatformConnectorManager:
    """Start the complete platform system."""
    manager = await initialize_platform_system()
    await manager.start_all()
    return manager
