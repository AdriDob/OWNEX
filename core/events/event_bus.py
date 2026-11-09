"""Core EventBus — compatibility facade over the canonical cores EventBus.

ADR-0003 / OWNEX V15: there is now a single event bus
(``cores.events.event_bus.EventBus``) owning delivery, priority
classification, async dispatch and SQLite persistence. This module preserves
the historical ``CoreEventBus`` API — ``app:event`` namespaces, wildcard
patterns, ``app_id``-filtered history and unsubscribe callables — by
delegating to that canonical bus, so existing consumers keep working while
events can no longer be lost between the two trees.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from core.interfaces.event_bus import IEventBus

logger = logging.getLogger("orion.core.events")

EventHandler = Callable[..., Any]


class CoreEventBus(IEventBus):
    """Namespace/wildcard facade over the canonical cores EventBus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._lock = threading.Lock()
        self._bus: Any = None
        self._registered = False

    # ── Canonical bus access ─────────────────────────────────────

    def _canonical(self) -> Any:
        if self._bus is None:
            from cores.events.event_bus import get_event_bus

            self._bus = get_event_bus()
        return self._bus

    def _ensure_dispatcher(self) -> None:
        if self._registered:
            return
        self._canonical().subscribe("*", self._dispatch)
        self._registered = True

    # ── IEventBus ────────────────────────────────────────────────

    def publish(self, event: str, **data: Any) -> None:
        logger.debug("Event: %s %s", event, data)
        self._canonical().publish(event, **data)

    def subscribe(self, event: str, handler: EventHandler) -> Callable[[], None]:
        self._ensure_dispatcher()
        with self._lock:
            self._handlers.setdefault(event, []).append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._handlers.get(event)
                if handlers and handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()

    def get_history(self, app_id: str | None = None, limit: int = 100) -> list[dict]:
        records = self._canonical().get_history(limit=max(limit * 4, 200))
        out: list[dict] = []
        for rec in records:
            event = str(rec.get("type", ""))
            prefix = event.split(":")[0] if ":" in event else "core"
            if app_id and prefix != app_id:
                continue
            out.append(
                {
                    "event": event,
                    "data": rec.get("payload") or {},
                    "timestamp": float(rec.get("timestamp", 0.0) or 0.0),
                    "app_id": prefix,
                }
            )
        return out[-limit:]

    # ── Namespace helpers ────────────────────────────────────────

    @staticmethod
    def app_event(app_id: str, event: str) -> str:
        return f"{app_id}:{event}"

    def subscribe_app(self, app_id: str, handler: EventHandler) -> Callable[[], None]:
        return self.subscribe(f"{app_id}:*", handler)

    # ── Wildcard matching (local fan-out from canonical "*") ─────

    @staticmethod
    def _match(pattern: str, event: str) -> bool:
        if pattern == event:
            return True
        if pattern.endswith("*"):
            return event.startswith(pattern[:-1])
        return False

    def _dispatch(
        self,
        event_type: str | None = None,
        priority: str | None = None,
        _priority: str | None = None,
        **payload: Any,
    ) -> None:
        event = str(event_type)
        with self._lock:
            snapshot = list(self._handlers.items())
        for pattern, handlers in snapshot:
            if not self._match(pattern, event):
                continue
            for handler in handlers:
                try:
                    handler(event=event, **payload)
                except Exception:
                    logger.exception("Handler failed for %s", event)

    # ── Config compat (persistence/bridge owned by canonical bus) ─

    def disable_persistence(self) -> None:
        pass

    def disable_bridge(self) -> None:
        pass

    def enable_bridge(self) -> None:
        pass


# ── Singleton ────────────────────────────────────────────────────

_bus: CoreEventBus | None = None


def get_core_event_bus() -> CoreEventBus:
    global _bus
    if _bus is None:
        _bus = CoreEventBus()
    return _bus


def get_event_bus() -> Any:
    """Alias kept for legacy importers of this module (e.g. universal_connector).

    Returns the canonical cores EventBus, matching the
    ``cores.events.event_bus.get_event_bus`` contract.
    """
    from cores.events.event_bus import get_event_bus as _canonical

    return _canonical()
