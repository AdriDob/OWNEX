"""Sensor abstract base + SensorRegistry + cache.

Every sensor in the Universal Sensor Network inherits from Sensor.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any

from core.sensors.observation import Observation
from cores.prometheus_metrics import (
    SENSOR_FETCH_DURATION_SECONDS,
    SENSOR_FETCH_TOTAL,
    SENSOR_HEALTH_STATUS,
    SENSOR_OBSERVATIONS_COLLECTED,
    record_sensor_fetch,
)

logger = logging.getLogger("ownex.sensors")


class Sensor(ABC):
    """A single sensor in the Universal Sensor Network.

    Each sensor monitors one source of work and emits Observations.
    Observations are atomic signals — classification happens AFTER collection.

    Lifecycle:
      initialize() → [ fetch() x N ] → stop()
    """

    id: str = ""
    name: str = ""
    source_type: str = ""
    source_name: str = ""
    cadence_seconds: int = 3600  # default: check every hour

    def __init__(self) -> None:
        self._running = False
        self._fetch_count = 0
        self._last_fetch: float | None = None
        self._last_error: str | None = None

    @abstractmethod
    async def fetch(self) -> list[Observation]:
        """Fetch observations from the source.

        Must return Observable objects, not opportunities.
        Classification happens downstream.
        """
        raise NotImplementedError

    async def _record_fetch(self, duration: float, success: bool, obs_count: int) -> None:
        """Record sensor fetch metrics."""
        record_sensor_fetch(
            sensor_id=self.id,
            source_type=self.source_type,
            source_name=self.source_name,
            duration=duration,
            success=success,
            obs_count=obs_count,
        )
        SENSOR_FETCH_TOTAL.labels(
            sensor_id=self.id,
            source_type=self.source_type,
            source_name=self.source_name,
            status="success" if success else "error",
        ).inc()
        SENSOR_FETCH_DURATION_SECONDS.labels(sensor_id=self.id, source_type=self.source_type).observe(duration)
        if success and obs_count > 0:
            SENSOR_OBSERVATIONS_COLLECTED.labels(
                sensor_id=self.id, source_type=self.source_type, source_name=self.source_name
            ).inc(obs_count)
        SENSOR_HEALTH_STATUS.labels(sensor_id=self.id, source_type=self.source_type, source_name=self.source_name).set(
            1 if success else -1
        )

    async def fetch_with_metrics(self) -> list[Observation]:
        """Fetch with metrics recording - wrapper for sensors to use."""
        import time

        start = time.time()
        try:
            observations = await self.fetch()
            await self._record_fetch(time.time() - start, True, len(observations))
            return observations
        except Exception:
            await self._record_fetch(time.time() - start, False, 0)
            raise

    async def health(self) -> dict[str, Any]:
        """Return sensor health."""
        return {
            "id": self.id,
            "name": self.name,
            "running": self._running,
            "fetch_count": self._fetch_count,
            "last_fetch": self._last_fetch,
            "last_error": self._last_error,
            "cadence_seconds": self.cadence_seconds,
        }


class ObservationCache:
    """Short-term deduplication cache for observations.

    Prevents the same observation from entering the pipeline twice.
    Uses a simple LRU dict keyed by (sensor_id, external_id).

    Observations expire after cache_ttl_seconds to allow re-discovery.
    """

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 86400) -> None:
        self._cache: OrderedDict[str, float] = OrderedDict()  # key → timestamp
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _make_key(self, observation: Observation) -> str:
        return observation.dedup_key()

    def is_duplicate(self, observation: Observation) -> bool:
        """Check if observation is a duplicate (seen recently)."""
        key = self._make_key(observation)
        now = time.time()

        # Clean expired entries
        self._evict_expired(now)

        if key in self._cache:
            return True

        self._cache[key] = now
        self._evict_lru()

        return False

    def mark_seen(self, observation: Observation) -> None:
        """Manually mark an observation as seen (e.g., from history)."""
        key = self._make_key(observation)
        self._cache[key] = time.time()

    def _evict_expired(self, now: float) -> None:
        expired_keys = [k for k, v in self._cache.items() if now - v > self._ttl]
        for k in expired_keys:
            del self._cache[k]

    def _evict_lru(self) -> None:
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)
