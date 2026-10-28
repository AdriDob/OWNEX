"""Checkpoint and recovery for OWNEX Finisher."""

from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.finisher.events import log_event
from scripts.finisher.state import (
    FINISHER_STATE_DIR,
    REPO_ROOT,
    Checkpoint,
    FinisherState,
    Task,
    TaskStatus,
    state_manager,
)
from scripts.finisher.worker import worker_manager

BASE_RETRY_DELAY_SECONDS = 30
MAX_RETRY_DELAY_SECONDS = 900


class CheckpointManager:
    def __init__(self, state: FinisherState):
        self.state = state
        self.checkpoint_dir = Path(FINISHER_STATE_DIR) / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(
        self,
        task_id: str | None = None,
        worker_id: str | None = None,
        task_progress: float = 0.0,
        failures: list[str] | None = None,
        next_action: str = "",
    ) -> Checkpoint:
        git_commit = self._get_git_commit()
        modified_files = self._get_modified_files()
        verification_status = self._get_verification_status()
        worker_state = self._get_worker_state(worker_id)
        model = self._get_current_model()

        checkpoint = Checkpoint(
            checkpoint_id=f"cp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            worker_id=worker_id,
            git_commit=git_commit,
            modified_files=modified_files,
            verification_status=verification_status,
            worker_state=worker_state,
            model=model,
            task_progress=task_progress,
            failures=failures or [],
            next_action=next_action,
        )

        self.state.checkpoints.append(checkpoint)
        self._save_checkpoint(checkpoint)
        state_manager.save()

        return checkpoint

    def _get_git_commit(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _get_modified_files(self) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                files = []
                for line in result.stdout.strip().split("\n"):
                    if line:
                        files.append(line[3:].strip())
                return files
        except Exception:
            pass
        return []

    def _get_verification_status(self) -> str:
        return "pending"

    def _get_worker_state(self, worker_id: str | None) -> dict[str, Any]:
        if worker_id:
            worker = state_manager.get_worker(worker_id)
            if worker:
                return worker.to_dict()
        return {}

    def _get_current_model(self) -> str:
        return "auto"

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        filepath = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        with open(filepath, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

    def load_latest_checkpoint(self) -> Checkpoint | None:
        checkpoints = list(self.checkpoint_dir.glob("*.json"))
        if not checkpoints:
            return None
        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest) as f:
                data = json.load(f)
            return Checkpoint(**data)
        except Exception:
            return None

    def inspect_restore(self, checkpoint: Checkpoint) -> dict[str, Any]:
        """Report what a restore WOULD do. Never mutates. Safe to call autonomously."""
        head = self._get_git_commit()
        dirty = self._get_modified_files()
        target = checkpoint.git_commit
        diverged = bool(head and target and head != target)
        return {
            "checkpoint_id": checkpoint.checkpoint_id,
            "current_commit": head,
            "target_commit": target,
            "would_diverge_history": diverged,
            "uncommitted_files_lost": len(dirty),
            "uncommitted_files": dirty,
            "destructive": bool(checkpoint.git_commit and diverged) or bool(dirty),
            "task_id": checkpoint.task_id,
        }

    def restore_from_checkpoint(self, checkpoint: Checkpoint, destructive_allowed: bool = False) -> bool:
        """Restore TASK state only.

        Constitutional rule 5: never reset/clean the shared working tree
        automatically. Uncommitted user work is never touched. Git history is
        never rewritten. `destructive_allowed` only governs resetting tasks.
        """
        try:
            report = self.inspect_restore(checkpoint)
            if report["destructive"] and not destructive_allowed:
                print(
                    f"[SAFETY] Restore of {checkpoint.checkpoint_id} would touch "
                    f"{report['uncommitted_files_lost']} uncommitted file(s); "
                    "refusing destructive repo mutation. Task state not restored."
                )
                return False

            if checkpoint.task_id:
                task = self.state.tasks.get(checkpoint.task_id)
                if task:
                    task.status = TaskStatus.PENDING
                    task.checkpoint = checkpoint.checkpoint_id
                    task.result = f"restored from {checkpoint.checkpoint_id}"
                    state_manager.update_task(task)

            state_manager.save()
            return True
        except Exception as e:
            print(f"Failed to restore checkpoint: {e}")
            return False


PROVIDER_LIMIT = "PROVIDER_LIMIT"
PROCESS_EXITED = "PROCESS_EXITED"
MODEL_ERROR = "MODEL_ERROR"
TOOL_ERROR = "TOOL_ERROR"
ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
FILE_CONFLICT = "FILE_CONFLICT"
TEST_FAILURE = "TEST_FAILURE"
HUMAN_REQUIRED = "HUMAN_REQUIRED"
UNKNOWN = "UNKNOWN"


class RecoveryEngine:
    def __init__(self, state: FinisherState, checkpoint_manager: CheckpointManager):
        self.state = state
        self.checkpoint_manager = checkpoint_manager
        self.max_recovery_attempts = 3

    def classify_failure(self, task: Task) -> str:
        return self.classify_text(task.failure_reason or "")

    def classify_text(self, failure_reason: str) -> str:
        """Classify from real evidence.

        Order matters: a provider outage looks like a timeout to naive
        keyword matching, and misclassifying it causes pointless retries of
        the same broken path.

        Pure-digit codes ("429", "402", "503") require token boundaries:
        a stack-trace line number like `writable:402:23` must not read as
        HTTP 402 (live incident: an EPIPE crash was escalated as a provider
        billing limit, stalling the task on a human gate for no reason).
        """

        def has(code: str) -> bool:
            return re.search(rf"(?<![\w:]){code}(?![\w:])", reason) is not None

        reason = (failure_reason or "").lower()
        if not reason:
            return UNKNOWN

        if (
            any(
                w in reason
                for w in (
                    "rate limit",
                    "ratelimit",
                    "quota",
                    "too many requests",
                    "insufficient_quota",
                    "limit reached",
                )
            )
            or has("429")
            or has("402")
        ):
            return PROVIDER_LIMIT
        if (
            any(
                w in reason
                for w in ("unknownerror", "unexpected server error", "provider error", "overloaded", "bad gateway")
            )
            or has("503")
            or has("502")
        ):
            return MODEL_ERROR
        if any(
            w in reason
            for w in ("human", "approval", "gate", "credential", "auth", "token", "login", "permission denied")
        ):
            return HUMAN_REQUIRED
        if any(w in reason for w in ("lock conflict", "concurrent", "file conflict", "worktree")):
            return FILE_CONFLICT
        if any(
            w in reason for w in ("verification failed", "assertionerror", "tests failed", "test failed", "expected")
        ):
            return TEST_FAILURE
        if any(
            w in reason
            for w in (
                "tool",
                "mcp",
                "permission",
                "not found",
                "missing",
                "no such file",
                "modulenotfound",
                "importerror",
            )
        ):
            return TOOL_ERROR
        if any(
            w in reason for w in ("timeout", "timed out", "connection", "network", "temporary", "dns", "reset by peer")
        ):
            return ENVIRONMENT_ERROR
        if any(w in reason for w in ("syntax", "type", "logic", "runtime")):
            return MODEL_ERROR
        if any(w in reason for w in ("exited", "killed", "signal", "code ", "epipe", "broken pipe")):
            return PROCESS_EXITED
        if any(w in reason for w in ("env", "variable", "config", "path")):
            return ENVIRONMENT_ERROR
        return UNKNOWN

    def get_recovery_strategy(self, failure_type: str, task: Task) -> list[str]:
        strategies = {
            PROVIDER_LIMIT: ["request_human"],
            MODEL_ERROR: ["change_model", "retry", "request_human"],
            PROCESS_EXITED: ["restart_worker", "change_model", "retry", "request_human"],
            TOOL_ERROR: ["restart_worker", "request_human"],
            ENVIRONMENT_ERROR: ["retry", "restart_worker", "request_human"],
            FILE_CONFLICT: ["request_human"],
            TEST_FAILURE: ["split_task", "change_model", "retry", "request_human"],
            HUMAN_REQUIRED: ["request_human"],
            UNKNOWN: ["change_model", "retry", "request_human"],
        }
        return strategies.get(failure_type, ["retry", "request_human"])

    def execute_recovery(self, task: Task, failure_type: str) -> bool:
        if task.attempt_count >= task.max_attempts:
            task.status = TaskStatus.BLOCKED
            task.failure_reason = f"Max attempts ({task.max_attempts}) reached. Failure: {failure_type}"
            state_manager.update_task(task)
            # A blocked task with no gate is invisible to the operator.
            # Overnight mode depends on gates for the morning report (§12, §22).
            # set_waiting=False: the task stays BLOCKED (exhausted, not
            # awaiting retry), the gate is purely for visibility/escalation.
            self._request_human_gate(task, f"blocked_{failure_type}", set_waiting=False)
            log_event(
                "task.blocked",
                f"Task {task.id} BLOCKED after {task.max_attempts} attempts ({failure_type})",
                task_id=task.id,
                data={"failure_type": failure_type},
            )
            return False

        strategies = self.get_recovery_strategy(failure_type, task)

        for strategy in strategies:
            if strategy == "retry":
                return self._retry_task(task)
            elif strategy == "restart_worker":
                return self._restart_worker(task)
            elif strategy == "change_model":
                return self._change_model(task)
            elif strategy == "split_task":
                return self._split_task(task)
            elif strategy == "change_worker":
                return self._change_worker(task)
            elif strategy == "reduce_concurrency":
                return self._reduce_concurrency(task)
            elif strategy == "request_human":
                return self._request_human_gate(task, failure_type)

        return False

    def _retry_task(self, task: Task) -> bool:
        task.attempt_count += 1
        task.status = TaskStatus.READY
        # Exponential backoff. A dry run burned every attempt in seconds while
        # the provider was failing, turning recovery into a crash-loop
        # (§17: avoid restart storms).
        delay = min(BASE_RETRY_DELAY_SECONDS * (2 ** max(0, task.attempt_count - 1)), MAX_RETRY_DELAY_SECONDS)
        task.next_attempt_after = time.time() + delay
        task.failure_reason = None
        state_manager.update_task(task)
        print(f"    retry {task.id} in {delay:.0f}s (attempt {task.attempt_count}/{task.max_attempts})")
        log_event(
            "task.retry",
            f"Task {task.id} requeued with backoff",
            task_id=task.id,
            data={"attempt": task.attempt_count, "delay_s": round(delay)},
        )
        return True

    def _restart_worker(self, task: Task) -> bool:
        if task.assigned_worker:
            old_worker = state_manager.get_worker(task.assigned_worker)
            if old_worker:
                new_worker_id = f"{task.assigned_worker}_retry_{task.attempt_count}"
                new_worker = state_manager.get_state().workers.get(new_worker_id)
                if not new_worker:
                    new_worker = worker_manager.create_worker(new_worker_id, old_worker.model)
                replaced = worker_manager.replace_worker(task.assigned_worker, new_worker, task, old_worker.model)
                if replaced:
                    log_event(
                        "worker.replaced",
                        f"Worker {task.assigned_worker} replaced by {new_worker_id}",
                        task_id=task.id,
                        worker_id=new_worker_id,
                    )
                return replaced
        return self._retry_task(task)

    def _change_model(self, task: Task) -> bool:
        """Rotate to a different DISCOVERED free model.

        The previous implementation cycled a hardcoded list containing models
        that no longer exist, so "change model" silently retried the same dead
        provider instead of escaping the failure.
        """
        from scripts.finisher.model_router import model_router

        free = [m.id for m in model_router.free_models()]
        if not free:
            return self._retry_task(task)

        current = None
        if task.assigned_worker:
            worker = state_manager.get_worker(task.assigned_worker)
            if worker:
                current = worker.model

        alternatives = [m for m in free if m != current]
        if not alternatives:
            return self._retry_task(task)

        if task.assigned_worker:
            worker = state_manager.get_worker(task.assigned_worker)
            if worker:
                worker.model = alternatives[0]
                state_manager.update_worker(worker)
        return self._restart_worker(task)

    def _split_task(self, task: Task) -> bool:
        task.description += f"\n\n[SPLIT ATTEMPT {task.attempt_count}] Focus on smaller scope."
        task.weight = max(0.5, task.weight * 0.7)
        return self._retry_task(task)

    def _change_worker(self, task: Task) -> bool:
        return self._restart_worker(task)

    def _reduce_concurrency(self, task: Task) -> bool:
        return self._retry_task(task)

    def _request_human_gate(self, task: Task, failure_type: str, set_waiting: bool = True) -> bool:
        gate_id = f"gate_{task.id}_recovery_{failure_type}"
        if gate_id in self.state.human_gates:
            return False
        gate_info = {
            "type": "recovery",
            "task_id": task.id,
            "failure_type": failure_type,
            "failure_reason": task.failure_reason,
            "attempt": task.attempt_count,
            "created_at": datetime.now().isoformat(),
            "decision": None,
        }
        state_manager.add_human_gate(gate_id, gate_info)
        log_event(
            "gate.required",
            f"Human gate {gate_id} opened for {task.id} ({failure_type})",
            task_id=task.id,
            data={"gate_id": gate_id, "failure_type": failure_type},
        )
        if set_waiting:
            task.status = TaskStatus.WAITING_HUMAN
            state_manager.update_task(task)
        return False


checkpoint_manager = CheckpointManager(state_manager.get_state())
recovery_engine = RecoveryEngine(state_manager.get_state(), checkpoint_manager)
