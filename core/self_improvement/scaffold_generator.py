"""Scaffold generation for the self-improvement loop.

A scaffold turns a Task into an executable plan: ordered steps plus objective
verification commands. The harness runs the steps and checks them. Scaffolds
are deterministic per task category — no free-form LLM scaffolding, so the
verification stays objective and reproducible.
"""

from __future__ import annotations

from core.self_improvement.models import Scaffold, ScaffoldStep, Task, TaskCategory

_VERIFICATION_STRATEGY: dict[TaskCategory, str] = {
    TaskCategory.CODE: "file",
    TaskCategory.TEST: "command",
    TaskCategory.DEBUG: "command",
    TaskCategory.ANALYSIS: "assertion",
    TaskCategory.GENERATION: "file",
    TaskCategory.SECURITY: "assertion",
    TaskCategory.REASONING: "assertion",
}


class ScaffoldGenerator:
    """Builds a deterministic, verifiable scaffold for a Task."""

    def generate(self, task: Task) -> Scaffold:
        category = task.category
        steps = [
            ScaffoldStep(
                index=1,
                instruction="Understand the task and its requirements.",
                verification="Read the prompt",
                check_type="file",
            ),
            ScaffoldStep(
                index=2,
                instruction="Produce the solution artifact (file or output).",
                verification="Artifact produced",
                check_type="file",
            ),
            ScaffoldStep(
                index=3,
                instruction="Run the objective verification for this category.",
                verification=self._verification(category),
                check_type=self._check_type(category),
            ),
        ]
        hints = self._hints(category)
        return Scaffold(task_id=task.id, steps=steps, hints=hints)

    def _verification(self, category: TaskCategory) -> str:
        return {
            TaskCategory.CODE: "Solution file imports cleanly and returns the expected value",
            TaskCategory.TEST: "pytest passes all test cases",
            TaskCategory.DEBUG: "Patched snippet produces the expected output",
            TaskCategory.ANALYSIS: "Verdict string matches one of the accepted answers",
            TaskCategory.GENERATION: "JSON artifact parses and contains the required keys",
            TaskCategory.SECURITY: "Detected vulnerability type matches the planted one",
            TaskCategory.REASONING: "Final answer string matches the expected answer",
        }.get(category, "Objective check passes")

    def _check_type(self, category: TaskCategory) -> str:
        return _VERIFICATION_STRATEGY.get(category, "file")

    def _hints(self, category: TaskCategory) -> list[str]:
        return {
            TaskCategory.CODE: ["Keep the solution pure and self-contained", "No external dependencies"],
            TaskCategory.TEST: ["Use pytest conventions", "One test function is enough"],
            TaskCategory.DEBUG: ["Look for off-by-one or type errors first", "Do not rewrite the whole snippet"],
            TaskCategory.ANALYSIS: ["Pick exactly one of the provided options"],
            TaskCategory.GENERATION: ["Return valid JSON only", "Include every required key"],
            TaskCategory.SECURITY: ["Reason about the data flow, not the framework"],
            TaskCategory.REASONING: ["Return only the final answer string"],
        }.get(category, [])
