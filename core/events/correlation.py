"""Correlation ID — propagate a single trace ID through an end-to-end workflow.

Usage:

    from cores.events.correlation import get_or_create_correlation_id, with_correlation_id

    # Auto-generate if none exists
    cid = get_or_create_correlation_id()

    # Propagate explicitly
    with with_correlation_id(existing_cid):
        process_workflow()
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Generator
from contextlib import contextmanager

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Return the current correlation ID, or empty string if none set."""
    return _correlation_id.get()


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id.set(cid)


def get_or_create_correlation_id() -> str:
    """Return the current correlation ID, or generate a new one."""
    cid = _correlation_id.get()
    if not cid:
        cid = uuid.uuid4().hex
        _correlation_id.set(cid)
    return cid


def new_correlation_id() -> str:
    """Generate and set a fresh correlation ID."""
    cid = uuid.uuid4().hex
    _correlation_id.set(cid)
    return cid


@contextmanager
def with_correlation_id(cid: str) -> Generator[None, None, None]:
    """Temporarily set a correlation ID within a context."""
    token = _correlation_id.set(cid)
    try:
        yield
    finally:
        _correlation_id.reset(token)


@contextmanager
def with_new_correlation_id() -> Generator[str, None, None]:
    """Generate a new correlation ID within a context and yield it."""
    cid = new_correlation_id()
    token = _correlation_id.set(cid)
    try:
        yield cid
    finally:
        _correlation_id.reset(token)
