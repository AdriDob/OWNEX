"""Worker management for OWNEX Finisher."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

from scripts.finisher.locks import GLOBAL_LOCK, PathLockManager, normalize_path, resolve_safely, validate_task_scope
from scripts.finisher.state import (
    REPO_ROOT,
    FinisherState,
    Task,
    TaskStatus,
    Worker,
    WorkerStatus,
    state_manager,
)
from scripts.finisher.worktree import worktree_manager

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_PID_IDENTITY_TOLERANCE_SECONDS = 2.0


def is_expected_process(process_id: int | None, expected_create_time: float | None) -> bool:
    """True solo si el PID pertenece al proceso que lanzamos.

    Un PID reutilizado por el SO pasa `is_running()` pero casi nunca comparte
    el instante de creación: se exige coincidencia (tolerancia documentada).
    Sin dato registrado (workers legacy) se degrada al chequeo solo-PID.
    Fail-closed: PID ausente, proceso muerto/inaccesible o psutil ausente
    devuelven False. Nunca termina procesos: solo clasifica.
    """
    if not process_id:
        return False
    if psutil is None:
        return False
    try:
        proc = psutil.Process(process_id)
        if not proc.is_running():
            return False
        if expected_create_time is None:
            return True
        try:
            actual = proc.create_time()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
        return abs(actual - float(expected_create_time)) <= _PID_IDENTITY_TOLERANCE_SECONDS
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


_SECRET_PATTERNS = (
    re.compile(r"(sk-[A-Za-z0-9_\-]{8,})"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)(api[_-]?key\"?\s*[:=]\s*\"?)[^\"\s,}]{6,}"),
)


def summarize_worker_error(raw: str, limit: int = 600) -> str:
    """Turn raw worker output into a short, classified, secret-free message.

    Provider errors arrive as coloured JSON blobs (e.g. opencode
    "UnknownError"). Without this the failure reason stays None and every
    failure is classified UNKNOWN, which makes recovery guesswork.
    """
    text = _ANSI_RE.sub("", raw or "").strip()
    if not text:
        return "worker produced no output"

    # Prefer the provider's own message field when present.
    for match in re.finditer(r'"message"\s*:\s*"([^"]{4,400})"', text):
        text = match.group(1)
        break
    else:
        m = re.search(r'"name"\s*:\s*"([^"]+)"', text)
        if m:
            text = f"{m.group(1)}: {text[:400]}"

    text = " ".join(text.split())
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(r"\1[REDACTED]" if pattern.groups else "[REDACTED]", text)
    return text[:limit]


class WorkerManager:
    def __init__(self, state: FinisherState | None = None):
        self._fallback_state = state
        self.processes: dict[str, subprocess.Popen] = {}
        self.max_workers = int(os.environ.get("FINISHER_MAX_WORKERS", "2"))
        self.heartbeat_interval = 30
        self.worker_timeout = int(os.environ.get("FINISHER_WORKER_TIMEOUT", "1800"))

    @property
    def state(self) -> FinisherState:
        """Always the live state.

        Capturing it at construction makes this object go stale whenever the
        state manager's state is replaced (reload, test isolation, recovery).
        """
        return state_manager.get_state()

    @property
    def locks(self) -> PathLockManager:
        return PathLockManager(self.state)

    def acquire_paths_for(self, worker: Worker, task: Task) -> bool:
        """Claim the task's file scope before spawning a process.

        Refuses to launch when another worker already owns overlapping paths,
        so two agents can never edit the same files at the same time.
        Also refuses tasks whose declared scope escapes the repo (absolute
        paths, `..`): validated here because the worktree is not an OS jail.
        Also resolves symlinks and verifies no path escapes the repo.
        """
        scope_errors = validate_task_scope(task.files)
        if scope_errors:
            worker.status = WorkerStatus.UNAVAILABLE
            worker.failure_reason = f"out-of-scope task files: {scope_errors[0]}"
            state_manager.update_worker(worker)
            state_manager.save()
            return False
        paths = [normalize_path(p) for p in (task.files or [])] or [GLOBAL_LOCK]

        # Resolve symlinks and verify no path escapes the repo
        resolved_paths: list[str] = []
        for p in paths:
            try:
                resolved = resolve_safely(p)
                resolved_paths.append(str(resolved))
            except ValueError as e:
                worker.status = WorkerStatus.UNAVAILABLE
                worker.failure_reason = f"path escapes repo: {e}"
                state_manager.update_worker(worker)
                state_manager.save()
                return False

        result = self.locks.acquire(owner=worker.worker_id, paths=resolved_paths, task_id=task.id)
        if not result.acquired:
            worker.status = WorkerStatus.UNAVAILABLE
            worker.failure_reason = f"lock conflict: {result.reason}"
            state_manager.update_worker(worker)
            state_manager.save()
            return False
        worker.lock_id = result.lock_id
        state_manager.update_worker(worker)
        return True

    def release_paths_for(self, worker_id: str) -> None:
        self.locks.release_for_owner(worker_id)
        state_manager.save()

    def launch_worker(self, worker: Worker, task: Task, model: str = "auto") -> bool:
        if not self.acquire_paths_for(worker, task):
            return False

        worker.task_id = task.id
        worker.model = model
        worker.status = WorkerStatus.STARTING
        worker.attempt += 1
        state_manager.update_worker(worker)

        self.isolate_worker(worker, task)

        cmd = self._build_opencode_command(worker, task, model)

        try:
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            process = subprocess.Popen(
                cmd,
                cwd=worker.working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
                start_new_session=True,
            )
            worker.process_id = process.pid
            try:
                worker.process_create_time = psutil.Process(process.pid).create_time() if psutil else None
            except Exception:
                worker.process_create_time = None
            worker.status = WorkerStatus.RUNNING
            worker.started_at = datetime.now().isoformat()
            self.processes[worker.worker_id] = process
            state_manager.update_worker(worker)

            asyncio.create_task(self._monitor_worker(worker, task, process))
            return True
        except Exception as e:
            worker.status = WorkerStatus.CRASHED
            worker.failure_reason = str(e)
            state_manager.update_worker(worker)
            self.release_paths_for(worker.worker_id)
            return False

    def _build_opencode_command(self, worker: Worker, task: Task, model: str) -> list[str]:
        cmd = ["opencode", "run"]

        prompt = self._build_task_prompt(task)
        cmd.append(prompt)

        if model != "auto":
            cmd.extend(["--model", model])

        return cmd

    def _build_task_prompt(self, task: Task) -> str:
        criteria = "\n".join([f"- {ac.description}: {ac.verification_command}" for ac in task.acceptance_criteria])

        return f"""TASK: {task.title}
ID: {task.id}
PHASE: {task.phase}
DESCRIPTION: {task.description}

ACCEPTANCE CRITERIA:
{criteria}

VERIFICATION COMMANDS:
{chr(10).join(task.verification_commands)}

CONSTRAINTS:
- Do not modify protected files without policy
- Always checkpoint before/after critical operations
- Prefer free models
- Reuse existing infrastructure through adapters
- Do not treat known baseline test failures as regressions

REPORTING:
When complete, output a JSON summary with:
- status: "completed" | "failed" | "blocked"
- result: brief description
- verification_evidence: output of verification commands
- modified_files: list of files changed"""

    async def _monitor_worker(self, worker: Worker, task: Task, process: subprocess.Popen) -> None:
        try:
            stdout, stderr = await asyncio.get_event_loop().run_in_executor(
                None, process.communicate, None, self.worker_timeout
            )

            worker.stdout_log = stdout or ""
            worker.stderr_log = stderr or ""
            worker.exit_code = process.returncode
            worker.last_heartbeat = datetime.now().isoformat()

            if process.returncode == 0:
                worker.status = WorkerStatus.COMPLETED
                task.status = TaskStatus.VERIFYING
                task.result = "completed, awaiting verification"
            else:
                worker.status = WorkerStatus.CRASHED
                task.attempt_count += 1
                # Surface the real provider error on BOTH the worker and the
                # task. Previously only the task got a message and the worker
                # stayed None, so classification saw no reason at all and every
                # failure degraded to UNKNOWN.
                detail = summarize_worker_error(stderr or stdout or "")
                worker.failure_reason = detail
                task.failure_reason = f"Worker exited {process.returncode}: {detail}"
                task.status = TaskStatus.FAILED

            state_manager.update_worker(worker)
            state_manager.update_task(task)

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            worker.status = WorkerStatus.TIMEOUT
            worker.stdout_log = stdout or ""
            worker.stderr_log = stderr or ""
            task.attempt_count += 1
            task.failure_reason = f"Worker timeout after {self.worker_timeout}s"
            task.status = TaskStatus.FAILED
            state_manager.update_worker(worker)
            state_manager.update_task(task)
        except Exception as e:
            worker.status = WorkerStatus.CRASHED
            worker.failure_reason = str(e)
            task.attempt_count += 1
            task.failure_reason = f"Monitor error: {e}"
            task.status = TaskStatus.FAILED
            state_manager.update_worker(worker)
            state_manager.update_task(task)
        finally:
            self.processes.pop(worker.worker_id, None)
            # Always free the file scope: a leaked lock would block the queue
            # until expiry even though no worker is using those paths.
            self.release_paths_for(worker.worker_id)

    def terminate_worker(self, worker_id: str, graceful: bool = True) -> bool:
        process = self.processes.get(worker_id)
        worker = state_manager.get_worker(worker_id)
        if not process:
            self.release_paths_for(worker_id)
            return False

        if worker:
            worker.status = WorkerStatus.TERMINATED
            state_manager.update_worker(worker)

        if graceful:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        else:
            process.kill()
            process.wait(timeout=5)

        self.processes.pop(worker_id, None)
        self.release_paths_for(worker_id)
        return True

    def check_worker_health(self) -> dict[str, Any]:
        health = {}

        # 1. Workers launched and tracked by this manager
        for worker_id, process in self.processes.items():
            worker = state_manager.get_worker(worker_id)
            if not worker:
                continue

            now = datetime.now()
            last_hb = datetime.fromisoformat(worker.last_heartbeat)
            elapsed = (now - last_hb).total_seconds()

            health[worker_id] = {
                "status": worker.status.value,
                "process_alive": process.poll() is None,
                "elapsed_since_heartbeat": elapsed,
                "task_id": worker.task_id,
            }

        # 2. Orphaned workers in state (RUNNING/STARTING) but not in self.processes
        for worker in self.state.workers.values():
            if worker.status.value not in ["running", "starting"]:
                continue
            if worker.worker_id in self.processes:
                continue  # already checked above

            # Check if process is alive AND is the one we launched (PID + create_time).
            process_alive = is_expected_process(worker.process_id, worker.process_create_time)

            now = datetime.now()
            last_hb = datetime.fromisoformat(worker.last_heartbeat)
            elapsed = (now - last_hb).total_seconds()

            health[worker.worker_id] = {
                "status": worker.status.value,
                "process_alive": process_alive,
                "elapsed_since_heartbeat": elapsed,
                "task_id": worker.task_id,
                "orphaned": True,
            }

        return health

    def get_available_workers(self) -> list[Worker]:
        return [
            w
            for w in self.state.workers.values()
            if w.status in [WorkerStatus.IDLE, WorkerStatus.UNAVAILABLE] or w.task_id is None
        ]

    def get_running_workers(self) -> list[Worker]:
        return [
            w
            for w in self.state.workers.values()
            if w.status in [WorkerStatus.STARTING, WorkerStatus.RUNNING, WorkerStatus.ALIVE]
        ]

    def replace_worker(self, old_worker_id: str, new_worker: Worker, task: Task, model: str = "auto") -> bool:
        self.terminate_worker(old_worker_id, graceful=True)
        time.sleep(1)
        return self.launch_worker(new_worker, task, model)

    def create_worker(self, worker_id: str, model: str = "auto") -> Worker:
        worker = Worker(
            worker_id=worker_id,
            model=model,
            working_directory=str(REPO_ROOT),
        )
        state_manager.add_worker(worker)
        return worker

    def isolate_worker(self, worker: Worker, task: Task) -> bool:
        """Move a worker into its own worktree before it writes anything.

        Opt-in via FINISHER_WORKTREE_ISOLATION=1. Off by default because a
        worktree is a real branch: merging the result back is a human decision.
        """
        if os.environ.get("FINISHER_WORKTREE_ISOLATION", "0") != "1":
            return False
        if not task.files:
            # Unbounded task: isolation would hide everything it touches.
            return False

        info = worktree_manager.create(task.id)
        if not info.created or not info.path:
            worker.failure_reason = f"worktree unavailable: {info.reason}"
            state_manager.update_worker(worker)
            return False

        worker.working_directory = info.path
        worker.worktree_path = info.path
        worker.branch = info.branch
        state_manager.update_worker(worker)
        return True

    def shutdown_all(self) -> None:
        for worker_id in list(self.processes.keys()):
            self.terminate_worker(worker_id, graceful=True)
        # Nothing is running any more: every lock is stale by definition.
        for lock_id in list(self.state.locks.keys()):
            self.state.locks.pop(lock_id, None)
        state_manager.save()

    def reap_orphan_processes(self) -> list[int]:
        """Kill only processes FINISHER itself launched and still tracks.

        Never matches by process name: an unrelated `opencode` belonging to the
        user must not be touched (megaprompt §7).
        """
        reaped: list[int] = []
        for worker_id, process in list(self.processes.items()):
            if process.poll() is None:
                continue
            reaped.append(process.pid)
            self.processes.pop(worker_id, None)
            self.release_paths_for(worker_id)
        return reaped


worker_manager = WorkerManager(state_manager.get_state())
