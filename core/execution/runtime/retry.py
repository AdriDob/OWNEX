from __future__ import annotations

import logging
import random
from collections.abc import Callable
from enum import Enum
from typing import Any

from core.execution.runtime.clock import VirtualClock

logger = logging.getLogger("ownex.execution.retry")


class RetryPolicy(str, Enum):
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    JITTER = "jitter"
    CIRCUIT_BREAKER = "circuit_breaker"
    MANUAL = "manual"


class RetryEngine:
    """Configurable retry engine with multiple policies.

    Policies:
    - IMMEDIATE: retry instantly
    - LINEAR: constant delay between retries
    - EXPONENTIAL: base_delay * 2^attempt
    - JITTER: exponential + random jitter
    - CIRCUIT_BREAKER: fail after N consecutive failures with cooldown
    - MANUAL: always fail, requiring human intervention
    """

    def __init__(
        self,
        clock: VirtualClock,
        on_retry_fn: Callable[[str, int, int], None] | None = None,
    ) -> None:
        self.clock = clock
        self._on_retry = on_retry_fn
        self._failure_counts: dict[str, int] = {}
        self._circuit_open: dict[str, bool] = {}
        self._circuit_cooldown_until: dict[str, float] = {}

    def should_retry(
        self,
        capability: str,
        attempt: int,
        max_retries: int,
        policy: RetryPolicy = RetryPolicy.EXPONENTIAL,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 60000,
        circuit_breaker_threshold: int = 5,
        circuit_cooldown_ms: int = 30000,
    ) -> bool:
        if attempt >= max_retries:
            return False

        if policy == RetryPolicy.MANUAL:
            return False

        if policy == RetryPolicy.CIRCUIT_BREAKER:
            return self._check_circuit_breaker(capability, circuit_breaker_threshold, circuit_cooldown_ms)

        return True

    def execute_retry(
        self,
        capability: str,
        fn: Callable[[], Any],
        max_retries: int,
        policy: RetryPolicy = RetryPolicy.EXPONENTIAL,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 60000,
        circuit_breaker_threshold: int = 5,
        circuit_cooldown_ms: int = 30000,
    ) -> tuple[Any, int, bool]:
        for attempt in range(max_retries + 1):
            try:
                result = fn()
                self._failure_counts[capability] = 0
                self._circuit_open[capability] = False
                return result, attempt, True
            except Exception:
                self._failure_counts[capability] = self._failure_counts.get(capability, 0) + 1
                if not self.should_retry(
                    capability,
                    attempt,
                    max_retries,
                    policy,
                    base_delay_ms,
                    max_delay_ms,
                    circuit_breaker_threshold,
                    circuit_cooldown_ms,
                ):
                    break
                delay = self._calculate_delay(attempt, policy, base_delay_ms, max_delay_ms)
                logger.info(
                    "[Retry] %s attempt %d/%d failed, retrying in %dms", capability, attempt + 1, max_retries, delay
                )
                if self._on_retry:
                    self._on_retry(capability, attempt, max_retries)
                self.clock.wait(delay)

        return None, max_retries, False

    def _calculate_delay(
        self,
        attempt: int,
        policy: RetryPolicy,
        base_delay_ms: int,
        max_delay_ms: int,
    ) -> float:
        if policy == RetryPolicy.IMMEDIATE:
            return 0.0
        if policy == RetryPolicy.LINEAR:
            return float(min(base_delay_ms, max_delay_ms))
        if policy == RetryPolicy.EXPONENTIAL:
            delay = base_delay_ms * (2**attempt)
            return float(min(delay, max_delay_ms))
        if policy == RetryPolicy.JITTER:
            delay = base_delay_ms * (2**attempt)
            jittered = delay * (0.5 + random.random())
            return float(min(jittered, max_delay_ms))
        if policy == RetryPolicy.CIRCUIT_BREAKER:
            return float(min(base_delay_ms, max_delay_ms))
        return float(base_delay_ms)

    def _check_circuit_breaker(
        self,
        capability: str,
        threshold: int,
        cooldown_ms: int,
    ) -> bool:
        now = self.clock.now()
        if self._circuit_open.get(capability):
            if now >= self._circuit_cooldown_until.get(capability, 0):
                self._circuit_open[capability] = False
                logger.info("[Retry] Circuit breaker reset for %s", capability)
                return True
            logger.warning("[Retry] Circuit breaker open for %s", capability)
            return False
        if self._failure_counts.get(capability, 0) >= threshold:
            self._circuit_open[capability] = True
            self._circuit_cooldown_until[capability] = now + cooldown_ms / 1000.0
            logger.warning("[Retry] Circuit breaker opened for %s (cooldown %dms)", capability, cooldown_ms)
            return False
        return True
