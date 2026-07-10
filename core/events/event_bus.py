"""Core EventBus — namespace-aware event bus with SQLite persistence.

Bridges events to CATEYE's legacy EventBus so app events reach
legacy subscribers.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from core.interfaces.event_bus import IEventBus

logger = logging.getLogger("orion.core.events")


class CoreEventBus(IEventBus):
    """Namespaced event bus with persistence and legacy bridge."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Any]]] = {}
        self._namespaces: dict[str, str] = {}
        self._persist = True
        self._bridge = True

    def publish(self, event: str, **data: Any) -> None:
        logger.debug("Event: %s %s", event, data)

        # 1. Notificar handlers locales
        for pattern, handlers in self._handlers.items():
            if self._match(pattern, event):
                for handler in handlers:
                    try:
                        handler(event=event, **data)
                    except Exception:
                        logger.exception("Handler failed for %s", event)

        # 2. Registrar en historial en memoria
        self._recent.append({
            "event": event,
            "data": data,
            "timestamp": time.time(),
            "app_id": event.split(":")[0] if ":" in event else "core",
        })
        if len(self._recent) > 1000:
            self._recent.pop(0)

        # 3. Persistir a SQLite
        if self._persist:
            self._persist_event(event, data)

        # 4. Bridge al legacy EventBus de CATEYE
        if self._bridge:
            self._bridge_to_legacy(event, **data)

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
        recent = list(self._recent)
        if app_id:
            recent = [e for e in recent if e.get("app_id") == app_id]
        return recent[-limit:]

    # ── Namespace helpers ────────────────────────────────────────

    def app_event(self, app_id: str, event: str) -> str:
        return f"{app_id}:{event}"

    def subscribe_app(self, app_id: str, handler: Callable[..., Any]) -> Callable[[], None]:
        return self.subscribe(f"{app_id}:*", handler)

    # ── Wildcard matching ────────────────────────────────────────

    @staticmethod
    def _match(pattern: str, event: str) -> bool:
        if pattern == event:
            return True
        if pattern.endswith("*"):
            return event.startswith(pattern[:-1])
        return False

    # ── Persistence ──────────────────────────────────────────────

    def _persist_event(self, event: str, data: dict) -> None:
        try:
            from sqlalchemy import Column, Float, Integer, String, Text
            from sqlalchemy.orm import declarative_base

            from core.database.manager import get_db_manager

            dbm = get_db_manager()
            dbm.register("orion_core", "orion_core.db")
            _base = declarative_base()

            class EventRecord(_base):
                __tablename__ = "core_event_log"
                id = Column(Integer, primary_key=True)
                event = Column(String(128), nullable=False, index=True)
                app_id = Column(String(32), nullable=False, index=True)
                payload = Column(Text, default="")
                timestamp = Column(Float, default=time.time)

            _base.metadata.create_all(dbm.get_engine("orion_core"))
            session = dbm.get_session("orion_core")
            try:
                record = EventRecord(
                    event=event,
                    app_id=event.split(":")[0] if ":" in event else "core",
                    payload=json.dumps({k: str(v) for k, v in data.items()}),
                    timestamp=time.time(),
                )
                session.add(record)
                session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()
        except Exception as exc:
            logger.warning("Event persistence failed: %s", exc)

    # ── Legacy bridge ────────────────────────────────────────────

    @staticmethod
    def _bridge_to_legacy(event: str, **data: Any) -> None:
        try:
            from cores.events.event_bus import get_event_bus
            bus = get_event_bus()
            bus.publish(event, **data)
        except Exception as exc:
            logger.debug("Legacy bridge skipped: %s", exc)

    # ── Config ───────────────────────────────────────────────────

    def disable_persistence(self) -> None:
        self._persist = False

    def disable_bridge(self) -> None:
        self._bridge = False

    _recent: list[dict] = []


# ── Singleton ────────────────────────────────────────

_bus: CoreEventBus | None = None


def get_core_event_bus() -> CoreEventBus:
    global _bus
    if _bus is None:
        _bus = CoreEventBus()
    return _bus
