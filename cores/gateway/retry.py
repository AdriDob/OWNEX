"""Retry with exponential backoff, jitter, and error classification for external API calls."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")

logger = logging.getLogger("ownex.gateway.retry")

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 30.0
DEFAULT_TIMEOUT = 30.0
DEFAULT_JITTER = 0.1


class RetryableError(Exception):
    """An error that may succeed if retried (transient failure)."""


class NonRetryableError(Exception):
    """An error that will not succeed on retry (permanent failure)."""


@dataclass
class RetryConfig:
    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay: float = DEFAULT_BASE_DELAY
    max_delay: float = DEFAULT_MAX_DELAY
    timeout: float = DEFAULT_TIMEOUT
    jitter: float = DEFAULT_JITTER
    retryable_exceptions: tuple[type[Exception], ...] = (
        TimeoutError,
        asyncio.TimeoutError,
        ConnectionError,
        ConnectionRefusedError,
        ConnectionResetError,
        ConnectionAbortedError,
        RetryableError,
    )
    non_retryable_exceptions: tuple[type[Exception], ...] = (
        NonRetryableError,
    )


def classify_error(exc: Exception, config: RetryConfig | None = None) -> bool:
    """Return True if the error is retryable, False if permanent."""
    cfg = config or RetryConfig()
    if isinstance(exc, cfg.non_retryable_exceptions):
        return False
    return bool(isinstance(exc, cfg.retryable_exceptions))


def _backoff_delay(attempt: int, config: RetryConfig) -> float:
    delay = min(config.base_delay * (2 ** attempt), config.max_delay)
    jitter = random.uniform(0, config.jitter * delay)
    return delay + jitter


async def retry_async(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> T:
    """Execute an async call with retry logic.

    Args:
        fn: The async function to call.
        config: Retry configuration.
        *args, **kwargs: Passed to fn.

    Returns:
        The return value of fn.

    Raises:
        The last exception encountered (retryable or not) if all retries fail.
    """
    cfg = config or RetryConfig()
    last_exc: Exception | None = None

    for attempt in range(cfg.max_retries + 1):
        try:
            if attempt > 0:
                delay = _backoff_delay(attempt - 1, cfg)
                logger.info(
                    "[RETRY] attempt %d/%d for %s — waiting %.2fs",
                    attempt, cfg.max_retries, getattr(fn, "__name__", str(fn)), delay,
                )
                await asyncio.sleep(delay)

            if cfg.timeout > 0:
                result = await asyncio.wait_for(fn(*args, **kwargs), timeout=cfg.timeout)
            else:
                result = await fn(*args, **kwargs)

            if attempt > 0:
                logger.info("[RETRY] attempt %d succeeded for %s", attempt, getattr(fn, "__name__", str(fn)))
            return result

        except Exception as exc:
            last_exc = exc
            if not classify_error(exc, cfg):
                logger.warning("[RETRY] non-retryable error on %s: %s", getattr(fn, "__name__", str(fn)), exc)
                raise

            if attempt < cfg.max_retries:
                logger.warning(
                    "[RETRY] attempt %d/%d failed for %s: %s",
                    attempt + 1, cfg.max_retries, getattr(fn, "__name__", str(fn)), exc,
                )
            else:
                logger.error(
                    "[RETRY] all %d attempts failed for %s: %s",
                    cfg.max_retries + 1, getattr(fn, "__name__", str(fn)), exc,
                )

    assert last_exc is not None
    raise last_exc


async def retry_with_circuit_breaker(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig | None = None,
    circuit_breaker: Any = None,
    component: str = "unknown",
    **kwargs: Any,
) -> T:
    """Execute with retry + optional circuit breaker protection.

    If a circuit_breaker is provided and is open, raises immediately.
    Records failures in the breaker so subsequent calls are blocked.
    """
    if circuit_breaker is not None:
        state = circuit_breaker.state
        if state == "open":
            raise RetryableError(f"Circuit breaker open for {component} — call blocked")

    try:
        result = await retry_async(fn, *args, config=config, **kwargs)
        if circuit_breaker is not None:
            circuit_breaker.record_success()
        return result
    except Exception:
        if circuit_breaker is not None:
            circuit_breaker.record_failure()
        raise
