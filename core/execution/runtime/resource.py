from __future__ import annotations

import logging
import time as _real_time
from typing import Any

logger = logging.getLogger("ownex.execution.resource")


class ResourceManager:
    """Prevents resource exhaustion across workflows.

    Tracks named resources (Shodan API, VirusTotal API, etc.)
    and enforces max concurrency per resource.

    When a resource is at capacity, the scheduler must wait
    until a slot frees up.
    """

    def __init__(self) -> None:
        self._resources: dict[str, int] = {}
        self._max_concurrency: dict[str, int] = {}
        self._active: dict[str, set[str]] = {}
        self._rate_limits: dict[str, tuple[int, float]] = {}

    def register_resource(
        self,
        name: str,
        max_concurrency: int = 1,
        rate_limit_per_sec: int = 0,
    ) -> None:
        self._max_concurrency[name] = max_concurrency
        self._active[name] = set()
        if rate_limit_per_sec > 0:
            self._rate_limits[name] = (rate_limit_per_sec, _real_time.time())

    def acquire(self, resource_name: str, execution_id: str) -> bool:
        if resource_name not in self._max_concurrency:
            self.register_resource(resource_name)
        active = self._active[resource_name]
        if len(active) >= self._max_concurrency[resource_name]:
            logger.warning(
                "[Resource] %s at capacity (%d/%d), rejecting %s",
                resource_name,
                len(active),
                self._max_concurrency[resource_name],
                execution_id,
            )
            return False
        if resource_name in self._rate_limits:
            limit, window_start = self._rate_limits[resource_name]
            elapsed = _real_time.time() - window_start
            allowed = int(limit * elapsed)
            if len(active) >= allowed:
                logger.warning(
                    "[Resource] %s rate limited, rejecting %s",
                    resource_name,
                    execution_id,
                )
                return False
        active.add(execution_id)
        logger.debug("[Resource] %s acquired by %s", resource_name, execution_id)
        return True

    def release(self, resource_name: str, execution_id: str) -> None:
        active = self._active.get(resource_name)
        if active and execution_id in active:
            active.remove(execution_id)

    def release_all(self, execution_id: str) -> None:
        for resource_name in self._active:
            self._active[resource_name].discard(execution_id)

    def get_status(self) -> dict[str, Any]:
        return {
            name: {
                "active": len(self._active.get(name, set())),
                "max": self._max_concurrency.get(name, 1),
                "available": self._max_concurrency.get(name, 1) - len(self._active.get(name, set())),
            }
            for name in self._max_concurrency
        }

    def is_available(self, resource_name: str) -> bool:
        active = self._active.get(resource_name, set())
        max_conc = self._max_concurrency.get(resource_name, 1)
        return len(active) < max_conc
