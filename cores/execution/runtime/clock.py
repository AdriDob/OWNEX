from __future__ import annotations

import heapq
import time as _real_time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _TimerEvent:
    fire_at: float
    callback: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    timer_id: str = ""

    def __lt__(self, other: _TimerEvent) -> bool:
        return self.fire_at < other.fire_at


class VirtualClock:
    """Deterministic virtual clock for the Execution Platform.

    *Never* use ``time.sleep()`` inside any runtime code.
    Always use the clock so the Time Machine can replay exactly.

    In **real mode**, ``now()`` returns system time and ``wait()``
    actually sleeps. In **simulation mode**, ``advance()`` jumps the
    clock forward and ``wait()`` returns immediately after scheduling.
    """

    def __init__(self, simulation: bool = False) -> None:
        self._simulation = simulation
        self._virtual_now: float = _real_time.time()
        self._timers: list[_TimerEvent] = []
        self._paused: bool = False

    @property
    def simulation(self) -> bool:
        return self._simulation

    def now(self) -> float:
        if self._simulation:
            return self._virtual_now
        return _real_time.time()

    def wait(self, duration_ms: float) -> None:
        if self._simulation:
            self._virtual_now += duration_ms / 1000.0
            self._process_timers()
        else:
            _real_time.sleep(duration_ms / 1000.0)

    def advance(self, delta_ms: float) -> None:
        if not self._simulation:
            msg = "advance() is only valid in simulation mode"
            raise RuntimeError(msg)
        self._virtual_now += delta_ms / 1000.0
        self._process_timers()

    def schedule(self, delay_ms: float, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        timer_id = f"t_{id(callback)}_{int(self._virtual_now * 1000)}_{len(self._timers)}"
        heapq.heappush(
            self._timers,
            _TimerEvent(
                fire_at=self._virtual_now + delay_ms / 1000.0,
                callback=callback,
                args=args,
                kwargs=kwargs,
                timer_id=timer_id,
            ),
        )
        return timer_id

    def _process_timers(self) -> None:
        while self._timers and self._timers[0].fire_at <= self._virtual_now:
            ev = heapq.heappop(self._timers)
            ev.callback(*ev.args, **ev.kwargs)

    def cancel(self, timer_id: str) -> bool:
        before = len(self._timers)
        self._timers = [t for t in self._timers if t.timer_id != timer_id]
        heapq.heapify(self._timers)
        return len(self._timers) < before

    @property
    def pending_timers(self) -> int:
        return len(self._timers)

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused
