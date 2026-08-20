"""Configuration for the OWNEX Self-Improvement Engine.

The engine is inspired by the Ornith-1.5 LOOP architecture (task generation,
scaffolding, rollout, reward, curriculum), but adapted to OWNEX as a local-first
system: no model training, no GRPO, no huge downloads. It improves a small set
of real capabilities by generating tasks, executing them inside a policy-limited
harness, measuring objective outcomes, and persisting experiences to steer the
next task selection.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Default storage root for engine state. Injected in tests via tmp_path.
DEFAULT_DATA_DIR = Path(os.environ.get("OWNEX_DATA_DIR", "data/self_improvement"))


@dataclass(frozen=True)
class SelfImprovementConfig:
    """Tunable knobs for the self-improvement loop."""

    # ── Storage ───────────────────────────────────────────────────
    data_dir: Path = DEFAULT_DATA_DIR
    task_store_path: Path = DEFAULT_DATA_DIR / "tasks.json"
    experience_store_path: Path = DEFAULT_DATA_DIR / "experiences.json"
    capability_store_path: Path = DEFAULT_DATA_DIR / "capabilities.json"
    policy_store_path: Path = DEFAULT_DATA_DIR / "policies.json"

    # ── Curriculum / frontier ─────────────────────────────────────
    p_target: float = 0.20  # target task success rate (~20% = challenging)
    frontier_sigma: float = 0.25  # gaussian spread around p_target
    difficulty_step: float = 0.05  # how much difficulty moves after each outcome

    # ── Rollout / execution ───────────────────────────────────────
    rollout_timeout_seconds: int = 60
    max_rollouts_per_task: int = 1
    max_retries_per_rollout: int = 1
    solver_model: str = ""  # empty => use the system AI router default
    max_solution_tokens: int = 2048
    allow_network: bool = False  # harness runs must not touch the network

    # ── Loop cadence ──────────────────────────────────────────────
    max_tasks_per_cycle: int = 3
    max_experiences_kept: int = 500
    min_experiences_before_frontier: int = 5

    # ── Harness policy ────────────────────────────────────────────
    allowed_commands: tuple[str, ...] = (
        "python",
        "pytest",
        "sh",
        "bash",
    )
    forbidden_keywords: tuple[str, ...] = (
        "rm -rf",
        "sudo",
        "chmod",
        "mkfs",
        "dd ",
        ":(){",
        "curl",
        "wget",
    )
    workdir_max_bytes: int = 1_000_000  # solution payload size limit

    # Derived helpers
    def resolve_path(self, path: Path) -> Path:
        """Expand env vars and ~ in a path, anchored under data_dir when relative."""
        p = Path(os.path.expandvars(str(path))).expanduser()
        if p.is_absolute():
            return p
        return self.data_dir / p

    def store_paths(self) -> dict[str, Path]:
        """Resolve all store paths (absolute) for persistence helpers."""
        return {
            "tasks": self.resolve_path(self.task_store_path),
            "experiences": self.resolve_path(self.experience_store_path),
            "capabilities": self.resolve_path(self.capability_store_path),
            "policies": self.resolve_path(self.policy_store_path),
        }

    def to_dict(self) -> dict[str, object]:
        """Serializable snapshot of the configuration (no Path objects)."""
        return {
            "data_dir": str(self.data_dir),
            "p_target": self.p_target,
            "frontier_sigma": self.frontier_sigma,
            "difficulty_step": self.difficulty_step,
            "rollout_timeout_seconds": self.rollout_timeout_seconds,
            "max_rollouts_per_task": self.max_rollouts_per_task,
            "max_retries_per_rollout": self.max_retries_per_rollout,
            "solver_model": self.solver_model,
            "max_solution_tokens": self.max_solution_tokens,
            "allow_network": self.allow_network,
            "max_tasks_per_cycle": self.max_tasks_per_cycle,
            "max_experiences_kept": self.max_experiences_kept,
            "min_experiences_before_frontier": self.min_experiences_before_frontier,
            "allowed_commands": list(self.allowed_commands),
            "forbidden_keywords": list(self.forbidden_keywords),
            "workdir_max_bytes": self.workdir_max_bytes,
        }


def default_config() -> SelfImprovementConfig:
    """Return the default engine configuration."""
    return SelfImprovementConfig()
