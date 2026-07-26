from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger("cateye.ai_router.provider_store")

STATUS_PATH = os.path.expanduser("~/.orion/ai_provider_status.json")

PROVIDER_READY = "ready"
PROVIDER_DEGRADED = "degraded"
PROVIDER_COOLDOWN = "cooldown"
PROVIDER_QUOTA_EXCEEDED = "quota_exceeded"
PROVIDER_OFFLINE = "offline"
PROVIDER_ERROR = "error"

ALL_STATUSES = {
    PROVIDER_READY,
    PROVIDER_DEGRADED,
    PROVIDER_COOLDOWN,
    PROVIDER_QUOTA_EXCEEDED,
    PROVIDER_OFFLINE,
    PROVIDER_ERROR,
}


@dataclass
class ProviderEntry:
    name: str
    status: str = PROVIDER_OFFLINE
    model: str = ""
    latency_ms: float = 0.0
    error: str = ""
    cooldown_until: float = 0.0
    consecutive_failures: int = 0
    last_seen: float = 0.0

    @property
    def is_available(self) -> bool:
        return (
            self.status in (PROVIDER_READY, PROVIDER_DEGRADED)
            or (self.status == PROVIDER_COOLDOWN and time.time() >= self.cooldown_until)
        )

    @property
    def cooldown_remaining(self) -> float:
        if self.status != PROVIDER_COOLDOWN:
            return 0.0
        return max(0.0, self.cooldown_until - time.time())

    def mark_cooldown(self, duration: float = 60.0) -> None:
        self.status = PROVIDER_COOLDOWN
        self.cooldown_until = time.time() + duration

    def mark_error(self, error_msg: str) -> None:
        self.status = PROVIDER_ERROR
        self.error = error_msg
        self.consecutive_failures += 1

    def mark_ready(self, latency_ms: float = 0.0) -> None:
        self.status = PROVIDER_READY
        self.error = ""
        self.consecutive_failures = 0
        self.latency_ms = latency_ms
        self.last_seen = time.time()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "model": self.model,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
            "cooldown_until": self.cooldown_until,
            "consecutive_failures": self.consecutive_failures,
            "last_seen": self.last_seen,
            "cooldown_remaining": round(self.cooldown_remaining, 1),
            "is_available": self.is_available,
        }


class ProviderStatusStore:
    def __init__(self, path: str = STATUS_PATH) -> None:
        self._path = path
        self._providers: dict[str, ProviderEntry] = {}
        self._load()

    def get(self, name: str) -> ProviderEntry | None:
        return self._providers.get(name)

    def get_or_create(self, name: str) -> ProviderEntry:
        if name not in self._providers:
            self._providers[name] = ProviderEntry(name=name)
        return self._providers[name]
