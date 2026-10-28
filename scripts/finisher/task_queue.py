"""Task queue and prioritization for OWNEX Finisher."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from scripts.finisher.locks import GLOBAL_LOCK, PathLockManager, normalize_path
from scripts.finisher.state import FinisherState, Task, TaskStatus


class TaskPriority(Enum):
    CRITICAL_BLOCKER = 0
    DEPENDENCY_UNBLOCKER = 10
    RELEASE_BLOCKER = 20
    REGRESSION = 30
    IMPORTANT_DEBT = 40
    POLISH = 50
    OPTIONAL_IMPROVEMENT = 60


AREA_WEIGHTS = {
    "architecture": 0.20,
    "core_functionality": 0.25,
    "frontend": 0.15,
    "ai_agents": 0.10,
    "security": 0.10,
    "testing": 0.10,
    "data_release": 0.10,
}

# Weight for task areas outside the canonical map. Must be > 0 so work in
# unmapped areas is never silently worth 0% of the global number.
FALLBACK_AREA_WEIGHT: float = 0.10


@dataclass
class TaskScore:
    task_id: str
    priority_score: float
    blocking_power: float
    dependency_impact: float
    risk: float
    verification_difficulty: float
    effort: float
    parallelizability: float
    architecture_importance: float
    release_impact: float
    total: float


class TaskQueue:
    def __init__(self, state: FinisherState):
        self.state = state
        self.locks = PathLockManager(state)

    def get_ready_tasks(self) -> list[Task]:
        now = time.time()
        ready = []
        for task in self.state.tasks.values():
            if task.status != TaskStatus.PENDING and task.status != TaskStatus.READY:
                continue
            if task.next_attempt_after and now < task.next_attempt_after:
                continue  # exponential backoff between retries
            if self._dependencies_met(task):
                if self._is_blocked_by_human_gate(task):
                    continue
                if self.is_lock_conflicted(task):
                    continue
                ready.append(task)
        return ready

    def next_available_in(self) -> float:
        """Seconds until the earliest backoff expires (0 if something is ready)."""
        now = time.time()
        waits = [
            t.next_attempt_after - now
            for t in self.state.tasks.values()
            if t.status in (TaskStatus.READY, TaskStatus.PENDING) and t.next_attempt_after > now
        ]
        return max(0.0, min(waits)) if waits else 0.0

    def is_lock_conflicted(self, task: Task) -> bool:
        """True when another worker already holds overlapping paths.

        A task that declares no files is treated as repo-wide: an unbounded
        task must never run beside a bounded one.
        """
        paths = [normalize_path(p) for p in (task.files or [])] or [GLOBAL_LOCK]
        return bool(self.locks.conflicting_locks(paths))

    def _dependencies_met(self, task: Task) -> bool:
        for dep_id in task.dependencies:
            dep_task = self.state.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.PASSED:
                return False
        return True

    def _is_blocked_by_human_gate(self, task: Task) -> bool:
        """A task is blocked only by gates that reference IT.

        Gate ids are not reliably `gate_{task_id}`: RecoveryEngine creates
        `gate_{task_id}_recovery_{failure_type}`. Matching on the id prefix
        alone missed every recovery gate, so gated tasks kept running.
        """
        if task.status == TaskStatus.WAITING_HUMAN:
            return True

        for gate_id, gate in self.state.human_gates.items():
            if gate.get("decision") == "APPROVE":
                continue
            references_task = gate.get("task_id") == task.id
            if not references_task and gate_id.startswith(f"gate_{task.id}"):
                references_task = True
            if references_task:
                return True
        return False

    def score_tasks(self, tasks: list[Task]) -> list[TaskScore]:
        scores = []
        for task in tasks:
            score = self._calculate_score(task)
            scores.append(score)
        scores.sort(key=lambda s: s.total)
        return scores

    def _calculate_score(self, task: Task) -> TaskScore:
        priority_map = {
            "critical_blocker": 0,
            "dependency_unblocker": 10,
            "release_blocker": 20,
            "regression": 30,
            "important_debt": 40,
            "polish": 50,
            "optional_improvement": 60,
        }
        priority = priority_map.get(task.area, 50)

        blocking_power = self._calculate_blocking_power(task)
        dependency_impact = len(task.dependencies) * 2
        risk = task.priority * 0.5
        verification_difficulty = len(task.verification_commands) * 1.5
        effort = task.weight * 5
        parallelizability = 0 if task.dependencies else -5
        architecture_importance = AREA_WEIGHTS.get(task.area, 0.1) * 100
        release_impact = 10 if "release" in task.phase.lower() else 0

        total = (
            priority
            + blocking_power
            + dependency_impact
            + risk
            + verification_difficulty
            + effort
            + parallelizability
            - architecture_importance
            - release_impact
        )

        return TaskScore(
            task_id=task.id,
            priority_score=priority,
            blocking_power=blocking_power,
            dependency_impact=dependency_impact,
            risk=risk,
            verification_difficulty=verification_difficulty,
            effort=effort,
            parallelizability=parallelizability,
            architecture_importance=architecture_importance,
            release_impact=release_impact,
            total=total,
        )

    def _calculate_blocking_power(self, task: Task) -> float:
        count = 0
        for other in self.state.tasks.values():
            if task.id in other.dependencies:
                count += 1
        return count * 5

    def get_next_best_task(self) -> Task | None:
        ready = self.get_ready_tasks()
        if not ready:
            return None
        scored = self.score_tasks(ready)
        return self.state.tasks[scored[0].task_id]

    def get_blocked_tasks(self) -> list[Task]:
        blocked = []
        for task in self.state.tasks.values():
            if task.status in [TaskStatus.BLOCKED, TaskStatus.WAITING_HUMAN]:
                blocked.append(task)
        return blocked

    def get_running_tasks(self) -> list[Task]:
        return [t for t in self.state.tasks.values() if t.status == TaskStatus.RUNNING]

    def get_failed_tasks(self) -> list[Task]:
        return [t for t in self.state.tasks.values() if t.status == TaskStatus.FAILED]

    def get_completed_tasks(self) -> list[Task]:
        return [t for t in self.state.tasks.values() if t.status == TaskStatus.PASSED]

    def get_verification_pending_tasks(self) -> list[Task]:
        return [t for t in self.state.tasks.values() if t.status == TaskStatus.VERIFYING]

    def calculate_progress(self) -> dict[str, Any]:
        """Weighted progress computed from state flags, never from text.

        Constitution rule 9/18: a model writing "verified" in its own result
        string must never move the verified metric. Only VerificationEngine,
        after a command actually passed, sets `task.verified`.
        """
        area_progress = {}
        area_weights = AREA_WEIGHTS

        # Union of known areas and any area tasks actually declare. A task in
        # an unmapped area must still move the global number — otherwise work
        # silently counts as 0% (live incident: two verified sandbox tasks in
        # "documentation"/"backend" showed Overall 0.0%).
        # Scope (§5, rule 8): the denominator is REQUIRED tasks only.
        # Blocked/failed/optional tasks are never deleted to inflate the
        # number; optional ones are reported separately below.
        in_scope = [t for t in self.state.tasks.values() if t.required]
        out_of_scope_weight = round(sum(t.weight for t in self.state.tasks.values() if not t.required), 2)
        present_areas = sorted({t.area for t in in_scope})
        weights = {a: area_weights.get(a, FALLBACK_AREA_WEIGHT) for a in present_areas}

        for area in present_areas:
            area_tasks = [t for t in in_scope if t.area == area]
            total_weight = sum(t.weight for t in area_tasks)
            if total_weight == 0:
                area_progress[area] = 0.0
                continue

            # Verified flag only — never bare PASSED status. An implemented
            # but unverified task counts as 0% of its area (rule 9/18).
            verified_weight = sum(t.weight for t in area_tasks if t.verified)
            area_progress[area] = verified_weight / total_weight * 100

        # Only areas that actually have tasks contribute; a missing area must
        # not silently deflate overall progress toward an unreachable number.
        active_weight = sum(w for a, w in weights.items() if self._area_has_tasks(a))
        if active_weight == 0:
            overall = 0.0
        else:
            overall = sum(area_progress[a] * w for a, w in weights.items() if self._area_has_tasks(a)) / active_weight

        implemented = sum(
            t.weight for t in in_scope if t.status in [TaskStatus.RUNNING, TaskStatus.VERIFYING, TaskStatus.PASSED]
        )
        total = sum(t.weight for t in in_scope)
        task_completion = (implemented / total * 100) if total > 0 else 0

        verified = sum(t.weight for t in in_scope if t.verified)
        verified_completion = (verified / total * 100) if total > 0 else 0

        integrated = sum(t.weight for t in in_scope if t.verified and t.status == TaskStatus.PASSED)
        release_readiness = (integrated / total * 100) if total > 0 else 0

        return {
            "overall": overall,
            "scope": {
                "required_tasks": len(in_scope),
                "optional_excluded_weight": out_of_scope_weight,
            },
            "task_completion": task_completion,
            "verified_completion": verified_completion,
            "release_readiness": release_readiness,
            "areas": area_progress,
            "implemented": sum(
                1
                for t in self.state.tasks.values()
                if t.status in [TaskStatus.RUNNING, TaskStatus.VERIFYING, TaskStatus.PASSED]
            ),
            "verified": sum(1 for t in self.state.tasks.values() if t.verified),
            "blocked": len(self.get_blocked_tasks()),
            "failed": len(self.get_failed_tasks()),
            "remaining": sum(
                1 for t in self.state.tasks.values() if t.status in [TaskStatus.PENDING, TaskStatus.READY]
            ),
        }

    def _area_has_tasks(self, area: str) -> bool:
        return any(t.area == area and t.required for t in self.state.tasks.values())
