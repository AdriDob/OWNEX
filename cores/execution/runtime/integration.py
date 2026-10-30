from __future__ import annotations

import logging
from typing import Any

from cores.events.types import EventEnvelope

logger = logging.getLogger("ownex.execution.integration")


class ExecutionEventBusBridge:
    """Connects the Execution Runtime to the ORION Platform EventBus.

    Two-way bridge:
    1. ExecutionEventPublisher → CoreEventBus (execution events flow outward)
    2. CoreEventBus → Execution Runtime (external events can influence executions)

    Call ``wire()`` during application startup.
    """

    def __init__(self) -> None:
        self._core_bus: Any = None
        self._legacy_bus: Any = None
        self._unsubscribers: list[Any] = []

    def wire(self) -> None:
        """Connect the execution runtime to the event system."""
        from cores.events.event_bus import get_core_event_bus

        self._core_bus = get_core_event_bus()
        logger.info("[Integration] ExecutionEventBusBridge wired to CoreEventBus")

    def get_publish_fn(self) -> Any:
        """Return a publish function suitable for ExecutionEventPublisher.bind()."""
        if not self._core_bus:
            self.wire()

        def publish_to_core_bus(envelope: EventEnvelope) -> None:
            if self._core_bus:
                self._core_bus.publish(
                    envelope.event_type,
                    **envelope.to_dict(),
                )

        return publish_to_core_bus

    def subscribe_to_execution_events(self, handler: Any) -> None:
        """Subscribe to all execution:prefixed events."""
        if not self._core_bus:
            self.wire()

        def _wrapper(event_type: str, **data: Any) -> None:
            try:
                handler(event_type, data)
            except Exception as exc:
                logger.warning("[Integration] Handler error for %s: %s", event_type, exc)

        unsub = self._core_bus.subscribe("execution:*", _wrapper)
        self._unsubscribers.append(unsub)
        logger.info("[Integration] Subscribed to execution:* events")

    def subscribe_to_execution_node_events(self, handler: Any) -> None:
        if not self._core_bus:
            self.wire()

        def _wrapper(event_type: str, **data: Any) -> None:
            try:
                handler(event_type, data)
            except Exception as exc:
                logger.warning("[Integration] Handler error for %s: %s", event_type, exc)

        unsub = self._core_bus.subscribe("execution:node:*", _wrapper)
        self._unsubscribers.append(unsub)

    def unsubscribe_all(self) -> None:
        for unsub in self._unsubscribers:
            try:
                unsub()
            except Exception as exc:
                logger.warning("[Integration] Unsubscribe error: %s", exc)
        self._unsubscribers.clear()

    @property
    def is_wired(self) -> bool:
        return self._core_bus is not None
