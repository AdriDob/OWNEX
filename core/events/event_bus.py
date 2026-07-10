"""Core EventBus — namespace-aware wrapper around CATEYE's EventBus.

This is a thin adapter. The actual implementation lives in
``cores/events/event_bus.py`` and is NOT modified.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from core.interfaces.event_bus import IEventBus

logger = logging.getLogger("orion.core.events")


class CoreEventBus(IEventBus):
    """Namespaced wrapper that delegates to the existing CATEYE EventBus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Any]]] = {}
        self._namespaces: dict[str, str] = {}  # pattern → app_id

    def publish(self, event: str, **data: Any) -> None:
        logger.debug("Event: %s %s", event, data)
        for pattern, handlers in self._handlers.items():
            if self._match(pattern, event):
                for handler in handlers:
                    try:
                        handler(event=event, **data)
                    except Exception:
                        logger.exception("Handler failed for %s", event)

    def subscribe(self, event: str, handler: Callable[..., Any]) -> Callable[[], None]:
        self._handlers.setdefault(event, []).append(handler)

        def unsubscribe() -> None:
            handlers = self._handlers.get(event)
            if handlers and handler in handlers:
                handlers.remove(handler)

        return unsubscribe

    def clear(self) -> None:
        self._handlers.clear()

    def get_history(self, app_id: str | None = None, limit: int = 100) -> list[dict]:
        if not app_id:
            return list(self._recent)[-limit:]
        return [e for e in self._recent if e.get("app_id") == app_id][-limit:]

    # ── Namespace helpers ────────────────────────────────────────

    def app_event(self, app_id: str, event: str) -> str:
        """Qualify an event name with the app namespace.

        Example: ``app_event("atlas", "price:updated")`` → ``atlas:price:updated``
        """
        return f"{app_id}:{event}"

    def subscribe_app(self, app_id: str, handler: Callable[..., Any]) -> Callable[[], None]:
        """Subscribe to all events from a specific app."""
        return self.subscribe(f"{app_id}:*", handler)

    # ── Wildcard matching ────────────────────────────────────────

    @staticmethod
    def _match(pattern: str, event: str) -> bool:
        if pattern == event:
            return True
        if pattern.endswith("*"):
            return event.startswith(pattern[:-1])
        return False

    _recent: list[dict] = []


# ── Singleton ────────────────────────────────────────

_bus: CoreEventBus | None = None


def get_core_event_bus() -> CoreEventBus:
    global _bus
    if _bus is None:
        _bus = CoreEventBus()
    return _bus
