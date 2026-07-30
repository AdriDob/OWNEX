"""Sync Pipeline — orchestrates platform sync with rate-limiting, retry, and caching.

Every sync cycle:
  1. Acquire per-platform rate limiter
  2. Fetch delta (only changed records since last sync)
  3. Apply retry with exponential backoff on failure
  4. Update cache with TTL
  5. Run reconciliation check
  6. Record sync health
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cores.financial.truth_layer import (
    TruthLayer,
    get_truth_layer,
)
from cores.platforms.base import BugBountyPlatform, SyncResult

logger = logging.getLogger("ownex.financial.sync_pipeline")

DEFAULT_CACHE_TTL = 300  # 5 minutes
MAX_RETRIES = 5
INITIAL_BACKOFF = 10  # seconds


class SyncMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class DeltaType(str, Enum):
    NEW = "new"
    UPDATED = "updated"
    REMOVED = "removed"


@dataclass
class SyncConfig:
    mode: SyncMode = SyncMode.INCREMENTAL
    cache_ttl: int = DEFAULT_CACHE_TTL
    max_retries: int = MAX_RETRIES
    initial_backoff: int = INITIAL_BACKOFF
    rate_limit_per_minute: int = 30
    auto_reconcile: bool = True

    @classmethod
    def default(cls) -> SyncConfig:
        return cls()

    @classmethod
    def aggressive(cls) -> SyncConfig:
        return cls(mode=SyncMode.FULL, cache_ttl=60, max_retries=3, initial_backoff=5, rate_limit_per_minute=60)

    @classmethod
    def conservative(cls) -> SyncConfig:
        return cls(
            mode=SyncMode.INCREMENTAL, cache_ttl=600, max_retries=5, initial_backoff=30, rate_limit_per_minute=10
        )


@dataclass
class SyncReport:
    platform_id: str
    success: bool
    mode: SyncMode
    duration_ms: float
    entries_found: int
    entries_updated: int
    reconciliation_status: str
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class RateLimiter:
    """Token-bucket rate limiter per platform."""

    def __init__(self, tokens_per_minute: int = 30) -> None:
        self._tokens = tokens_per_minute
        self._max_tokens = tokens_per_minute
        self._last_refill = time.time()
        self._lock = False

    def acquire(self, timeout: float = 30.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._refill()
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            time.sleep(0.5)
        return False

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self._last_refill
        added = elapsed * (self._max_tokens / 60.0)
        self._tokens = min(self._max_tokens, self._tokens + added)
        self._last_refill = now


class SyncCache:
    """TTL cache for sync results."""

    def __init__(self, default_ttl: int = DEFAULT_CACHE_TTL) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._data[key] = (time.time() + (ttl or self._default_ttl), value)

    def invalidate(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()


class SyncPipeline:
    """Orchestrates multi-platform sync with rate-limiting, retry, and caching."""

    def __init__(self, truth_layer: TruthLayer | None = None) -> None:
        self._truth = truth_layer or get_truth_layer()
        self._limiters: dict[str, RateLimiter] = {}
        self._cache = SyncCache()
        self._last_sync_data: dict[str, dict[str, Any]] = {}

    def set_cache_ttl(self, ttl: int) -> None:
        self._cache = SyncCache(ttl)

    def get_limiter(self, platform_id: str, rpm: int = 30) -> RateLimiter:
        if platform_id not in self._limiters:
            self._limiters[platform_id] = RateLimiter(rpm)
        return self._limiters[platform_id]

    def sync_platform(
        self,
        platform: BugBountyPlatform,
        api_key: str,
        config: SyncConfig | None = None,
    ) -> SyncReport:
        cfg = config or SyncConfig.default()
        platform_id = platform.platform_id
        start = time.time()

        limiter = self.get_limiter(platform_id, cfg.rate_limit_per_minute)
        if not limiter.acquire():
            self._truth.record_sync_failure(platform_id, "rate_limited")
            return SyncReport(
                platform_id=platform_id,
                success=False,
                mode=cfg.mode,
                duration_ms=0,
                entries_found=0,
                entries_updated=0,
                reconciliation_status="failed",
                error="Rate limit exceeded",
            )

        if cfg.mode == SyncMode.FULL:
            result = self._sync_with_retry(platform, api_key, cfg)
        else:
            cache_key = f"sync:{platform_id}"
            cached = self._cache.get(cache_key)
            if cached is not None:
                result = cached
            else:
                result = self._sync_with_retry(platform, api_key, cfg)
                if result and result.success:
                    self._cache.set(cache_key, result, cfg.cache_ttl)

        duration = (time.time() - start) * 1000

        if result is None or not result.success:
            self._truth.record_sync_failure(platform_id, result.error if result else "no_result")
            return SyncReport(
                platform_id=platform_id,
                success=False,
                mode=cfg.mode,
                duration_ms=round(duration, 1),
                entries_found=0,
                entries_updated=0,
                reconciliation_status="failed",
                error=result.error if result else "Unknown error",
            )

        entries = result.earnings + result.payouts
        delta = self._detect_delta(platform_id, entries)
        self._last_sync_data[platform_id] = {e.get("id", ""): e for e in entries}

        self._truth.record_sync_success(platform_id)

        reconciliation_status = "skipped"
        if cfg.auto_reconcile:
            try:
                self._run_reconciliation(platform_id, entries)
                reconciliation_status = "consistent"
            except Exception as exc:
                reconciliation_status = f"error: {exc}"

        return SyncReport(
            platform_id=platform_id,
            success=True,
            mode=cfg.mode,
            duration_ms=round(duration, 1),
            entries_found=len(entries),
            entries_updated=len(delta),
            reconciliation_status=reconciliation_status,
            details={
                "earnings": len(result.earnings),
                "payouts": len(result.payouts),
                "programs": len(result.programs),
                "total_earned": result.total_earned,
                "total_pending": result.total_pending,
                "delta_entries": delta,
            },
        )

    def _sync_with_retry(
        self,
        platform: BugBountyPlatform,
        api_key: str,
        config: SyncConfig,
    ) -> SyncResult | None:
        last_error = ""
        for attempt in range(config.max_retries):
            try:
                result = platform.sync_earnings(api_key)
                if result.success:
                    return result
                last_error = result.error
            except Exception as exc:
                last_error = str(exc)

            if attempt < config.max_retries - 1:
                backoff = config.initial_backoff * (2**attempt)
                logger.info(
                    "Retry %d/%d for %s in %.1fs: %s",
                    attempt + 1,
                    config.max_retries,
                    platform.platform_id,
                    backoff,
                    last_error,
                )
                time.sleep(backoff)

        logger.error("All retries exhausted for %s: %s", platform.platform_id, last_error)
        return SyncResult(success=False, error=last_error)

    def _detect_delta(self, platform_id: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prev = self._last_sync_data.get(platform_id, {})
        current = {e.get("id", ""): e for e in entries}
        delta = []
        for eid, entry in current.items():
            if eid not in prev:
                delta.append({**entry, "_delta": DeltaType.NEW.value})
            elif prev[eid] != entry:
                delta.append({**entry, "_delta": DeltaType.UPDATED.value})
        for eid in prev:
            if eid not in current:
                delta.append({"_delta": DeltaType.REMOVED.value, "id": eid})
        return delta

    def _run_reconciliation(self, platform_id: str, entries: list[dict[str, Any]]) -> None:
        from cores.financial.reconciliation import get_reconciliation_engine

        engine = get_reconciliation_engine()
        engine.check_platform(self._truth, platform_id, entries)

    def sync_all(
        self,
        platforms: list[tuple[BugBountyPlatform, str]],
        config: SyncConfig | None = None,
    ) -> list[SyncReport]:
        return [self.sync_platform(p, key, config) for p, key in platforms]


_PIPELINE: SyncPipeline | None = None


def get_sync_pipeline() -> SyncPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = SyncPipeline()
    return _PIPELINE
