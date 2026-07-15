from __future__ import annotations

import logging
from collections.abc import Callable

from core.execution.runtime.clock import VirtualClock

logger = logging.getLogger("cateye.execution.timeout")


class TimeoutEngine:
    """Manages timeouts for nodes, workflows, approvals, and resources.

    All timeouts use the VirtualClock so they work in both
    real and simulation modes.
    """

    def __init__(self, clock: VirtualClock) -> None:
        self.clock = clock
        self._timers: dict[str, str] = {}

    def start_node_timeout(
        self,
        execution_id: str,
        node_id: str,
        duration_ms: int,
        on_timeout: Callable[[], None],
    ) -> str:
        timer_id = self.clock.schedule(duration_ms, on_timeout)
        self._timers[f"node:{execution_id}:{node_id}"] = timer_id
        return timer_id

    def start_workflow_timeout(
        self,
        execution_id: str,
        duration_ms: int,
        on_timeout: Callable[[], None],
    ) -> str:
        timer_id = self.clock.schedule(duration_ms, on_timeout)
        self._timers[f"workflow:{execution_id}"] = timer_id
        return timer_id

    def start_approval_timeout(
        self,
        approval_id: str,
        duration_ms: int,
        on_timeout: Callable[[], None],
    ) -> str:
        timer_id = self.clock.schedule(duration_ms, on_timeout)
        self._timers[f"approval:{approval_id}"] = timer_id
        return timer_id

    def start_resource_timeout(
        self,
        resource_name: str,
        duration_ms: int,
        on_timeout: Callable[[], None],
    ) -> str:
        timer_id = self.clock.schedule(duration_ms, on_timeout)
        self._timers[f"resource:{resource_name}"] = timer_id
        return timer_id

    def cancel_timeout(self, key: str) -> bool:
        timer_id = self._timers.pop(key, None)
        if timer_id:
            return self.clock.cancel(timer_id)
        return False

    def cancel_node_timeout(self, execution_id: str, node_id: str) -> bool:
        return self.cancel_timeout(f"node:{execution_id}:{node_id}")

    def cancel_workflow_timeout(self, execution_id: str) -> bool:
        return self.cancel_timeout(f"workflow:{execution_id}")

    def cancel_approval_timeout(self, approval_id: str) -> bool:
        return self.cancel_timeout(f"approval:{approval_id}")

    def cancel_resource_timeout(self, resource_name: str) -> bool:
        return self.cancel_timeout(f"resource:{resource_name}")

    @property
    def active_timeouts(self) -> int:
        return len(self._timers)
