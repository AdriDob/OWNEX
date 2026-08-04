"""OAR Health Monitor — Continuous health monitoring for all providers."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable
from datetime import datetime

from .interfaces import (
    AIProviderProtocol,
    HealthMonitorProtocol,
    HealthStatus,
    OARConfig,
    ProviderHealth,
    get_config,
)

logger = logging.getLogger("oar.health")


class HealthMonitor(HealthMonitorProtocol):
    """Continuous health monitoring for all AI providers."""

    def __init__(self, registry, config: OARConfig | None = None):
        self._registry = registry
        self._config = config or get_config()
        self._health: dict[str, ProviderHealth] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._start_times: dict[str, float] = {}
        self._check_functions: dict[str, Awaitable[ProviderHealth]] = {}

    def register_check(self, provider_id: str, check_fn: Awaitable[ProviderHealth]) -> None:
        """Register a custom health check function for a provider."""
        self._check_functions[provider_id] = check_fn

    async def start(self) -> None:
        """Start continuous health monitoring."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started (interval: %ds)", self._config.health_check_interval_seconds)

        # Initial health check
        await self.check_all()

    async def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Health monitor stopped")

    async def check_all(self) -> dict[str, ProviderHealth]:
        """Check health of all registered providers."""
        results = {}
        for provider_id, provider in self._registry._providers.items():
            health = await self._check_provider(provider)
            results[provider_id] = health
            self._health[provider_id] = health
        return results

    async def _check_provider(self, provider: AIProviderProtocol) -> ProviderHealth:
        """Check health of a single provider."""
        start = time.monotonic()
        provider_id = provider.provider_id

        # Track uptime
        if provider_id not in self._start_times:
            self._start_times[provider_id] = start

        try:
            # Use custom check if registered, otherwise use provider's check_health
            if provider_id in self._check_functions:
                health = await self._check_functions[provider_id]
            else:
                health = await provider.check_health()

            # Update uptime
            health.uptime_seconds = start - self._start_times[provider_id]
            health.last_check = datetime.now()

            # Calculate error rate
            total = health.success_count + health.error_count
            if total > 0:
                health.error_rate = health.error_count / total

            # Determine status based on metrics
            health.status = self._determine_status(health)

            # Store on provider for quick access (using setattr to avoid protocol issues)
            provider._last_health = health

            logger.debug(
                "Health check %s: %s (%.0fms, err=%.2f%%)",
                provider_id,
                health.status.value,
                health.latency_ms,
                health.error_rate * 100,
            )

            return health

        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            health = ProviderHealth(
                provider_id=provider_id,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                last_error=str(e),
                error_count=1,
                last_check=datetime.now(),
            )
            provider._last_health = health
            logger.warning("Health check failed for %s: %s", provider_id, e)
            return health

    def _determine_status(self, health: ProviderHealth) -> HealthStatus:
        """Determine health status from metrics."""
        if health.last_error and "auth" in health.last_error.lower():
            return HealthStatus.AUTH_FAILED
        if health.last_error and "quota" in health.last_error.lower():
            return HealthStatus.QUOTA_EXCEEDED
        if health.error_rate > 0.5:
            return HealthStatus.UNHEALTHY
        if health.error_rate > 0.1 or health.latency_ms > 10000:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    async def _monitor_loop(self) -> None:
        """Continuous monitoring loop."""
        while self._running:
            try:
                await self.check_all()
            except Exception as e:
                logger.error("Health monitor loop error: %s", e)

            try:
                await asyncio.sleep(self._config.health_check_interval_seconds)
            except asyncio.CancelledError:
                break

    def get_health(self, provider_id: str) -> ProviderHealth | None:
        """Get current health for a provider."""
        return self._health.get(provider_id)

    def get_all_health(self) -> dict[str, ProviderHealth]:
        """Get health for all providers."""
        return self._health.copy()

    def get_healthy_providers(self) -> list[str]:
        """Get list of healthy provider IDs."""
        return [
            pid
            for pid, health in self._health.items()
            if health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        ]

    def get_degraded_providers(self) -> list[str]:
        """Get list of degraded provider IDs."""
        return [pid for pid, health in self._health.items() if health.status == HealthStatus.DEGRADED]

    def get_unhealthy_providers(self) -> list[str]:
        """Get list of unhealthy provider IDs."""
        return [
            pid
            for pid, health in self._health.items()
            if health.status in (HealthStatus.UNHEALTHY, HealthStatus.QUOTA_EXCEEDED, HealthStatus.AUTH_FAILED)
        ]


# Global health monitor instance
_health_monitor: HealthMonitor | None = None


def get_health_monitor(registry=None, config: OARConfig | None = None) -> HealthMonitor:
    """Get global health monitor."""
    global _health_monitor
    if _health_monitor is None:
        if registry is None:
            from .registry import get_registry

            registry = get_registry(config)
        _health_monitor = HealthMonitor(registry, config)
    return _health_monitor


async def initialize_health_monitor(registry=None, config: OARConfig | None = None) -> HealthMonitor:
    """Initialize and start the global health monitor."""
    monitor = get_health_monitor(registry, config)
    await monitor.start()
    return monitor
