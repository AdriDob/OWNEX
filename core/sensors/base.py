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
