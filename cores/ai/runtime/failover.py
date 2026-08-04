"""OAR Failover Engine — Circuit breakers and graceful degradation."""

from __future__ import annotations

import logging
import time

from .interfaces import (
    FailoverEngineProtocol,
    HealthMonitorProtocol,
    OARConfig,
    RoutingContext,
    get_config,
)
from .registry import ProviderRegistry

logger = logging.getLogger("oar.failover")


class FailoverEngine(FailoverEngineProtocol):
    """Intelligent failover with circuit breakers and graceful degradation."""

    def __init__(
        self,
        registry: ProviderRegistry,
        health_monitor: HealthMonitorProtocol,
        config: OARConfig | None = None,
    ):
        self._registry = registry
        self._health = health_monitor
        self._config = config or get_config()
        self._failure_counts: dict[str, int] = {}
        self._failure_times: dict[str, list[float]] = {}
        self._circuit_open: dict[str, bool] = {}
        self._circuit_open_time: dict[str, float] = {}

    def record_failure(self, provider_id: str, error: Exception) -> None:
        """Record a provider failure for circuit breaker logic."""
        now = time.monotonic()

        # Track failure count
        self._failure_counts[provider_id] = self._failure_counts.get(provider_id, 0) + 1

        # Track failure times for rate-based circuit breaking
        if provider_id not in self._failure_times:
            self._failure_times[provider_id] = []
        self._failure_times[provider_id].append(now)

        # Clean old failure times (older than circuit_breaker_timeout)
        cutoff = now - self._config.circuit_breaker_timeout_seconds
        self._failure_times[provider_id] = [t for t in self._failure_times[provider_id] if t > cutoff]

        # Check if circuit should open
        threshold = self._config.circuit_breaker_threshold
        recent_failures = len(self._failure_times[provider_id])

        if recent_failures >= threshold and not self._circuit_open.get(provider_id, False):
            self._circuit_open[provider_id] = True
            self._circuit_open_time[provider_id] = now
            logger.warning(
                "Circuit breaker OPENED for %s (%d failures in %ds)",
                provider_id,
                recent_failures,
                self._config.circuit_breaker_timeout_seconds,
            )

    def record_success(self, provider_id: str) -> None:
        """Record a successful call to reset failure tracking."""
        if provider_id in self._failure_counts:
            self._failure_counts[provider_id] = max(0, self._failure_counts[provider_id] - 1)

        # Close circuit if it was open and we have successes
        if self._circuit_open.get(provider_id, False) and self._failure_counts.get(provider_id, 0) == 0:
            self._circuit_open[provider_id] = False
            self._circuit_open_time.pop(provider_id, None)
            logger.info("Circuit breaker CLOSED for %s", provider_id)

    def is_circuit_open(self, provider_id: str) -> bool:
        """Check if circuit breaker is open for a provider."""
        if not self._circuit_open.get(provider_id, False):
            return False

        # Auto-close after timeout
        open_time = self._circuit_open_time.get(provider_id, 0)
        if time.monotonic() - open_time > self._config.circuit_breaker_timeout_seconds:
            self._circuit_open[provider_id] = False
            self._circuit_open_time.pop(provider_id, None)
            self._failure_counts[provider_id] = 0
            self._failure_times[provider_id] = []
            logger.info("Circuit breaker AUTO-CLOSED for %s (timeout)", provider_id)
            return False

        return True

    def get_fallback_chain(self, primary_provider: str, context: RoutingContext) -> list[str]:
        """Get ordered fallback providers based on health, cost, and capabilities."""
        # Get all healthy providers
        healthy = self._health.get_healthy_providers()

        # Remove primary and excluded
        candidates = [p for p in healthy if p != primary_provider and p not in context.excluded_providers]

        # Filter by privacy requirement
        if context.privacy_required:
            candidates = [p for p in candidates if p in ["ollama", "lmstudio"]]

        # Filter by required capabilities
        if context.required_capabilities:
            filtered = []
            for p in candidates:
                models = self._registry._model_to_provider
                provider_models = [m for m, prov in models.items() if prov == p]
                has_caps = False
                for model in provider_models:
                    caps = self._registry.get_model_capabilities(model)
                    if caps and context.required_capabilities.issubset(caps.supports):
                        has_caps = True
                        break
                if has_caps:
                    filtered.append(p)
            candidates = filtered

        # Sort by tier preference (local > free > cheap > premium)
        tier_order = {
            "ollama": 0,
            "lmstudio": 0,
            "opencode": 1,
            "groq": 2,
            "together": 2,
            "deepinfra": 2,
            "cerebras": 2,
            "fcc": 3,
            "nvidia_nim": 3,
            "openrouter": 4,
        }
        candidates.sort(key=lambda p: tier_order.get(p, 5))

        # Limit fallback chain length
        return candidates[:5]


# Global failover engine instance
_failover_engine: FailoverEngine | None = None


def get_failover_engine(
    registry=None,
    health_monitor=None,
    config: OARConfig | None = None,
) -> FailoverEngine:
    """Get global failover engine."""
    global _failover_engine
    if _failover_engine is None:
        if registry is None:
            from .registry import get_registry

            registry = get_registry(config)
        if health_monitor is None:
            from .health import get_health_monitor

            health_monitor = get_health_monitor(registry, config)
        _failover_engine = FailoverEngine(registry, health_monitor, config)
    return _failover_engine
