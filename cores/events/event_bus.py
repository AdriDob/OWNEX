"""Async-safe event bus — publish/subscribe for system-wide events.

Every event passes through the priority engine before being dispatched.
Events are classified: critical, high, medium, low, or ignore.
History is persisted to SQLite via EventBusEntry model.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.events")

EventHandler = Callable[..., Any]


class EventPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    IGNORE = "ignore"


EVENT_PRIORITY_MAP: dict[str, str] = {
    "system:error": "critical",
    "system:degraded": "critical",
    "system:alert": "critical",
    "recovery:started": "critical",
    "recovery:failed": "critical",
    "anomaly_detected": "critical",
    "failure_predicted": "critical",
    "opportunity:found": "high",
    "quick_win:detected": "high",
    "contract:warning": "high",
    "system:ready": "medium",
    "recovery:success": "medium",
    "health_score_updated": "medium",
    "auto_optimization_applied": "medium",
    "report:generated": "medium",
    "opportunity:updated": "medium",
    "assistant:recommendation": "medium",
    "sync:completed": "low",
    "discovery:completed": "low",
    "system:boot:complete": "low",
    "system:boot:starting": "low",
}


def classify_event(event_type: str) -> str:
    return EVENT_PRIORITY_MAP.get(event_type, "medium")


def _get_session():
    from database.db import SessionLocal

    return SessionLocal()


def _persist_event(event_type: str, priority: str, payload: dict[str, Any]) -> None:
    try:
        session = _get_session()
        try:
            from database.models import EventBusEntry

            ts = str(time.time())
            pj = {}
            for k, v in payload.items():
                try:
                    json.dumps(v)
                    pj[k] = v
                except (TypeError, ValueError):
                    pj[k] = str(v)
            entry = EventBusEntry(
                event_type=event_type,
                priority=priority,
                payload_json=json.dumps(pj),
                timestamp=ts,
            )
            session.add(entry)
            session.commit()
        except Exception as exc:
            logger.warning("Failed to persist event %s: %s", event_type, exc)
            session.rollback()
        finally:
            session.close()
    except Exception as exc:
        logger.warning("Failed to open DB session for event: %s", exc)


class EventBus:
    """Lightweight in-process event bus with SQLite persistence.

    Every publish() call:
      1. Classifies the event via priority map
      2. Records in-memory + persists to SQLite
      3. Routes through priority engine for ranking
      4. Dispatches to sync + async handlers
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handlers: dict[str, list[EventHandler]] = {}
        self._async_handlers: dict[str, list[EventHandler]] = {}
        self._history: list[dict[str, Any]] = []
        self._max_history = 500

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def subscribe_async(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            if event_type not in self._async_handlers:
                self._async_handlers[event_type] = []
            self._async_handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]
            if event_type in self._async_handlers:
                self._async_handlers[event_type] = [h for h in self._async_handlers[event_type] if h != handler]

    def publish(self, event_type: str, **payload: Any) -> None:
        """Publish an event. Classifies -> persists -> routes -> dispatches."""
        priority = classify_event(event_type)

        payload["_priority"] = priority
        with self._lock:
            _record_event(self._history, self._max_history, event_type, priority, payload)

        _persist_event(event_type, priority, payload)

        if priority == "ignore":
            logger.debug("Ignored event: %s", event_type)
            return

        try:
            from cores.intelligence.priority_engine import get_priority_engine

            engine = get_priority_engine()
            if event_type.startswith("opportunity"):
                engine.ingest_opportunity({"source": "opportunity", **payload})
            elif event_type.startswith("quick_win"):
                engine.ingest_quick_win({"source": "quick_win", **payload})
            elif event_type in ("system:error", "system:degraded", "system:ready"):
                engine.ingest_system_alert(
                    {
                        "source": "alert",
                        "severity": priority,
                        "title": event_type,
                        "message": payload.get("message", str(payload)),
                        **payload,
                    }
                )
        except Exception as exc:
            logger.debug("Priority routing skipped: %s", exc)

        with self._lock:
            handlers = list(self._handlers.get(event_type, [])) + list(self._handlers.get("*", []))
        for handler in handlers:
            try:
                handler(event_type=event_type, priority=priority, **payload)
            except Exception as exc:
                logger.warning("Event handler error on %s: %s", event_type, exc)

        with self._lock:
            async_handlers = list(self._async_handlers.get(event_type, [])) + list(self._async_handlers.get("*", []))
        if async_handlers:
            loop = _get_loop()
            if loop is None or loop.is_closed():
                logger.debug("No running event loop for async handlers of %s", event_type)
            else:
                for handler in async_handlers:
                    try:
                        fut = asyncio.run_coroutine_threadsafe(
                            handler(event_type=event_type, priority=priority, **payload),
                            loop,
                        )
                        fut.add_done_callback(
                            lambda f: (
                                logger.warning("Async handler error on %s: %s", event_type, f.exception())
                                if f.exception()
                                else None
                            )
                        )
                    except Exception as exc:
                        logger.warning("Async event handler error on %s: %s", event_type, exc)

    def get_history(self, event_type: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent events, combining in-memory cache with persisted history."""
        db_events: list[dict[str, Any]] = []
        try:
            session = _get_session()
            try:
                from database.models import EventBusEntry

                q = session.query(EventBusEntry)
                if event_type:
                    q = q.filter(EventBusEntry.event_type == event_type)
                q = q.order_by(EventBusEntry.id.desc()).limit(limit)
                for row in q:
                    try:
                        pj = json.loads(row.payload_json or "{}")
                    except (json.JSONDecodeError, TypeError):
                        pj = {}
                    db_events.append(
                        {
                            "type": row.event_type,
                            "priority": row.priority,
                            "timestamp": float(row.timestamp) if row.timestamp else 0.0,
                            "payload": pj,
                            "_persisted": True,
                        }
                    )
            except Exception as exc:
                logger.debug("DB history query failed: %s", exc)
            finally:
                session.close()
        except Exception as exc:
            logger.debug("Failed to open DB session for history: %s", exc)

        with self._lock:
            mem_events = list(self._history)
            if event_type:
                mem_events = [e for e in mem_events if e["type"] == event_type]

        seen_ids: set[str] = set()
        combined: list[dict[str, Any]] = []

        for e in db_events:
            ts_key = f"{e['type']}:{e['timestamp']}"
            if ts_key not in seen_ids:
                seen_ids.add(ts_key)
                combined.append(e)

        for e in reversed(mem_events):
            ts_key = f"{e['type']}:{e['timestamp']}"
            if ts_key not in seen_ids:
                seen_ids.add(ts_key)
                combined.append(e)

        return combined[-limit:]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()
        try:
            session = _get_session()
            try:
                from database.models import EventBusEntry

                session.query(EventBusEntry).delete()
                session.commit()
            except Exception as exc:
                logger.warning("Failed to clear persisted history: %s", exc)
                session.rollback()
            finally:
                session.close()
        except Exception as exc:
            logger.debug("Failed to open DB session for clear: %s", exc)

    def handler_count(self, event_type: str | None = None) -> int:
        with self._lock:
            if event_type:
                return len(self._handlers.get(event_type, [])) + len(self._async_handlers.get(event_type, []))
            return sum(len(v) for v in self._handlers.values()) + sum(len(v) for v in self._async_handlers.values())


def _record_event(
    history: list[dict[str, Any]], max_history: int, event_type: str, priority: str, payload: dict[str, Any]
) -> None:
    history.append(
        {
            "type": event_type,
            "priority": priority,
            "timestamp": time.time(),
            "payload": payload,
        }
    )
    if len(history) > max_history:
        history[:] = history[-max_history:]


def _get_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


_BUS: EventBus | None = None


def get_event_bus() -> EventBus:
    global _BUS
    if _BUS is None:
        _BUS = EventBus()
        logger.info("Event bus initialized (persistent)")
    return _BUS


get_core_event_bus = get_event_bus
