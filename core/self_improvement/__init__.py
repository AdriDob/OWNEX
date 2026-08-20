"""OWNEX Self-Improvement Engine.

Implements an Ornith-inspired curriculum loop (task generation -> scaffold ->
rollout -> evaluate -> reward -> experience -> frontier/capability update) that
runs locally, produces objective evidence via a policy-limited harness, and
persists experiences to steer future task selection. It never modifies its own
source code; it only improves the capabilities the registry already exposes.

Public API:
    - SelfImprovementEngine.run_once() / run_batch() / status()
    - get_self_improvement_engine()  (module-level singleton)
"""

from __future__ import annotations

from core.self_improvement.capability import CapabilityTracker
from core.self_improvement.config import SelfImprovementConfig, default_config
from core.self_improvement.engine import SelfImprovementEngine, get_self_improvement_engine
from core.self_improvement.evaluator import Evaluator
from core.self_improvement.experience import ExperienceStore
from core.self_improvement.frontier import DifficultyFrontier
from core.self_improvement.harness import Harness
from core.self_improvement.models import (
    CapabilityStats,
    Evaluation,
    Experience,
    Rollout,
    Scaffold,
    ScaffoldStep,
    Task,
    TaskCategory,
    TaskSource,
)
from core.self_improvement.novelty import NoveltyScorer
from core.self_improvement.policies import ExecutionPolicy, PolicyViolationError
from core.self_improvement.reward import RewardModel
from core.self_improvement.rollout import DeterministicSolver, OARSolver, RolloutRunner, SolverClient
from core.self_improvement.scaffold_generator import ScaffoldGenerator
from core.self_improvement.task_generator import TaskGenerator

__all__ = [
    "CapabilityStats",
    "CapabilityTracker",
    "DeterministicSolver",
    "DifficultyFrontier",
    "Evaluation",
    "Evaluator",
    "ExecutionPolicy",
    "Experience",
    "ExperienceStore",
    "Harness",
    "NoveltyScorer",
    "OARSolver",
    "PolicyViolationError",
    "RewardModel",
    "Rollout",
    "RolloutRunner",
    "Scaffold",
    "ScaffoldGenerator",
    "ScaffoldStep",
    "SelfImprovementConfig",
    "SelfImprovementEngine",
    "SolverClient",
    "Task",
    "TaskCategory",
    "TaskGenerator",
    "TaskSource",
    "default_config",
    "get_self_improvement_engine",
]
