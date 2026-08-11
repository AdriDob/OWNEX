from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

EventHandler = Callable[..., Any]


class IEventBus(ABC):
    """Async-safe pub/sub with namespace support.

    Events follow the pattern: ``<app_id>:<event_name>``
    Example: ``cateye:finding:confirmed``, ``atlas:portfolio:updated``
    """

    @abstractmethod
    def publish(self, event: str, **data: Any) -> None:
        """Publish an event to all subscribers.

        Args:
            event: Fully qualified event name (e.g. ``atlas:price:updated``)
            data: Keyword arguments passed to each handler.
        """

    @abstractmethod
    def subscribe(self, event: str, handler: EventHandler) -> Callable[[], None]:
        """Subscribe to an event pattern.

        Supports glob-style: ``atlas:*``, ``*.confirmed``

        Args:
            event: Event name or pattern.
            handler: Async or sync callable.

        Returns:
            A callable to unsubscribe.
        """

    @abstractmethod
    def clear(self) -> None:
        """Remove all subscribers (for shutdown / testing)."""

    @abstractmethod
    def get_history(self, app_id: str | None = None, limit: int = 100) -> list[dict]:
        """Return recent events, optionally filtered by app_id."""
