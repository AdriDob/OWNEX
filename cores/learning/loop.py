"""Learning loop — continuous improvement cycle tying all learning components together."""

from __future__ import annotations

import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock, Thread

from cores.learning.contrastive import train_contrastive
from cores.learning.distillation import train_distilled_model
from cores.learning.evolution import evolve_prompts


@dataclass(slots=True)
class LearningCycleResult:
    """Result of one learning cycle."""

    cycle_id: str
    timestamp: datetime
    contrastive_training: dict
    prompt_evolution: dict
    distillation: dict
    stats: dict
    duration_seconds: float


class LearningLoop:
    """
    Continuous learning loop that runs in the background.

    Cycle:
    1. Collect recent engagements
    2. Contrastive learning on success/failure pairs
    3. Prompt evolution on best/worst prompts
    4. Distill new student models if enough data
    4. Update agent prompts with best evolved versions
    5. Update contrastive learner
    6. Log cycle results
    """

    def __init__(
        self,
        cycle_interval_seconds: int = 300,  # 5 minutes
        min_engagements_per_cycle: int = 50,
        max_engagements_per_cycle: int = 500,
    ):
        self.cycle_interval = timedelta(seconds=cycle_interval_seconds)
        self.min_engagements = min_engagements_per_cycle
        self.max_engagements = max_engagements_per_cycle

        self._running = False
        self._thread: Thread | None = None
        self._lock = Lock()
        self._cycle_history: deque = deque(maxlen=100)
        self._last_cycle: datetime | None = None
        self._next_cycle: datetime | None = None

        # Component references (lazy import)
        self._engagement_store = None
        self._contrastive_learner = None
        self._evolution_engine = None
        self._distillation_pipeline = None

        # Callbacks
        self._prompt_update_callbacks: list[Callable] = []

    def _get_components(self) -> None:
        """Lazy import of learning components."""
        if self._engagement_store is None:
            from cores.learning.engagements import get_learning_stats as _engagement_store

            self._engagement_store = _engagement_store
        if self._contrastive_learner is None:
            from cores.learning.contrastive import _contrastive_learner

            self._contrastive_learner = _contrastive_learner
        if self._evolution_engine is None:
            from cores.learning.evolution import _evolution_engine

            self._evolution_engine = _evolution_engine
        if self._distillation_pipeline is None:
            from cores.learning.distillation import _distillation_pipeline

            self._distillation_pipeline = _distillation_pipeline

    def register_prompt_update_callback(self, callback: Callable[[str, str], None]) -> None:
        """Register callback when best prompt is updated.

        callback(agent_id: str, new_prompt: str)
        """
        self._prompt_update_callbacks.append(callback)

    def start(self) -> None:
        """Start the learning loop in background thread."""
        if self._running:
            return

        self._running = True
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._next_cycle = datetime.utcnow()
        print(f"[LEARNING] Loop started, first cycle at {self._next_cycle}")

    def stop(self) -> None:
        """Stop the learning loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        print("[LEARNING] Loop stopped")

    def _run_loop(self) -> None:
        """Main learning loop."""
        while self._running:
            try:
                now = datetime.utcnow()

                # Check if it's time for next cycle
                if self._next_cycle and now < self._next_cycle:
                    sleep_seconds = (self._next_cycle - now).total_seconds()
                    time.sleep(min(sleep_seconds, 10))
                    continue

                # Run learning cycle
                result = self._run_cycle()

                with self._lock:
                    self._cycle_history.append(result)
                    self._last_cycle = datetime.utcnow()
                    self._next_cycle = self._last_cycle + self.cycle_interval

                print(f"[LEARNING] Cycle {result.cycle_id} completed in {result.duration_seconds:.1f}s")
                print(f"  Contrastive: {result.contrastive_training}")
                print(f"  Evolution: {result.prompt_evolution}")
                print(f"  Distillation: {result.distillation}")

            except Exception as e:
                print(f"[LEARNING] Cycle error: {e}")
                time.sleep(30)  # Back off on error

    def _run_cycle(self) -> LearningCycleResult:
        """Run one complete learning cycle."""
        start_time = time.time()
        cycle_id = f"cycle_{uuid.uuid4().hex[:8]}"

        # 1. Get recent engagements
        from cores.learning.engagements import get_learning_stats

        stats = get_learning_stats()

        if stats["total_engagements"] < self.min_engagements:
            return LearningCycleResult(
                cycle_id=cycle_id,
                timestamp=datetime.utcnow(),
                contrastive_training={"skipped": "insufficient_data"},
                prompt_evolution={"skipped": "insufficient_data"},
                distillation={"skipped": "insufficient_data"},
                stats=stats,
                duration_seconds=time.time() - start_time,
            )

        # Get recent engagements for this cycle
        # (In production, would query time-windowed)

        # 2. Contrastive Learning
        contrastive_result = self._run_contrastive_training()

        # 3. Prompt Evolution
        evolution_result = self._run_prompt_evolution()

        # 4. Distillation (if enough data)
        distillation_result = self._run_distillation()

        # 5. Update callbacks with best prompt
        self._propagate_best_prompts()

        duration = time.time() - start_time

        return LearningCycleResult(
            cycle_id=cycle_id,
            timestamp=datetime.utcnow(),
            contrastive_training=contrastive_result,
            prompt_evolution=evolution_result,
            distillation=distillation_result,
            stats=self._get_aggregate_stats(),
            duration_seconds=duration,
        )

    def _run_contrastive_training(self) -> dict:
        """Run contrastive learning on success/failure pairs."""
        try:
            # Get recent engagements and create pairs
            # In production, would query engagement store for success/failure pairs
            result = train_contrastive(batch_size=32)
            return {"status": "completed", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_prompt_evolution(self) -> dict:
        """Run one generation of prompt evolution."""
        try:
            # Get test cases from recent successful engagements
            test_cases = self._get_evolution_test_cases()

            if not test_cases:
                return {"skipped": "no_test_cases"}

            result = evolve_prompts(test_cases)
            return {"status": "completed", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_distillation(self) -> dict:
        """Run model distillation if enough samples."""
        try:
            from cores.learning.distillation import get_distillation_stats

            stats = get_distillation_stats()

            if stats["total_samples"] >= 100:
                # Train a new distilled model
                result = train_distilled_model(
                    model_name=f"student_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    architecture="linear",
                )
                return {"status": "completed", "result": result}
            else:
                return {"skipped": f"only {stats['total_samples']} samples, need 100"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_evolution_test_cases(self) -> list[dict]:
        """Get test cases for prompt evolution from recent engagements."""
        # In production, would query engagement store
        # Return mock test cases for now
        return [
            {"input": {"target": "example.com", "action": "recon"}, "expected": "subdomains found"},
            {"input": {"target": "api.example.com", "action": "fuzz"}, "expected": "vulns found"},
        ]

    def _propagate_best_prompts(self) -> None:
        """Propagate best evolved prompts to registered callbacks."""
        try:
            from cores.learning.evolution import get_best_prompt

            best_prompt = get_best_prompt()

            if best_prompt:
                for callback in self._prompt_update_callbacks:
                    try:
                        callback("global_best", best_prompt)
                    except Exception as e:
                        print(f"[LEARNING] Prompt callback error: {e}")
        except Exception:
            pass

    def _get_aggregate_stats(self) -> dict:
        """Get aggregate learning stats."""
        from cores.learning import get_learning_stats
        from cores.learning.contrastive import get_contrastive_model_state
        from cores.learning.distillation import get_distillation_stats
        from cores.learning.evolution import get_evolution_stats

        return {
            "engagements": get_learning_stats(),
            "contrastive": get_contrastive_model_state(),
            "evolution": get_evolution_stats(),
            "distillation": get_distillation_stats(),
        }

    def force_cycle(self) -> LearningCycleResult:
        """Force an immediate learning cycle."""
        with self._lock:
            self._next_cycle = datetime.utcnow()
        # Wait for cycle to complete (with timeout)
        time.sleep(2)
        with self._lock:
            if self._cycle_history:
                return self._cycle_history[-1]
            return None

    def get_status(self) -> dict:
        """Get learning loop status."""
        with self._lock:
            return {
                "running": self._running,
                "last_cycle": self._last_cycle.isoformat() if self._last_cycle else None,
                "next_cycle": self._next_cycle.isoformat() if self._next_cycle else None,
                "cycles_completed": len(self._cycle_history),
                "cycle_interval_seconds": self.cycle_interval.total_seconds(),
            }

    def get_history(self, limit: int = 10) -> list[dict]:
        """Get recent cycle history."""
        with self._lock:
            history = list(self._cycle_history)[-limit:]
            return [
                {
                    "cycle_id": c.cycle_id,
                    "timestamp": c.timestamp.isoformat(),
                    "duration_seconds": c.duration_seconds,
                    "contrastive": c.contrastive_training.get("status")
                    if isinstance(c.contrastive_training, dict)
                    else str(c.contrastive_training),
                    "evolution": c.prompt_evolution.get("status")
                    if isinstance(c.prompt_evolution, dict)
                    else str(c.prompt_evolution),
                    "distillation": c.distillation.get("status")
                    if isinstance(c.distillation, dict)
                    else str(c.distillation),
                }
                for c in history
            ]


# Global learning loop
_learning_loop = LearningLoop()


def start_learning_loop(
    cycle_interval_seconds: int = 300,
    min_engagements_per_cycle: int = 50,
) -> None:
    """Start the global learning loop."""
    global _learning_loop
    _learning_loop = LearningLoop(
        cycle_interval_seconds=cycle_interval_seconds,
        min_engagements_per_cycle=min_engagements_per_cycle,
    )
    _learning_loop.start()


def stop_learning_loop() -> None:
    """Stop the global learning loop."""
    _learning_loop.stop()


def force_learning_cycle() -> dict:
    """Force an immediate learning cycle."""
    return _learning_loop.force_cycle()


def get_learning_loop_status() -> dict:
    return _learning_loop.get_status()


def get_learning_history(limit: int = 10) -> list[dict]:
    return _learning_loop.get_history(limit)


def register_prompt_update_callback(callback) -> None:
    """Register callback for best prompt updates."""
    _learning_loop.register_prompt_update_callback(callback)
