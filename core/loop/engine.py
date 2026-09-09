"""OWNEX Loop Engine — runs loop patterns via Scheduler + EventBus.

The LoopEngine is the runtime for loop-engineering patterns in OWNEX:

  1. Registers a pattern as a Scheduler job
  2. When the job fires, executes the pattern phases
  3. Publishes events at each phase transition
  4. Maintains LoopState (persisted + in-memory)
  5. Supports the OODA loop: Observe → Orient → Decide → Act

Integration:
  - Scheduler → job interval (cadence)
  - EventBus → phase transition events + state updates
  - Health API → loop status / score
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from core.interfaces.event_bus import IEventBus
from core.interfaces.scheduler import IScheduler, JobDefinition
from core.loop.models import (
    CycleState,
    LoopPattern,
    LoopRunResult,
    LoopState,
    Phase,
)

logger = logging.getLogger("orion.core.loop.engine")


class LoopEngine:
    """Runtime engine for executing loop patterns.

    Each pattern gets its own LoopEngine instance that manages
    state transitions, phase execution, and event publishing.
    """

    def __init__(
        self,
        pattern: LoopPattern,
        scheduler: IScheduler | None = None,
        event_bus: IEventBus | None = None,
        state: LoopState | None = None,
    ) -> None:
        self.pattern = pattern
        self._scheduler = scheduler
        self._event_bus = event_bus
        self._state = state or LoopState(pattern_id=pattern.id)
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._running = False

    # ── Properties ─────────────────────────────────────────────────

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def pattern_id(self) -> str:
        return self.pattern.id

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Phase handlers ─────────────────────────────────────────────

    def on(self, phase: Phase | str, handler: Callable[..., Any]) -> None:
        """Register a handler for a specific phase.

        Args:
            phase: Phase name (Phase enum or string)
            handler: Callable that receives (engine, context) when phase fires.
        """
        key = phase if isinstance(phase, str) else phase.value
        self._handlers[key] = handler

    def off(self, phase: Phase | str) -> None:
        """Remove a phase handler."""
        key = phase if isinstance(phase, str) else phase.value
        self._handlers.pop(key, None)

    # ── Lifecycle ─────────────────────────────────────────────────

    def register(self) -> str | None:
        """Register this pattern as a scheduler job.

        Returns:
            job_id if scheduler is available, else None.
        """
        if not self._scheduler:
            logger.warning("No scheduler available for pattern %s", self.pattern.id)
            return None

        # Parse cadence (e.g. "1d" → 86400, "2h" → 7200, "5m" → 300)
        seconds = self._parse_cadence(self.pattern.cadence)

        job = JobDefinition(
            job_id=f"loop:{self.pattern.id}",
            app_id=self.pattern.app_id or "loop",
            handler=self.run,
            trigger="interval",
            seconds=seconds,
            pattern_id=self.pattern.id,
        )
        job_id = self._scheduler.add_job(job)
        logger.info(
            "Registered loop pattern %s (cadence=%s, interval=%ds)",
            self.pattern.id,
            self.pattern.cadence,
            seconds,
        )
        return job_id

    async def run(self, **context: Any) -> LoopRunResult:
        """Execute a single cycle of this loop pattern.

        Iterates through the pattern's phases in order,
        calling registered handlers for each phase.
        """
        start = time.monotonic()
        self._running = True
        self._state.cycle_state = CycleState.RUNNING
        self._publish_event(f"loop:{self.pattern.id}:started", context=context)

        result = LoopRunResult(pattern_id=self.pattern.id, success=True, duration_ms=0)
        errors: list[str] = []

        for phase in self.pattern.phases:
            try:
                await self._execute_phase(phase, context)
                result.phases_completed.append(phase)
                self._publish_event(
                    f"loop:{self.pattern.id}:phase:{phase.value}",
                    phase=phase.value,
                )
            except Exception as exc:
                msg = f"Phase {phase.value}: {exc}"
                errors.append(msg)
                logger.exception("Loop %s phase %s failed", self.pattern.id, phase.value)
                self._publish_event(
                    f"loop:{self.pattern.id}:phase_error",
                    phase=phase.value,
                    error=str(exc),
                )
                # On L1 (report-only), abort on first error
                if self.pattern.week_one_mode.value == "L1":
                    break

        # Update state
        elapsed = (time.monotonic() - start) * 1000
        result.success = (
            len(errors) == 0 if self.pattern.week_one_mode.value == "L1" else len(errors) < len(self.pattern.phases)
        )
        result.duration_ms = elapsed
        result.errors = errors
        result.state = self._state

        self._state.last_run = time.time()
        self._state.cycle_state = CycleState.COMPLETED if result.success else CycleState.ERROR
        self._running = False

        self._publish_event(
            f"loop:{self.pattern.id}:completed" if result.success else f"loop:{self.pattern.id}:failed",
            duration_ms=elapsed,
            errors=errors,
        )

        return result

    # ── Internal ───────────────────────────────────────────────────

    async def _execute_phase(self, phase: Phase, context: dict[str, Any]) -> None:
        """Execute a single phase."""
        handler = self._handlers.get(phase.value)
        if handler:
            result = handler(self, context)
            if hasattr(result, "__await__"):
                await result

    def _publish_event(self, event: str, **data: Any) -> None:
        """Publish an event if EventBus is available."""
        if self._event_bus:
            self._event_bus.publish(event, **data)

    @staticmethod
    def _parse_cadence(cadence: str) -> int:
        """Parse a cadence string into seconds.

        Examples:
            "5m" → 300
            "2h" → 7200
            "1d" → 86400
            "30m" → 1800
        """
        cadence = cadence.strip().lower()
        if cadence.endswith("d"):
            return int(cadence[:-1]) * 86400
        if cadence.endswith("h"):
            return int(cadence[:-1]) * 3600
        if cadence.endswith("m"):
            return int(cadence[:-1]) * 60
        if cadence.endswith("s"):
            return int(cadence[:-1])
        return int(cadence) if cadence.isdigit() else 3600

    # ── Health / Status ────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Return current status for the health API."""
        return {
            "pattern_id": self.pattern.id,
            "name": self.pattern.name,
            "goal": self.pattern.goal,
            "cadence": self.pattern.cadence,
            "cycle_state": self._state.cycle_state.value,
            "is_running": self._running,
            "last_run": self._state.last_run,
            "phases": [p.value for p in self.pattern.phases],
            "human_gates": self.pattern.human_gates,
            "week_one_mode": self.pattern.week_one_mode.value,
        }

    def score(self) -> int:
        """Compute a Loop Ready score (0-100) for this pattern.

        Mirrors loop-audit's scoring methodology:
          - Has skills registered? (25 pts)
          - Has phase handlers? (25 pts)
          - Has scheduler? (25 pts)
          - Has state file? (25 pts)
        """
        s = 0
        if self._handlers:
            coverage = len(self._handlers) / max(len(self.pattern.phases), 1)
            s += int(25 * min(coverage, 1.0))
        if len(self.pattern.skills) > 0:
            s += 25
        if self._scheduler:
            s += 25
        if self._state.last_run > 0:
            s += 15
        if self._state.cycle_state not in (CycleState.IDLE, CycleState.ERROR):
            s += 10
        return min(s, 100)
