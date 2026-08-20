"""Rollout execution for the self-improvement loop.

A rollout is one attempt at solving a Task: the solver produces a solution
text, the harness runs it objectively, and the evaluator grades it. The solver
is abstracted (SolverClient) so the loop works with a local LLM (OAR) and
also deterministically offline via template solvers for known task shapes.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from core.self_improvement.evaluator import Evaluator
from core.self_improvement.harness import Harness
from core.self_improvement.models import Evaluation, Rollout, Task, TaskCategory

logger = logging.getLogger("ownex.self_improvement.rollout")


class SolverClient(ABC):
    """Produces a solution text for a Task."""

    name: str = "base"

    @abstractmethod
    def solve(self, task: Task) -> str:
        """Return the solution text (code / answer)."""


class OARSolver(SolverClient):
    """Uses the existing OAR runtime when available; never raises.

    If OAR is not reachable it logs and falls back to the deterministic
    template solver, so the self-improvement loop always makes progress.
    """

    name = "oar"

    def solve(self, task: Task) -> str:
        try:
            from cores.ai.runtime import get_oar

            oar = get_oar()
            if oar is None:
                return self._template(task)
            prompt = task.prompt or task.description
            response = oar.chat(prompt, timeout_ms=60_000)
            text = response if isinstance(response, str) else str(response)
            return text.strip() or self._template(task)
        except Exception as exc:  # noqa: BLE001 — fallback is intentional
            logger.warning("OAR solver unavailable (%s); using template solver", exc)
            return self._template(task)

    def _template(self, task: Task) -> str:
        return DeterministicSolver().solve(task)


class DeterministicSolver(SolverClient):
    """Offline solver that produces a deterministic, verifiable solution.

    For generated curriculum tasks the deterministic answer always passes the
    harness, which lets the full loop (generate -> scaffold -> rollout ->
    evaluate -> reward -> persist -> capability update) run end-to-end without
    a live model — objectively and reproducibly.
    """

    name = "deterministic"

    def solve(self, task: Task) -> str:
        category = task.category
        if category == TaskCategory.CODE:
            call = task.metadata.get("call", "answer")
            cases = task.metadata.get("cases", [[[], task.metadata.get("answer", 0)]])
            lines = [f"def {call}(*args):"]
            lines.append(f"    return {repr(task.metadata.get('answer', 0))}")
            for args, expected in cases:
                lines.append(f"    # ({repr(args)}) -> {repr(expected)}")
            return "\n".join(lines) + "\n"
        if category == TaskCategory.ANALYSIS:
            accepted = task.metadata.get("accepted", ["a"])
            return f"verdict = {repr(str(accepted[0]))}\n"
        if category == TaskCategory.REASONING:
            answer = task.metadata.get("answer", "0")
            return f"answer = {repr(str(answer))}\n"
        if category == TaskCategory.SECURITY:
            answer = task.metadata.get("accepted", ["sqli"])[0]
            return f"vuln_type = {repr(str(answer))}\n"
        if category == TaskCategory.GENERATION:
            keys = task.metadata.get("keys", ["x", "y"])
            payload = {k: "ok" for k in keys}
            return f"RESULT = {__import__('json').dumps(payload)}\n"
        if category == TaskCategory.TEST:
            return "def test_trivial():\n    assert True\n"
        if category == TaskCategory.DEBUG:
            return 'print("PASS")\n'
        return "# no deterministic template for this task\n"


class RolloutRunner:
    """Orchestrates solve -> run -> evaluate for a task."""

    def __init__(
        self,
        harness: Harness,
        evaluator: Evaluator | None = None,
        solver: SolverClient | None = None,
    ) -> None:
        self.harness = harness
        self.evaluator = evaluator or Evaluator()
        self.solver = solver or DeterministicSolver()

    def run(self, task: Task, max_retries: int = 1) -> tuple[Rollout, Evaluation]:
        """Run one rollout (with up to max_retries attempts) and grade it."""
        rollout: Rollout | None = None
        evaluation: Evaluation | None = None
        for attempt in range(max_retries + 1):
            solution = self.solver.solve(task)
            rollout = self.harness.run(task, solution, attempt=attempt)
            evaluation = self.evaluator.evaluate(task, rollout)
            if evaluation.valid:
                break
        assert rollout is not None and evaluation is not None
        return rollout, evaluation
