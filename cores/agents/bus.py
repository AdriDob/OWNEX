"""IEventBus interface + LocalEventBus implementation.

Agents communicate exclusively through this bus.
Never call agents directly.
Events are immutable, serializable, and fully traceable.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.bus")

EventHandler = Callable[[AgentEvent], Any]
LoggingHook = Callable[[AgentEvent], None]


class IEventBus(ABC):
    """Interface for the event bus. Swap implementations without affecting agents."""

    @abstractmethod
    def publish(self, event: AgentEvent) -> None:
        """Publish an event to all subscribed handlers."""

    @abstractmethod
    def subscribe(self, event_type: EventType | str, handler: EventHandler) -> None:
        """Subscribe to a specific event type."""

    @abstractmethod
    def subscribe_agent(self, agent_id: AgentId, handler: EventHandler) -> None:
        """Subscribe to all events targeted at this agent."""

    @abstractmethod
    def unsubscribe(self, event_type: EventType | str, handler: EventHandler) -> None:
        """Remove a specific subscription."""

    @abstractmethod
    def unsubscribe_agent(self, agent_id: AgentId, handler: EventHandler) -> None:
        """Remove a specific agent subscription."""

    @abstractmethod
    def get_history(self, event_type: str | None = None, limit: int = 50) -> list[AgentEvent]:
        """Retrieve recent event history, optionally filtered by type."""

    @abstractmethod
    def replay(self, correlation_id: str) -> list[AgentEvent]:
        """Replay all events matching a correlation_id for full traceability."""

    @abstractmethod
    def clear_history(self) -> None:
        """Clear all stored history."""

    @abstractmethod
    def set_logging_hook(self, hook: LoggingHook | None) -> None:
        """Attach a custom logging hook invoked on every publish."""


class LocalEventBus(IEventBus):
    """In-process event bus for single-node execution.

    Thread-safe. Supports sync and async handlers.
    Events are immutable (frozen dataclasses).
    Full traceability via replay(correlation_id).
    No external dependencies.
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._lock = threading.Lock()
        self._handlers: dict[str, list[EventHandler]] = {}
        self._agent_handlers: dict[str, list[EventHandler]] = {}
        self._history: list[AgentEvent] = []
        self._max_history = max_history
        self._logging_hook: LoggingHook | None = None

    def publish(self, event: AgentEvent) -> None:
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history[:] = self._history[-self._max_history :]

        # Logging hook
        if self._logging_hook:
            try:
                self._logging_hook(event)
            except Exception as exc:
                logger.warning("[EVENTS] Logging hook error: %s", exc)

        # Structured log
        logger.info(
            "[EVENTS] %s -> %s: %s (corr=%s, pri=%d)",
            event.source,
            event.target or "*",
            event.event_type,
            event.correlation_id[:8],
            event.priority,
        )

        # Dispatch to type-specific handlers
        handlers: list[EventHandler] = []
        event_key = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        with self._lock:
            handlers.extend(self._handlers.get(event_key, []))
            handlers.extend(self._handlers.get("*", []))
            target_key = event.target.value if isinstance(event.target, AgentId) else event.target
            if target_key and target_key in self._agent_handlers:
                handlers.extend(self._agent_handlers[target_key])

        for handler in handlers:
            try:
                result = handler(event)
                if inspect.iscoroutine(result):
                    # Fire-and-forget async handler in background
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None
                    if loop and loop.is_running():
                        task = asyncio.ensure_future(result)
                        task.add_done_callback(
                            lambda t: (
                                logger.warning("[EVENTS] Handler error for %s: %s", event.event_type, t.exception())
                                if t.exception()
                                else None
                            )
                        )
                    else:
                        import threading

                        threading.Thread(target=lambda r=result: asyncio.run(r), daemon=True).start()
            except Exception as exc:
                logger.warning("[EVENTS] Handler error for %s: %s", event.event_type, exc)

    def subscribe(self, event_type: EventType | str, handler: EventHandler) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        with self._lock:
            if key not in self._handlers:
                self._handlers[key] = []
            self._handlers[key].append(handler)

    def subscribe_agent(self, agent_id: AgentId, handler: EventHandler) -> None:
        with self._lock:
            key = agent_id.value
            if key not in self._agent_handlers:
                self._agent_handlers[key] = []
            self._agent_handlers[key].append(handler)

    def unsubscribe(self, event_type: EventType | str, handler: EventHandler) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        with self._lock:
            if key in self._handlers:
                self._handlers[key] = [h for h in self._handlers[key] if h is not handler]

    def unsubscribe_agent(self, agent_id: AgentId, handler: EventHandler) -> None:
        with self._lock:
            key = agent_id.value
            if key in self._agent_handlers:
                self._agent_handlers[key] = [h for h in self._agent_handlers[key] if h is not handler]

    def get_history(self, event_type: str | None = None, limit: int = 50) -> list[AgentEvent]:
        with self._lock:
            if event_type:
                filtered = [e for e in self._history if e.event_type == event_type]
                return filtered[-limit:]
            return self._history[-limit:]

    def replay(self, correlation_id: str) -> list[AgentEvent]:
        """Replay all events matching a correlation_id for full traceability."""
        with self._lock:
            return [e for e in self._history if e.correlation_id == correlation_id]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def set_logging_hook(self, hook: LoggingHook | None) -> None:
        self._logging_hook = hook


_BUS: IEventBus | None = None


def get_agent_bus() -> IEventBus:
    """Get the singleton agent event bus."""
    global _BUS
    if _BUS is None:
        _BUS = LocalEventBus()
        logger.info("[EVENTS] Agent event bus initialized")
    return _BUS


def reset_agent_bus() -> None:
    """Reset the bus (for testing)."""
    global _BUS
    _BUS = None


def bridge_agent_bus_to_eventbus() -> None:
    """Forward AgentBus pipeline events to the system-wide EventBus."""
    try:
        from cores.events.event_bus import get_event_bus

        event_bus = get_event_bus()
        agent_bus = get_agent_bus()

        def _forward(event):
            try:
                etype = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
                event_bus.publish(
                    f"agent:{etype}",
                    source=str(event.source) if event.source else None,
                    target=str(event.target) if event.target else None,
                    correlation_id=event.correlation_id,
                    priority=event.priority,
                    payload=event.payload if hasattr(event, "payload") else {},
                )
            except Exception:
                logger.debug("Failed to forward agent event to EventBus")

        agent_bus.subscribe("*", _forward)
        logger.info("[EVENTS] AgentBus → EventBus bridge started")
    except Exception:
        logger.warning("[EVENTS] Failed to start AgentBus → EventBus bridge")


def bridge_eventbus_to_agent_bus() -> None:
    """Forward scheduler pipeline events from EventBus to AgentBus.

    The scheduler (api/scheduler.py) publishes pipeline lifecycle events
    (pipeline.start, pipeline.stage_completed, pipeline.failed, pipeline.cancelled)
    to the system EventBus. The CoordinatorAgent listens on the AgentBus.
    This bridge makes those events reach the coordinator so it can track
    pipeline state in its DB-backed state machine.
    """
    try:
        from cores.events.event_bus import get_event_bus

        event_bus = get_event_bus()
        agent_bus = get_agent_bus()

        pipeline_events = {
            "pipeline.start",
            "pipeline.stage_completed",
            "pipeline.failed",
            "pipeline.cancelled",
        }

        def _on_event(event_type: str, **data: Any) -> None:
            if event_type not in pipeline_events:
                return
            try:
                from cores.agents.types import EventType as AgentEventType

                etype = AgentEventType(event_type)
            except (ValueError, ImportError):
                etype = event_type

            from cores.agents.types import AgentId

            source_id = data.get("source", "coordinator")
            try:
                source = AgentId(str(source_id))
            except (ValueError, ImportError):
                source = str(source_id)

            target_id = data.get("target", "coordinator")
            try:
                target = AgentId(str(target_id))
            except (ValueError, ImportError):
                target = str(target_id)

            correlation_id = data.get("correlation_id", "")
            payload = data.get("payload", {})

            try:
                agent_event = AgentEvent(
                    event_type=etype,
                    source=source,
                    target=target,
                    correlation_id=correlation_id,
                    priority=5,
                    payload=payload,
                )
                agent_bus.publish(agent_event)
                logger.debug(
                    "[BRIDGE] EventBus → AgentBus: %s (corr=%s)",
                    event_type,
                    correlation_id[:8],
                )
            except Exception:
                logger.debug("Failed to forward EventBus event to AgentBus: %s", event_type)

        event_bus.subscribe("pipeline.start", _on_event)
        event_bus.subscribe("pipeline.stage_completed", _on_event)
        event_bus.subscribe("pipeline.failed", _on_event)
        event_bus.subscribe("pipeline.cancelled", _on_event)
        logger.info("[EVENTS] EventBus → AgentBus bridge started (4 pipeline events)")
    except Exception:
        logger.warning("[EVENTS] Failed to start EventBus → AgentBus bridge")
