"""State management for OWNEX Finisher."""

from __future__ import annotations

import contextlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from cores.utils.oscompat import LockHeldError, acquire_lock, release_lock

REPO_ROOT = Path(__file__).resolve().parents[2]
FINISHER_STATE_DIR = Path(os.environ.get("FINISHER_STATE_DIR", str(REPO_ROOT / ".finisher")))


class StatusEnum(Enum):
    """Enum whose members compare equal to their string value.

    `WorkerStatus.RUNNING == "running"` and `"running" in [WorkerStatus.RUNNING]`
    both behave correctly, so status checks cannot silently fail on type.
    """

    @classmethod
    def _missing_(cls, value: object) -> StatusEnum | None:
        for member in cls:
            if member.value == value:
                return member
        return None

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, StatusEnum):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)


class TaskStatus(StatusEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    VERIFYING = "verifying"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    WAITING_HUMAN = "waiting_human"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class ProjectStatus(StatusEnum):
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_HUMAN = "waiting_human"
    BLOCKED = "blocked"
    FAILED = "failed"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    STOPPED = "stopped"


class WorkerStatus(StatusEnum):
    STARTING = "starting"
    ALIVE = "alive"
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    CRASHED = "crashed"
    TIMEOUT = "timeout"
    TERMINATED = "terminated"
    UNAVAILABLE = "unavailable"


@dataclass
class AcceptanceCriteria:
    description: str
    verification_command: str
    expected_output: str = ""
    required: bool = True


@dataclass
class Task:
    id: str
    title: str
    description: str
    phase: str
    priority: int
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    acceptance_criteria: list[AcceptanceCriteria] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    assigned_worker: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    checkpoint: str | None = None
    result: str | None = None
    failure_reason: str | None = None
    rollback_information: str | None = None
    weight: float = 1.0
    area: str = "general"
    verified: bool = False
    verified_at: str | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    next_attempt_after: float = 0.0
    # Scope control (§5): only required tasks count toward the global
    # denominator. required=False is for approved out-of-scope work — it stays
    # visible, never silently deleted. Defaults True so all existing states
    # behave exactly as before.
    required: bool = True
    version: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "phase": self.phase,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "acceptance_criteria": [
                {
                    "description": ac.description,
                    "verification_command": ac.verification_command,
                    "expected_output": ac.expected_output,
                    "required": ac.required,
                }
                for ac in self.acceptance_criteria
            ],
            "verification_commands": self.verification_commands,
            "assigned_worker": self.assigned_worker,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "checkpoint": self.checkpoint,
            "result": self.result,
            "failure_reason": self.failure_reason,
            "rollback_information": self.rollback_information,
            "weight": self.weight,
            "area": self.area,
            "verified": self.verified,
            "verified_at": self.verified_at,
            "evidence": self.evidence,
            "files": self.files,
            "next_attempt_after": self.next_attempt_after,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        task = cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            phase=data["phase"],
            priority=data["priority"],
            dependencies=data.get("dependencies", []),
            status=TaskStatus(data.get("status", "pending")),
            verification_commands=data.get("verification_commands", []),
            assigned_worker=data.get("assigned_worker"),
            attempt_count=data.get("attempt_count", 0),
            max_attempts=data.get("max_attempts", 3),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            checkpoint=data.get("checkpoint"),
            result=data.get("result"),
            failure_reason=data.get("failure_reason"),
            rollback_information=data.get("rollback_information"),
            weight=data.get("weight", 1.0),
            area=data.get("area", "general"),
        )
        task.verified = bool(data.get("verified", False))
        task.verified_at = data.get("verified_at")
        task.evidence = data.get("evidence", [])
        task.files = data.get("files", [])
        task.next_attempt_after = float(data.get("next_attempt_after", 0.0) or 0.0)
        task.required = bool(data.get("required", True))
        task.acceptance_criteria = [
            AcceptanceCriteria(
                description=ac["description"],
                verification_command=ac["verification_command"],
                expected_output=ac.get("expected_output", ""),
                required=ac.get("required", True),
            )
            for ac in data.get("acceptance_criteria", [])
        ]
        return task


@dataclass
class Worker:
    worker_id: str
    task_id: str | None = None
    process_id: int | None = None
    # Epoch de creación del proceso visto al lanzar. Permite distinguir el
    # proceso esperado de un PID reutilizado por el SO (ver is_expected_process).
    # None = registro legacy sin dato (se degrada a chequeo solo-PID).
    process_create_time: float | None = None
    status: WorkerStatus = WorkerStatus.STARTING
    model: str = "auto"
    working_directory: str = str(REPO_ROOT)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now().isoformat())
    stdout_log: str = ""
    stderr_log: str = ""
    exit_code: int | None = None
    attempt: int = 1
    failure_reason: str | None = None
    lock_id: str | None = None
    worktree_path: str | None = None
    branch: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "task_id": self.task_id,
            "process_id": self.process_id,
            "process_create_time": self.process_create_time,
            "status": self.status.value,
            "model": self.model,
            "working_directory": self.working_directory,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "stdout_log": self.stdout_log,
            "stderr_log": self.stderr_log,
            "exit_code": self.exit_code,
            "attempt": self.attempt,
            "failure_reason": self.failure_reason,
            "lock_id": self.lock_id,
            "worktree_path": self.worktree_path,
            "branch": self.branch,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Worker:
        return cls(
            worker_id=data["worker_id"],
            task_id=data.get("task_id"),
            process_id=data.get("process_id"),
            process_create_time=data.get("process_create_time"),
            status=WorkerStatus(data.get("status", "starting")),
            model=data.get("model", "auto"),
            working_directory=data.get("working_directory", str(REPO_ROOT)),
            started_at=data.get("started_at", datetime.now().isoformat()),
            last_heartbeat=data.get("last_heartbeat", datetime.now().isoformat()),
            stdout_log=data.get("stdout_log", ""),
            stderr_log=data.get("stderr_log", ""),
            exit_code=data.get("exit_code"),
            attempt=data.get("attempt", 1),
            failure_reason=data.get("failure_reason"),
            lock_id=data.get("lock_id"),
            worktree_path=data.get("worktree_path"),
            branch=data.get("branch"),
        )


@dataclass
class Checkpoint:
    checkpoint_id: str
    timestamp: str
    task_id: str | None
    worker_id: str | None
    git_commit: str | None
    modified_files: list[str]
    verification_status: str
    worker_state: dict[str, Any]
    model: str
    task_progress: float
    failures: list[str]
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "git_commit": self.git_commit,
            "modified_files": self.modified_files,
            "verification_status": self.verification_status,
            "worker_state": self.worker_state,
            "model": self.model,
            "task_progress": self.task_progress,
            "failures": self.failures,
            "next_action": self.next_action,
        }


@dataclass
class FinisherState:
    project_status: ProjectStatus = ProjectStatus.STOPPED
    tasks: dict[str, Task] = field(default_factory=dict)
    workers: dict[str, Worker] = field(default_factory=dict)
    checkpoints: list[Checkpoint] = field(default_factory=list)
    human_gates: dict[str, dict] = field(default_factory=dict)
    locks: dict[str, dict[str, Any]] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 0  # Optimistic locking version
    tombstones: dict[str, dict[str, Any]] = field(default_factory=dict)  # Tombstone records with TTL

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_status": self.project_status.value,
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
            "workers": {k: v.to_dict() for k, v in self.workers.items()},
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "human_gates": self.human_gates,
            "locks": self.locks,
            "metrics": self.metrics,
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinisherState:
        state = cls(
            project_status=ProjectStatus(data.get("project_status", "stopped")),
            config=data.get("config", {}),
            metrics=data.get("metrics", {}),
            human_gates=data.get("human_gates", {}),
            locks=data.get("locks", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )
        state.tasks = {k: Task.from_dict(v) for k, v in data.get("tasks", {}).items()}
        state.workers = {k: Worker.from_dict(v) for k, v in data.get("workers", {}).items()}
        state.checkpoints = [Checkpoint(**c) for c in data.get("checkpoints", [])]
        return state


class StateManager:
    def __init__(self, state_dir: Path | None = None, lock: bool = False):
        self.state_dir = state_dir or FINISHER_STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "state.json"
        if lock:
            self.acquire_instance_lock()
        self.state = self._load()

    def acquire_instance_lock(self) -> None:
        """Advisory single-daemon lock. Prevents two Finisher processes from
        interleaving state writes and launching duplicate workers."""
        self.lock_file = self.state_dir / "finisher.lock"
        try:
            acquire_lock(self.lock_file)
        except LockHeldError as e:
            raise RuntimeError(f"Another Finisher instance holds {self.lock_file}. Refusing to start.") from e

    def release_instance_lock(self) -> None:
        lock_file = getattr(self, "lock_file", None)
        if lock_file is None:
            return
        with contextlib.suppress(Exception):
            release_lock(lock_file)

    def recover_interrupted_tasks(self) -> list[str]:
        """Boot recovery: release tasks stranded mid-flight by a dead daemon.

        Call only from the lock-holding daemon at start. Tasks in RUNNING
        or VERIFYING whose worker is gone are requeued (READY) or BLOCKED
        when attempts are exhausted; stale worker records go CRASHED.
        Tasks with a live worker are never touched.
        """
        from scripts.finisher.worker import is_expected_process  # lazy: worker imports state

        live_states = (WorkerStatus.RUNNING, WorkerStatus.STARTING, WorkerStatus.ALIVE)
        recovered: list[str] = []
        for task in self.state.tasks.values():
            if task.status not in (TaskStatus.RUNNING, TaskStatus.VERIFYING):
                continue
            worker = self.state.workers.get(task.assigned_worker) if task.assigned_worker else None
            alive = bool(
                worker is not None
                and worker.status in live_states
                and is_expected_process(worker.process_id, worker.process_create_time)
            )
            if alive:
                continue
            if worker is not None and worker.status in live_states:
                worker.status = WorkerStatus.CRASHED
                worker.failure_reason = "daemon restarted; worker gone"
            task.assigned_worker = None
            if task.attempt_count >= task.max_attempts:
                task.status = TaskStatus.BLOCKED
                task.failure_reason = "Interrupted mid-flight; attempts exhausted"
            else:
                task.status = TaskStatus.READY
                task.failure_reason = None
            task.updated_at = datetime.now().isoformat()
            recovered.append(task.id)
        if recovered:
            self.save()
        return recovered

    def _load(self) -> FinisherState:
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                return FinisherState.from_dict(data)
            except Exception as e:
                print(f"Warning: Failed to load state: {e}. Starting fresh.")
                return FinisherState()
        return FinisherState()

    def save(self) -> None:
        """Atomic write: temp file + fsync + rename. A crash mid-write can never
        leave a truncated state.json (constitutional rule 11: always recoverable)."""
        self.state.updated_at = datetime.now().isoformat()
        self.state.version += 1
        tmp = self.state_file.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self.state.to_dict(), f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.state_file)

    def reload(self) -> bool:
        """Re-read state.json, adopting external changes (CLI approve/pause/resume).

        Live incident: the daemon cached state at startup, so `approve` from
        another process never reached the running loop — gates were decorative
        until restart. Updates IN PLACE so every holder of the state object
        (queue, engines, managers) sees the same data without rebinding.

        Returns True when disk state was adopted, False when kept memory
        (missing/corrupt file — never clobber good memory with bad disk).
        """
        if not self.state_file.exists():
            return False
        try:
            with open(self.state_file) as f:
                fresh = FinisherState.from_dict(json.load(f))
        except Exception as e:
            print(f"Warning: Keeping in-memory state, disk reload failed: {e}")
            return False
        self.state.__dict__.update(fresh.__dict__)
        return True

    def get_state(self) -> FinisherState:
        return self.state

    def add_task(self, task: Task) -> None:
        self.state.tasks[task.id] = task
        self.save()

    def update_task(self, task: Task) -> None:
        task.updated_at = datetime.now().isoformat()
        self.state.tasks[task.id] = task
        self.save()

    def compare_and_swap_task(
        self, task_id: str, expected_version: int, update_fn: Callable[[Task], Task]
    ) -> tuple[bool, Task | None]:
        """Compare-and-swap for task updates.

        Args:
            task_id: Task ID to update
            expected_version: Expected version number
            update_fn: Function that takes the task and returns the modified task

        Returns:
            (success, updated_task_or_none)
        """
        task = self.state.tasks.get(task_id)
        if task is None:
            return False, None
        if task.version != expected_version:
            return False, task

        new_task = update_fn(task)
        new_task.version = task.version + 1
        new_task.updated_at = datetime.now().isoformat()
        self.state.tasks[task_id] = new_task
        self.save()
        return True, new_task

    def get_task(self, task_id: str) -> Task | None:
        return self.state.tasks.get(task_id)

    def add_worker(self, worker: Worker) -> None:
        self.state.workers[worker.worker_id] = worker
        self.save()

    def update_worker(self, worker: Worker) -> None:
        worker.last_heartbeat = datetime.now().isoformat()
        self.state.workers[worker.worker_id] = worker
        self.save()

    def get_worker(self, worker_id: str) -> Worker | None:
        return self.state.workers.get(worker_id)

    def add_checkpoint(self, checkpoint: Checkpoint) -> None:
        self.state.checkpoints.append(checkpoint)
        if len(self.state.checkpoints) > 100:
            self.state.checkpoints = self.state.checkpoints[-100:]
        self.save()

    # -- Tombstone management (Phase 2) --------------------------------------

    def add_tombstone(self, entity_type: str, entity_id: str, reason: str, ttl_seconds: int = 86400) -> None:
        """Add a tombstone for a soft-deleted entity.

        Args:
            entity_type: Type of entity (task, worker, lock, etc.)
            entity_id: ID of the deleted entity
            reason: Reason for deletion
            ttl_seconds: Time-to-live in seconds (default: 24 hours)
        """
        tombstone_id = f"{entity_type}:{entity_id}"
        self.state.tombstones[f"{entity_type}:{entity_id}"] = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat(),
        }
        self.save()

    def cleanup_tombstones(self, now: float | None = None) -> int:
        """Remove expired tombstones. Returns count of removed tombstones."""
        now_ts = now if now is not None else time.time()
        expired = [
            tombstone_id
            for tombstone_id, ts in self.state.tombstones.items()
            if datetime.fromisoformat(ts["expires_at"]).timestamp() <= now_ts
        ]
        for tombstone_id in expired:
            del self.state.tombstones[tombstone_id]
        if expired:
            self.save()
        return len(expired)

    def is_tombstoned(self, entity_type: str, entity_id: str) -> bool:
        """Check if an entity has been tombstoned (soft-deleted)."""
        tombstone = self.state.tombstones.get(f"{entity_type}:{entity_id}")
        if tombstone is None:
            return False
        if datetime.fromisoformat(tombstone["expires_at"]) < datetime.now():
            return False  # Expired
        return True

    def batch_update(self, operations: list[Callable[[FinisherState], None]]) -> bool:
        """Execute multiple operations atomically.

        Args:
            operations: List of callables that take the state and modify it.

        Returns:
            True if all operations succeeded, False otherwise.
        """
        expected_version = self.state.version
        try:
            for op in operations:
                op(self.state)
            self.state.updated_at = datetime.now().isoformat()
            self.state.version += 1
            tmp = self.state_file.with_suffix(".json.tmp")
            with open(tmp, "w") as f:
                json.dump(self.state.to_dict(), f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.state_file)
            return True
        except Exception as e:
            print(f"Warning: Batch update failed: {e}")
            return False

    def add_human_gate(self, gate_id: str, gate_info: dict) -> None:
        self.state.human_gates[gate_id] = gate_info
        self.save()

    def resolve_human_gate(self, gate_id: str, decision: str) -> None:
        """Record a gate decision and move the gated task accordingly.

        Previously a decision was recorded but the task stayed WAITING_HUMAN
        forever, so APPROVE never actually resumed anything and the gate flow
        was decorative. Now:
          APPROVE → task returns to READY when attempts remain (retry budget
                    is NOT reset; max_attempts still enforced).
          REJECT  → task goes BLOCKED with the rejection recorded.
        """
        if gate_id not in self.state.human_gates:
            return
        gate = self.state.human_gates[gate_id]
        gate["decision"] = decision
        gate["resolved_at"] = datetime.now().isoformat()

        from scripts.finisher.events import log_event

        log_event(
            "gate.resolved",
            f"Gate {gate_id} {decision} by operator",
            task_id=gate.get("task_id"),
            data={"gate_id": gate_id, "decision": decision},
        )

        task = self.state.tasks.get(gate.get("task_id", ""))
        if task is not None and task.status == TaskStatus.WAITING_HUMAN:
            if decision == "APPROVE":
                if task.attempt_count < task.max_attempts:
                    task.status = TaskStatus.READY
                    task.next_attempt_after = 0.0
                    task.failure_reason = None
                else:
                    task.status = TaskStatus.BLOCKED
                    task.failure_reason = f"Gate {gate_id} approved but attempts exhausted"
            elif decision == "REJECT":
                task.status = TaskStatus.BLOCKED
                task.failure_reason = f"Rejected by operator at gate {gate_id}"
            task.updated_at = datetime.now().isoformat()
        self.save()


state_manager = StateManager()
