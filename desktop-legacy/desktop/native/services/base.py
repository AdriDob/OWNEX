"""Base service primitives shared across native services."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field

logger = logging.getLogger("ownex.native.services")


@dataclass
class AsyncResult:
    """Thin envelope for async-bound operations surfaced to the GUI thread."""

    ok: bool
    payload: object = None
    error: str | None = None


@dataclass
class TaskSpec:
    """Describes a background task the service can run off the UI thread."""

    name: str
    fn: Callable[..., object]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    on_done: Callable[[AsyncResult], None] | None = None
    on_progress: Callable[[str, float], None] | None = None


class ServiceError(Exception):
    """Raised when an in-process service call fails."""


@contextmanager
def service_call():
    """Wrap a service call: log timing/errors, never leak tracebacks to the UI."""
    import time

    t0 = time.perf_counter()
    try:
        yield
    except ServiceError:
        raise
    except Exception as exc:  # noqa: BLE001
        dt = (time.perf_counter() - t0) * 1000
        logger.exception("service call failed (%dms): %s", dt, exc)
        raise ServiceError(str(exc)) from exc
    else:
        dt = (time.perf_counter() - t0) * 1000
        logger.debug("service call ok (%dms)", dt)


def safe_call(fn: Callable[..., object], *args, **kwargs) -> object:
    """Call a service function, returning Result envelope instead of raising."""
    try:
        with service_call():
            return fn(*args, **kwargs)
    except ServiceError as exc:
        return AsyncResult(ok=False, error=str(exc))
    return AsyncResult(ok=True, payload=fn(*args, **kwargs))


__all__ = [
    "AsyncResult",
    "TaskSpec",
    "ServiceError",
    "service_call",
    "safe_call",
]
