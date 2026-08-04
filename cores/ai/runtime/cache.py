"""OAR Cache Layer — Semantic caching with embeddings."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any

from .interfaces import AIResponse, CacheProtocol, OARConfig, get_config

logger = logging.getLogger("oar.cache")


class SemanticCache(CacheProtocol):
    """Semantic cache using embeddings for similarity matching."""

    def __init__(self, config: OARConfig | None = None):
        self._config = config or get_config()
        self._cache: OrderedDict[str, tuple[AIResponse, float]] = OrderedDict()  # key -> (response, timestamp)
        self._embeddings: dict[str, list[float]] = {}  # key -> embedding
        self._max_entries = 10000
        self._hit_count = 0
        self._miss_count = 0

    def _generate_key(self, request_dict: dict[str, Any]) -> str:
        """Generate cache key from request."""
        # Normalize request for consistent keys
        normalized = {
            "messages": request_dict.get("messages", []),
            "model": request_dict.get("model"),
            "max_tokens": request_dict.get("max_tokens", 4096),
            "temperature": request_dict.get("temperature", 0.3),
            "task_type": request_dict.get("task_type", "chat"),
        }
        content = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    async def get(self, key: str) -> AIResponse | None:
        """Get cached response."""
        if not self._config.enable_cache:
            return None

        if key in self._cache:
            response, timestamp = self._cache[key]
            # Check TTL
            if time.time() - timestamp < self._config.cache_ttl_seconds:
                self._hit_count += 1
                # Move to end (LRU)
                self._cache.move_to_end(key)
                logger.debug("Cache HIT: %s", key[:8])
                return response
            else:
                # Expired
                del self._cache[key]
                self._embeddings.pop(key, None)

        self._miss_count += 1
        logger.debug("Cache MISS: %s", key[:8])
        return None

    async def set(self, key: str, response: AIResponse, ttl_seconds: int = 3600) -> None:
        """Cache a response."""
        if not self._config.enable_cache:
            return

        # Evict if at capacity
        while len(self._cache) >= self._max_entries:
            self._cache.popitem(last=False)
            self._embeddings.pop(next(iter(self._embeddings)), None)

        self._cache[key] = (response, time.time())
        logger.debug("Cache SET: %s", key[:8])

    async def invalidate(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        keys_to_remove = [k for k in self._cache if pattern in k]
        for key in keys_to_remove:
            del self._cache[key]
            self._embeddings.pop(key, None)
        logger.info("Invalidated %d cache entries matching '%s'", len(keys_to_remove), pattern)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0.0
        return {
            "entries": len(self._cache),
            "max_entries": self._max_entries,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": hit_rate,
            "ttl_seconds": self._config.cache_ttl_seconds,
        }

    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._embeddings.clear()
        self._hit_count = 0
        self._miss_count = 0


# Global cache instance
_cache: SemanticCache | None = None


def get_cache(config: OARConfig | None = None) -> SemanticCache:
    """Get global semantic cache."""
    global _cache
    if _cache is None:
        _cache = SemanticCache(config)
    return _cache
