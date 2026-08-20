"""Self-Improvement Engine for OWNEX.

Orchestrates the Ornith-style loop:

    generate -> scaffold -> rollout -> evaluate -> reward -> experience ->
    frontier update -> capability update

run_once() executes a single task end-to-end and persists everything.
run_batch() runs N tasks. All persistence is JSON with injectable paths so the
engine is testable without touching real data. The loop is always observable:
every step either produces data or an explicit reason why not.
"""

from __future__ import annotations

import logging
from typing import Any

from core.self_improvement.capability import CapabilityTracker
from core.self_improvement.config import SelfImprovementConfig, default_config
from core.self_improvement.evaluator import Evaluator
from core.self_improvement.experience import ExperienceStore
from core.self_improvement.frontier import DifficultyFrontier
from core.self_improvement.harness import Harness
from core.self_improvement.models import Experience, Scaffold, Task
from core.self_improvement.novelty import NoveltyScorer
from core.self_improvement.reward import RewardModel
from core.self_improvement.rollout import RolloutRunner, SolverClient
from core.self_improvement.scaffold_generator import ScaffoldGenerator
from core.self_improvement.task_generator import TaskGenerator

logger = logging.getLogger("ownex.self_improvement.engine")


class SelfImprovementEngine:
    """Single loop orchestrator with explicit dependencies."""

    def __init__(
        self,
        config: SelfImprovementConfig | None = None,
        *,
        solver: SolverClient | None = None,
        experiences_path: str | None = None,
        capabilities_path: str | None = None,
    ) -> None:
        self.config = config or default_config()
        self.experiences = ExperienceStore(self.config, experiences_path)
        self.capabilities = CapabilityTracker(self.config, capabilities_path)
        self.frontier = DifficultyFrontier(self.config)
        self.generator = TaskGenerator(self.config, self.frontier)
        self.scaffolds = ScaffoldGenerator()
        self.reward_model = RewardModel()
        self.evaluator = Evaluator()
        self.harness = Harness(self.config)
        self.runner = RolloutRunner(self.harness, self.evaluator, solver)

    def run_once(
        self,
        task: Task | None = None,
        *,
        skill_gaps: list[str] | None = None,
        reflections: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run a full loop iteration and persist the result."""
        history = self.experiences.all()

        # 1) Task: use the provided one or generate from context.
        if task is None:
            generated = self.generator.generate_batch(
                count=1,
                existing=[e.task for e in history],
                capabilities=self.capabilities.skills(),
                skill_gaps=skill_gaps or [],
                reflections=reflections or [],
            )
            if not generated:
                return {"status": "no_tasks", "reason": "generation returned no novel tasks"}
            task = generated[0]

        # 2) Scaffold
        scaffold: Scaffold = self.scaffolds.generate(task)

        # 3) Rollout (solve + run + grade)
        rollout, evaluation = self.runner.run(task, max_retries=self.config.max_retries_per_rollout)

        # 4) Reward with novelty against history
        scorer = NoveltyScorer(history)
        novelty = scorer.novelty(task)
        reward = self.reward_model.compute(task, evaluation, novelty)

        # 5) Frontier update
        difficulty_before = self.frontier.current_difficulty()
        self.frontier.record_outcome(task.difficulty, evaluation.valid)
        difficulty_after = self.frontier.current_difficulty()

        # 6) Persist experience + capability stats
        experience = Experience(
            id=task.id,
            task=task,
            scaffold=scaffold,
            evaluation=evaluation,
            reward=reward,
            difficulty_before=difficulty_before,
            difficulty_after=difficulty_after,
        )
        self.experiences.add(experience)
        for skill in task.skills:
            self.capabilities.record(skill, evaluation.valid, reward)

        return {
            "status": "completed",
            "task_id": task.id,
            "task_title": task.title,
            "category": task.category.value,
            "valid": evaluation.valid,
            "reward": reward,
            "novelty": novelty,
            "difficulty_before": difficulty_before,
            "difficulty_after": difficulty_after,
            "evaluation_notes": evaluation.notes,
            "rollout_exit_code": rollout.exit_code,
            "duration_ms": rollout.duration_ms,
            "skills": task.skills,
        }

    def run_batch(
        self, count: int = 3, *, skill_gaps: list[str] | None = None, reflections: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Generate `count` tasks once, then run a full loop iteration per task."""
        history = self.experiences.all()
        tasks = self.generator.generate_batch(
            count=count,
            existing=[e.task for e in history],
            capabilities=self.capabilities.skills(),
            skill_gaps=skill_gaps or [],
            reflections=reflections or [],
        )
        results: list[dict[str, Any]] = []
        for task in tasks:
            results.append(self.run_once(task=task, skill_gaps=skill_gaps, reflections=reflections))
        return results

    def status(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "experiences": self.experiences.count(),
            "success_rate": self.experiences.success_rate(),
            "frontier": self.frontier.to_dict(),
            "capabilities": self.capabilities.stats(),
            "policies": self.harness.policy.to_dict(),
        }

    def recommendations(self, limit: int = 5) -> list[dict[str, Any]]:
        """Suggest next skills based on capability stats and recent failures."""
        stats = self.capabilities.stats()
        recommendations: list[dict[str, Any]] = []
        for skill, entry in stats.items():
            rate = float(entry.get("success_rate", 0.0))
            attempts = int(entry.get("attempts", 0))
            if attempts > 0 and rate < 0.5:
                recommendations.append(
                    {
                        "skill": skill,
                        "kind": "improve",
                        "success_rate": rate,
                        "attempts": attempts,
                    }
                )
        recommendations.sort(key=lambda r: r["success_rate"])
        return recommendations[:limit]

    def close(self) -> None:
        self.harness.cleanup()


def get_self_improvement_engine() -> SelfImprovementEngine:
    """Module-level singleton for API and scheduler access."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = SelfImprovementEngine()
    return _ENGINE


_ENGINE: SelfImprovementEngine | None = None
