#!/usr/bin/env python3
"""OWNEX Finisher CLI — Autonomous Project Completion System."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from typing import Any

from scripts.finisher.checkpoint import checkpoint_manager, recovery_engine
from scripts.finisher.events import log_event
from scripts.finisher.model_router import model_router
from scripts.finisher.state import (
    FINISHER_STATE_DIR,
    REPO_ROOT,
    ProjectStatus,
    Task,
    TaskStatus,
    WorkerStatus,
    state_manager,
)
from scripts.finisher.task_queue import TaskQueue
from scripts.finisher.verification import verification_engine
from scripts.finisher.worker import worker_manager
from scripts.finisher.worktree import worktree_manager

TERMINAL_WORKER_STATES = frozenset({"completed", "crashed", "timeout", "terminated", "unavailable"})
NON_TERMINAL_WORKER_STATES = frozenset({"running", "starting", "alive"})

DEFAULT_OVERNIGHT_SECONDS = 8 * 3600

# Failure types that must NEVER be auto-retried by the overnight stall
# handler: retrying them is either pointless (provider down, human needed,
# paths still locked) or unsafe. They wait for the morning report instead.
NON_RETRYABLE_OVERNIGHT = frozenset({"PROVIDER_LIMIT", "HUMAN_REQUIRED", "FILE_CONFLICT"})


@dataclasses.dataclass
class OvernightConfig:
    max_duration_seconds: float = DEFAULT_OVERNIGHT_SECONDS
    max_tasks: int = 0  # 0 = unlimited

    @classmethod
    def from_env(cls) -> OvernightConfig:
        try:
            duration = float(os.environ.get("FINISHER_MAX_DURATION", str(DEFAULT_OVERNIGHT_SECONDS)))
        except ValueError:
            duration = float(DEFAULT_OVERNIGHT_SECONDS)
        try:
            tasks = int(os.environ.get("FINISHER_MAX_TASKS", "0"))
        except ValueError:
            tasks = 0
        return cls(max_duration_seconds=max(60.0, duration), max_tasks=max(0, tasks))

    @classmethod
    def from_args(cls, max_duration: float | None, max_tasks: int | None) -> OvernightConfig:
        """Create config from CLI args. 0 = unlimited."""
        duration = DEFAULT_OVERNIGHT_SECONDS
        tasks = 0
        if max_duration is not None:
            duration = max(60.0, max_duration)
        if max_tasks is not None:
            tasks = max(0, max_tasks)
        return cls(max_duration_seconds=duration, max_tasks=tasks)

    def merge_env(self) -> OvernightConfig:
        """Merge with environment variables (env takes precedence over CLI defaults)."""
        try:
            env_duration = float(os.environ.get("FINISHER_MAX_DURATION", str(self.max_duration_seconds)))
        except ValueError:
            env_duration = self.max_duration_seconds
        try:
            env_tasks = int(os.environ.get("FINISHER_MAX_TASKS", str(self.max_tasks)))
        except ValueError:
            env_tasks = self.max_tasks
        # Env takes precedence over CLI args
        return OvernightConfig(
            max_duration_seconds=max(60.0, env_duration),
            max_tasks=max(0, env_tasks),
        )


class FinisherDaemon:
    def __init__(self, acquire_lock: bool = False):
        self.state = state_manager.get_state()
        self.queue = TaskQueue(self.state)
        self.running = False
        self.overnight_mode = False
        self.check_interval = 10
        self.stop_requested = False
        self.started_at = datetime.now()
        self._holds_lock = False
        self.overnight_config = OvernightConfig.from_env()
        self._run_monotonic_start = 0.0
        self.run_tasks_launched = 0
        self._limits_explicit = False  # True if limits were explicitly set (CLI or env)
        if acquire_lock:
            state_manager.acquire_instance_lock()
            self._holds_lock = True

    def start(self, overnight: bool = False, max_duration: float | None = None, max_tasks: int | None = None) -> int:
        # Determine if limits are explicitly set (CLI args or env vars override defaults)
        limits_from_cli = max_duration is not None or max_tasks is not None
        limits_from_env = "FINISHER_MAX_DURATION" in os.environ or "FINISHER_MAX_TASKS" in os.environ
        self._limits_explicit = limits_from_cli or limits_from_env

        self.overnight_mode = overnight
        if max_duration is not None:
            self.overnight_config.max_duration_seconds = max(60.0, max_duration)
        if max_tasks is not None:
            self.overnight_config.max_tasks = max(0, max_tasks)

        # Merge env vars (they take precedence over CLI args per spec)
        self.overnight_config = self.overnight_config.merge_env()

        self.state.project_status = ProjectStatus.RUNNING
        state_manager.save()

        recovered = state_manager.recover_interrupted_tasks()
        if recovered:
            print(f"Boot recovery: {len(recovered)} interrupted task(s) requeued: {', '.join(recovered)}")

        print("OWNEX Finisher v0.2.0 starting...")
        print(f"Overnight mode: {overnight}")
        print(
            f"Limits: max_duration={self.overnight_config.max_duration_seconds:.0f}s "
            f"max_tasks={'unlimited' if not self.overnight_config.max_tasks else self.overnight_config.max_tasks}"
        )
        print(f"Explicit limits: {self._limits_explicit}")
        print(f"State dir: {FINISHER_STATE_DIR}")
        (FINISHER_STATE_DIR / "finisher.pid").write_text(str(os.getpid()))
        log_event("run.started", f"Daemon started (overnight={overnight})", data={"overnight": overnight})

        self._load_default_tasks()
        self._run_monotonic_start = time.monotonic()

        signal.signal(signal.SIGTERM, self._on_stop_signal)
        try:
            asyncio.run(self._main_loop())
        except KeyboardInterrupt:
            print("\nShutdown requested...")
        finally:
            self.shutdown()

        return 0

    def _limits_engaged(self) -> bool:
        """True if limits should be enforced (explicit limits OR overnight mode)."""
        return self.overnight_mode or self._limits_explicit

    def past_deadline(self) -> bool:
        """True when the run exceeded its duration budget, in ANY mode.

        There is intentionally no way to disable the deadline: unbounded
        autonomy is exactly what §13 forbids. Day runs obey the same budget
        as overnight runs (previously only overnight was bounded, so a plain
        `start` could run forever: the blocking defect).
        """
        if not self._run_monotonic_start:
            return False
        if not self._limits_engaged():
            return False
        return (time.monotonic() - self._run_monotonic_start) >= self.overnight_config.max_duration_seconds

    def task_budget_exhausted(self) -> bool:
        limit = self.overnight_config.max_tasks
        return bool(self._limits_engaged() and limit and self.run_tasks_launched >= limit)

    def _on_stop_signal(self, signum: int, frame: Any) -> None:
        print(f"\nReceived signal {signum}; finishing current task then stopping...")
        self.stop_requested = True
        self.running = False

    def _load_default_tasks(self) -> None:
        """Seed the queue only on explicit request.

        A daemon that finds an empty state used to auto-inject five tasks that
        operate on the real repository. An orphaned instance with a wiped state
        therefore began auditing/modifying live work unprompted. An empty state
        now means an empty queue.
        """
        if self.state.tasks:
            return
        if os.environ.get("FINISHER_SEED_DEFAULTS", "0") != "1":
            print("No tasks queued. Add tasks explicitly (or set FINISHER_SEED_DEFAULTS=1).")
            return

        default_tasks = [
            Task(
                id="TASK-001",
                title="Audit OWNEX repository state",
                description="Scan repository for current state, tests, architecture, blockers",
                phase="audit",
                priority=1,
                area="architecture",
                weight=2.0,
                verification_commands=[
                    "python -m pytest --timeout=30 -q tests/test_scoring.py",
                    "python -m ruff check .",
                    "python -m mypy cores/opportunity/scoring.py cores/scheduler/scheduler.py cores/scheduler/jobs.py",
                ],
                acceptance_criteria=[],
            ),
            Task(
                id="TASK-002",
                title="Verify test baseline",
                description="Run test-fast to confirm 103/1 baseline intact",
                phase="audit",
                priority=1,
                area="testing",
                weight=2.0,
                verification_commands=[
                    "python scripts/dev test-fast",
                ],
                acceptance_criteria=[],
            ),
            Task(
                id="TASK-003",
                title="Check for critical blockers",
                description="Identify any blockers preventing progress",
                phase="audit",
                priority=1,
                area="core_functionality",
                weight=1.5,
                verification_commands=[
                    "git status --short",
                    "python -c \"import scripts.finisher.state; s=scripts.finisher.state.state_manager.get_state(); print('Tasks:', len(s.tasks))\"",
                ],
                acceptance_criteria=[],
            ),
            Task(
                id="TASK-004",
                title="Implement core functionality fix",
                description="Address any critical functionality gaps found in audit",
                phase="implement",
                priority=2,
                area="core_functionality",
                weight=3.0,
                dependencies=["TASK-001", "TASK-002", "TASK-003"],
                verification_commands=[
                    "python scripts/dev check",
                ],
                acceptance_criteria=[],
            ),
            Task(
                id="TASK-005",
                title="Run full regression verification",
                description="Complete verification suite to confirm no regressions",
                phase="verify",
                priority=2,
                area="testing",
                weight=2.5,
                dependencies=["TASK-004"],
                verification_commands=[
                    "python scripts/dev check",
                    "python -m pytest --timeout=60 -q tests/test_scoring.py tests/test_opportunity_engine.py",
                ],
                acceptance_criteria=[],
            ),
        ]

        for task in default_tasks:
            self.state.tasks[task.id] = task
            self.queue = TaskQueue(self.state)

        state_manager.save()
        print(f"Loaded {len(default_tasks)} default tasks")

    async def _main_loop(self) -> None:
        self.running = True
        consecutive_failures = 0
        max_consecutive_failures = 5

        while self.running and not self.stop_requested:
            if self.state.project_status == ProjectStatus.PAUSED:
                print("  Paused. Waiting for `resume`.")
                await asyncio.sleep(self.check_interval)
                continue

            try:
                await self._tick()
                consecutive_failures = 0
            except Exception as e:
                consecutive_failures += 1
                print(f"Error in main loop ({consecutive_failures}/{max_consecutive_failures}): {e}")
                if consecutive_failures >= max_consecutive_failures:
                    print("Too many consecutive failures, entering recovery mode...")
                    self.state.project_status = ProjectStatus.RECOVERING
                    state_manager.save()
                    await self._recovery_mode()
                    consecutive_failures = 0

            await asyncio.sleep(self.check_interval)

    async def _tick(self) -> None:
        if self.stop_requested or self.state.project_status == ProjectStatus.STOPPED:
            self.running = False
            return

        # Adopt operator changes (approve / pause / resume / task edits) made
        # through the CLI while the daemon runs. Without this, Human Gates
        # only take effect after a restart.
        state_manager.reload()

        # Deadline: stop launching NEW work, drain what runs, then
        # exit. In-flight tasks finish within their own worker timeout; the
        # loop below stops as soon as nothing is running. Applies in every
        # mode (day runs obey the same budget as overnight runs).
        if self.past_deadline():
            running = self.queue.get_running_tasks()
            verifying = self.queue.get_verification_pending_tasks()
            if not running and not verifying:
                print("\n*** DEADLINE REACHED — stopping cleanly ***")
                log_event("run.deadline", "Duration budget reached; draining done, stopping")
                self.running = False
                return

            # BOUNDED DRAIN: allow grace period for in-flight tasks, then force termination
            print(f"  [deadline passed; draining {len(running)} running / {len(verifying)} verifying, no new tasks]")
            self._print_status()

            # Grace period for in-flight tasks (bounded by worker_timeout)
            grace_seconds = getattr(worker_manager, "worker_timeout", 300)
            drain_deadline = time.monotonic() + grace_seconds

            while time.monotonic() < drain_deadline:
                running = self.queue.get_running_tasks()
                if not running:
                    break
                # Check if any workers have finished
                running_still = [t for t in running if t.status in (TaskStatus.RUNNING, TaskStatus.VERIFYING)]
                if not running_still:
                    break
                await asyncio.sleep(5)

            # Grace period expired: forcefully terminate remaining workers
            running = self.queue.get_running_tasks()
            if running:
                print(f"  [grace expired; terminating {len(running)} remaining workers]")
                for task in running:
                    if task.assigned_worker:
                        worker_manager.terminate_worker(task.assigned_worker, graceful=False)
                        task.status = TaskStatus.FAILED
                        task.failure_reason = "Terminated due to deadline (drain timeout)"
                        state_manager.update_task(task)

            # Verify no orphans
            worker_manager.reap_orphan_processes()
            running = self.queue.get_running_tasks()
            if running:
                print(f"  [WARNING: {len(running)} tasks still running after forced termination]")

            # Persist final state and stop
            log_event("run.deadline", "Duration budget reached; draining done, stopping")
            self.running = False
            return

        if self.task_budget_exhausted():
            print(f"  [task budget reached ({self.run_tasks_launched}); no new tasks]")
            self._print_status()
            return

        self._check_worker_health()
        self._check_human_gates()

        # Constitutional rule 16: a pending human gate stops ONLY the affected
        # task. Independent tasks must keep running. We report the gate and
        # continue; the gate itself already marked its task WAITING_HUMAN.
        if self.state.project_status == ProjectStatus.WAITING_HUMAN:
            print(f"  [{len(self.pending_gate_ids())} human gate(s) pending — continuing independent tasks]")

        next_task = self.queue.get_next_best_task()
        if next_task:
            await self._execute_task(next_task)
        else:
            running = self.queue.get_running_tasks()
            verifying = self.queue.get_verification_pending_tasks()

            if not running and not verifying:
                progress = self.queue.calculate_progress()
                if progress["overall"] >= 100:
                    print("\n*** PROJECT COMPLETE ***")
                    self.state.project_status = ProjectStatus.COMPLETED
                    state_manager.save()
                    self.running = False
                else:
                    print(f"No ready tasks. Progress: {progress['overall']:.1f}%")
                    if self.overnight_mode:
                        await self._handle_overnight_stall()

        self._print_status()

    async def _await_worker(self, worker_id: str, task: Task) -> Any:
        """Block until the worker reaches a terminal state or the task deadline.

        The previous loop keyed only on `processes` membership, which the
        monitor pops in a `finally` block — so a worker could vanish from the
        map while still RUNNING, silently mis-classifying a live task as failed.
        """
        deadline = time.monotonic() + getattr(worker_manager, "worker_timeout", 300) + 30
        last_status = None
        while time.monotonic() < deadline:
            await asyncio.sleep(2)
            worker = state_manager.get_worker(worker_id)
            if worker is None:
                return None
            if worker.status in TERMINAL_WORKER_STATES:
                return worker
            if worker.status != last_status:
                last_status = worker.status
                print(f"    worker {worker_id}: {worker.status} ({worker.exit_code})")
            # Honour stop signals here, not just between ticks. Without this a
            # SIGTERM during a long task was ignored until the worker
            # deadline expired, leaving an orphaned daemon for up to 30 min.
            if self.stop_requested or self.state.project_status in (
                ProjectStatus.STOPPED,
                ProjectStatus.PAUSED,
            ):
                print(f"    Stop requested — terminating worker {worker_id}")
                worker_manager.terminate_worker(worker_id, graceful=True)
                if worker.failure_reason is None:
                    worker.failure_reason = "terminated on stop request"
                    state_manager.update_worker(worker)
                return worker

        worker = state_manager.get_worker(worker_id)
        if worker:
            worker_manager.terminate_worker(worker_id, graceful=True)
            worker.status = WorkerStatus.TIMEOUT
            worker.failure_reason = f"Task deadline exceeded ({getattr(worker_manager, 'worker_timeout', 300)}s)"
            log_event(
                "worker.timeout", f"Worker {worker_id} exceeded task deadline", task_id=task.id, worker_id=worker_id
            )
            state_manager.update_worker(worker)
        return worker

    async def _execute_task(self, task: Task) -> None:
        if task.attempt_count >= task.max_attempts:
            task.status = TaskStatus.BLOCKED
            task.failure_reason = f"Max attempts ({task.max_attempts}) reached"
            state_manager.update_task(task)
            return

        print(f"\n>>> Executing: {task.id} - {task.title}")

        checkpoint_manager.create_checkpoint(
            task_id=task.id,
            task_progress=0.0,
            next_action=f"execute {task.id}",
        )

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        state_manager.update_task(task)

        model = model_router.get_model_for_task(task)
        if model is None:
            # §9: never invent a fallback, never auto-select a paid model.
            # Pause this task and keep running independent ones.
            if task.status != TaskStatus.WAITING_HUMAN:
                task.status = TaskStatus.WAITING_HUMAN
                task.failure_reason = f"No suitable free model discovered ({model_router.last_error})"
                state_manager.update_task(task)
                gate_id = f"gate_{task.id}_no_model"
                if gate_id not in self.state.human_gates:
                    self.state.human_gates[gate_id] = {
                        "type": "model_unavailable",
                        "task_id": task.id,
                        "failure_reason": task.failure_reason,
                        "created_at": datetime.now().isoformat(),
                        "decision": None,
                    }
                    state_manager.save()
                    log_event("gate.required", f"No free model for {task.id}; task paused", task_id=task.id)
            print(f"    PAUSED {task.id}: no free model available ({model_router.last_error})")
            return
        print(f"    Model: {model}")

        worker_id = f"worker_{task.id}_{task.attempt_count}"
        worker = worker_manager.create_worker(worker_id, model)

        success = worker_manager.launch_worker(worker, task, model)
        if not success:
            task.status = TaskStatus.FAILED
            task.failure_reason = "Failed to launch worker"
            log_event("task.failed", f"Task {task.id}: worker failed to launch", task_id=task.id)
            state_manager.update_task(task)
            return

        task.assigned_worker = worker_id
        state_manager.update_task(task)
        self.run_tasks_launched += 1
        log_event(
            "task.launched",
            f"Task {task.id} launched on {worker_id} ({model})",
            task_id=task.id,
            worker_id=worker_id,
            data={"model": model},
        )

        worker = await self._await_worker(worker_id, task)
        if worker is None:
            print(f"    ✗ {task.id} FAILED: Worker disappeared")
            await self._handle_task_failure(task, "Worker disappeared")
            return

        # Verification is the arbiter, not the exit code. A worker can do the
        # work and then die tearing down (live incident: opencode EPIPE after
        # writing the file and printing VERIFIED), and a clean exit proves
        # nothing on its own. So every terminal worker with acceptance
        # criteria gets verified; only a worker that produced nothing skips
        # straight to failure handling.
        if worker.status == WorkerStatus.COMPLETED or task.verification_commands:
            task.status = TaskStatus.VERIFYING
            state_manager.update_task(task)

            print("    Verifying...")
            verified = verification_engine.verify_task_completion(task)

            if verified:
                checkpoint_manager.create_checkpoint(
                    task_id=task.id,
                    task_progress=1.0,
                    next_action=f"task {task.id} completed",
                )
                print(f"    ✓ {task.id} PASSED")
                log_event("task.verified", f"Task {task.id} PASSED with evidence", task_id=task.id, worker_id=worker_id)
            elif worker.status != WorkerStatus.COMPLETED and worker.failure_reason:
                # Keep the crash evidence for classification: otherwise the
                # "Verification failed" wrapper hides e.g. an UnknownError and
                # recovery picks the wrong strategy. Classifier order still
                # resolves model/provider faults before test faults.
                combined = f"{worker.failure_reason} | Verification also failed: {(task.failure_reason or '')[:300]}"
                print(f"    ✗ {task.id} FAILED verification")
                await self._handle_task_failure(task, combined, classify_on=worker.failure_reason)
            else:
                print(f"    ✗ {task.id} FAILED verification")
                await self._handle_task_failure(task)
        else:
            failure_reason = worker.failure_reason or "Worker failed without output"
            print(f"    ✗ {task.id} FAILED: {failure_reason}")
            await self._handle_task_failure(task, failure_reason)

    async def _handle_task_failure(
        self, task: Task, failure_reason: str | None = None, classify_on: str | None = None
    ) -> None:
        """Handle a failed task.

        `failure_reason` is stored as the visible record (it may combine the
        crash evidence with the verification outcome). `classify_on` selects
        what the classifier sees: for a crashed worker the crash text must win
        over the "Verification failed" wrapper, or every crash misclassifies
        as TEST_FAILURE and recovery picks the wrong strategy.
        """
        if failure_reason:
            task.failure_reason = failure_reason
        state_manager.update_task(task)

        failure_type = recovery_engine.classify_text(classify_on or task.failure_reason or "")
        print(f"    Failure type: {failure_type}")
        log_event(
            "task.failed",
            f"Task {task.id} failed ({failure_type})",
            task_id=task.id,
            worker_id=task.assigned_worker,
            data={"failure_type": failure_type},
        )

        recovered = recovery_engine.execute_recovery(task, failure_type)
        if not recovered:
            print(f"    Task {task.id} blocked, awaiting human or retry")

    async def _handle_overnight_stall(self) -> None:
        """Retry FAILED tasks that are actually retryable.

        The previous version reset every failed task to READY unconditionally:
        it ignored backoff (retry storm within seconds of a provider outage)
        and retried failures that can never succeed without a human
        (provider limits, missing credentials, locked paths). Those now wait
        for the morning report instead of burning the retry budget all night.
        """
        print("    Overnight: no ready tasks, checking for recoverable failures...")
        now = time.time()
        for task in self.queue.get_failed_tasks():
            if task.attempt_count >= task.max_attempts:
                continue
            if task.next_attempt_after and now < task.next_attempt_after:
                continue
            failure_type = recovery_engine.classify_text(task.failure_reason or "")
            if failure_type in NON_RETRYABLE_OVERNIGHT:
                print(f"    Overnight: holding {task.id} ({failure_type}) for operator")
                continue
            print(f"    Overnight: retrying {task.id} (attempt {task.attempt_count + 1})")
            task.status = TaskStatus.READY
            task.failure_reason = None
            state_manager.update_task(task)

    NON_TERMINAL_WORKER_STATES = frozenset({"running", "starting", "alive"})

    def _check_worker_health(self) -> None:
        """Detect dead workers. Orphaned processes are always reaped, and the
        owning task is released for retry rather than left RUNNING forever."""
        health = worker_manager.check_worker_health()
        for worker_id, info in health.items():
            if info["process_alive"] or info["status"] not in NON_TERMINAL_WORKER_STATES:
                continue
            worker = state_manager.get_worker(worker_id)
            if not worker:
                continue
            print(f"    Worker {worker_id} died (status={info['status']}), marking crashed")
            worker.status = WorkerStatus.CRASHED
            worker.failure_reason = worker.failure_reason or "Worker process died"
            state_manager.update_worker(worker)
            log_event(
                "worker.crashed",
                f"Worker {worker_id} died unexpectedly; task released for retry",
                task_id=worker.task_id,
                worker_id=worker_id,
            )

            if worker.task_id:
                task = state_manager.get_task(worker.task_id)
                if task and task.status in (TaskStatus.RUNNING, TaskStatus.VERIFYING):
                    task.attempt_count += 1
                    task.status = TaskStatus.FAILED
                    task.failure_reason = worker.failure_reason
                    state_manager.update_task(task)

    def pending_gate_ids(self) -> list[str]:
        return [gid for gid, g in self.state.human_gates.items() if g.get("decision") is None]

    def _check_human_gates(self) -> None:
        """Track WAITING_HUMAN for reporting only.

        Does NOT halt the scheduler: constitutional rule 16 requires independent
        tasks to continue while a gate is pending.
        """
        pending = self.pending_gate_ids()
        if pending and self.state.project_status != ProjectStatus.WAITING_HUMAN:
            self.state.project_status = ProjectStatus.WAITING_HUMAN
            state_manager.save()

        for gate_id in pending:
            gate = self.state.human_gates[gate_id]
            if not gate.get("notified"):
                gate["notified"] = True
                state_manager.save()
                print(f"\n!!! HUMAN GATE REQUIRED: {gate_id}")
                print(f"    Type: {gate.get('type', 'unknown')}")
                print(f"    Task: {gate.get('task_id', 'unknown')}")
                print(f"    Reason: {gate.get('failure_reason', gate.get('failure_type', 'unknown'))}")
                print(f"    Resolve: ownex-finisher approve {gate_id} | reject {gate_id}")
                print(f"    (independent tasks continue; only {gate.get('task_id')} is blocked)")

        if not pending and self.state.project_status == ProjectStatus.WAITING_HUMAN:
            self.state.project_status = ProjectStatus.RUNNING
            state_manager.save()

    def _print_status(self) -> None:
        progress = self.queue.calculate_progress()
        running = len(self.queue.get_running_tasks())
        print(
            f"  Progress: {progress['overall']:.1f}% | Running: {running} | Implemented: {progress['implemented']:.0f} | Verified: {progress['verified']:.0f} | Blocked: {progress['blocked']:.0f} | Failed: {progress['failed']:.0f} | Remaining: {progress['remaining']:.0f}"
        )

    def shutdown(self) -> None:
        """Controlled shutdown: stop accepting work, terminate managed workers,
        persist state, release the instance lock. Never leaves orphans."""
        self.running = False
        worker_manager.shutdown_all()
        self.state.project_status = ProjectStatus.STOPPED
        state_manager.save()
        if self._holds_lock:
            state_manager.release_instance_lock()
            self._holds_lock = False
        log_event("run.stopped", "Daemon stopped cleanly")
        try:
            self.write_final_report()
        except Exception as e:
            print(f"Warning: final report failed: {e}")
        print("Finisher stopped.")

    async def _recovery_mode(self) -> None:
        """Recover WITHOUT touching the user's working tree.

        The previous implementation called restore_from_checkpoint(), which ran
        `git reset --hard` on the shared repo and destroyed uncommitted work.
        Recovery now only resets retryable TASK state; checkpoints are read-only
        evidence for the operator.
        """
        print("Entering recovery mode...")
        log_event("recovery.mode", "Daemon entered recovery mode after repeated loop failures")
        latest_cp = checkpoint_manager.load_latest_checkpoint()
        if latest_cp:
            report = checkpoint_manager.inspect_restore(latest_cp)
            print(f"Found checkpoint: {latest_cp.checkpoint_id}")
            print(
                f"  commit={report['current_commit']} uncommitted={report['uncommitted_files_lost']} "
                "(repo left untouched)"
            )

        # Release every task left mid-flight by the crash. Restoring only the
        # checkpoint's task would strand the others in RUNNING forever.
        for task in self.state.tasks.values():
            if task.status in (TaskStatus.RUNNING, TaskStatus.VERIFYING):
                if task.attempt_count >= task.max_attempts:
                    task.status = TaskStatus.BLOCKED
                    task.failure_reason = "Interrupted mid-flight; attempts exhausted"
                else:
                    task.status = TaskStatus.READY
                    task.failure_reason = None
                state_manager.update_task(task)
                print(f"  released stuck task {task.id} -> {task.status.value}")

        # Locks outlive the process that took them; reclaim any whose owner is
        # gone, otherwise the whole queue stays blocked until expiry.
        worker_manager.locks.reap_expired()
        for lock_id, lock in list(self.state.locks.items()):
            if worker_manager.locks._owner_is_dead(lock):
                self.state.locks.pop(lock_id, None)
                print(f"  reclaimed orphan lock {lock_id} (owner={lock.get('owner')})")
        state_manager.save()

        failed_tasks = self.queue.get_failed_tasks()
        for task in failed_tasks:
            if task.attempt_count < task.max_attempts:
                task.status = TaskStatus.READY
                task.failure_reason = None
                state_manager.update_task(task)
                print(f"Reset task {task.id} for retry")

        self.state.project_status = ProjectStatus.RUNNING
        state_manager.save()
        print("Recovery complete, resuming normal operation.")

    def status(self) -> dict[str, Any]:
        progress = self.queue.calculate_progress()
        return {
            "project_status": self.state.project_status.value,
            "progress": progress,
            "tasks": {tid: t.to_dict() for tid, t in self.state.tasks.items()},
            "workers": {wid: w.to_dict() for wid, w in self.state.workers.items()},
            "human_gates": self.state.human_gates,
        }

    def build_final_report(self, ended_at: str | None = None) -> dict[str, Any]:
        """Morning report per §22. Derived from persisted state + evidence,
        never from model prose. NOTE: this is the FINISHER's own execution
        report, not OWNEX product completion."""
        progress = self.queue.calculate_progress()
        by_status: dict[str, int] = {}
        attempted: list[str] = []
        models: list[str] = []
        errors: list[dict[str, str]] = []
        verified_tests = 0
        for tid, task in self.state.tasks.items():
            by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
            if task.attempt_count > 0 or task.started_at:
                attempted.append(tid)
            if task.failure_reason:
                errors.append({"task": tid, "reason": task.failure_reason[:300]})
            verified_tests += sum(1 for e in task.evidence if e.get("passed"))
        for worker in self.state.workers.values():
            if worker.model and worker.model not in models:
                models.append(worker.model)
        gates = {g: v for g, v in self.state.human_gates.items() if v.get("decision") is None}
        from scripts.finisher.events import estimate_remaining, evaluate_alerts, read_events

        alerts = evaluate_alerts(self.state)
        remaining = estimate_remaining(self.state)
        recent_events = read_events(limit=20)
        elapsed = (time.monotonic() - self._run_monotonic_start) if self._run_monotonic_start else 0.0
        return {
            "finisher_version": "0.2.0",
            "scope_note": "FINISHER execution progress, NOT verified OWNEX completion",
            "started_at": self.started_at.isoformat(),
            "ended_at": ended_at or datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "overnight_mode": self.overnight_mode,
            "limits": {
                "max_duration_seconds": self.overnight_config.max_duration_seconds,
                "max_tasks": self.overnight_config.max_tasks,
            },
            "tasks_attempted": attempted,
            "tasks_total": len(self.state.tasks),
            "by_status": by_status,
            "progress": progress,
            "models_used": models,
            "workers_total": len(self.state.workers),
            "tasks_launched_this_run": self.run_tasks_launched,
            "verification_commands_passed": verified_tests,
            "checkpoints": len(self.state.checkpoints),
            "errors": errors,
            "pending_gates": gates,
            "alerts": alerts,
            "remaining_estimate": remaining,
            "recent_events": recent_events,
            "next_action": self._recommend_next_action(by_status, gates),
        }

    def _recommend_next_action(self, by_status: dict[str, int], gates: dict[str, Any]) -> str:
        if gates:
            first = next(iter(gates))
            return f"Resolve human gate {first} (task={gates[first].get('task_id')})"
        if by_status.get("failed", 0):
            return "Inspect FAILED tasks; fix root cause or narrow scope, then requeue"
        if by_status.get("blocked", 0):
            return "Review BLOCKED tasks; convert to explicit gates or cancel"
        remaining = by_status.get("pending", 0) + by_status.get("ready", 0)
        if remaining:
            return f"Queue has {remaining} remaining task(s); start next run"
        return "All tasks terminal; declare completion only against verified acceptance criteria"

    def write_final_report(self) -> str:
        reports_dir = FINISHER_STATE_DIR / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        path = reports_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report = self.build_final_report()
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nFinal report written to {path}")
        print(
            f"  attempted={len(report['tasks_attempted'])} verified={report['progress']['verified']} "
            f"blocked={report['progress']['blocked']} failed={report['progress']['failed']}"
        )
        print(f"  pending_gates={len(report['pending_gates'])} next: {report['next_action']}")
        return str(path)


def cmd_start(args: argparse.Namespace) -> int:
    try:
        daemon = FinisherDaemon(acquire_lock=True)
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 2
    return daemon.start(overnight=args.overnight, max_duration=args.max_duration, max_tasks=args.max_tasks)


def cmd_stop(args: argparse.Namespace) -> int:
    """Controlled stop: signal the running daemon to finish and persist."""
    state = state_manager.get_state()
    state.project_status = ProjectStatus.STOPPED
    state_manager.save()
    pid_file = FINISHER_STATE_DIR / "finisher.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            from cores.utils.oscompat import terminate_pid

            result = terminate_pid(pid)
            print(f"Stop signalled to finisher pid {pid} ({result})")
        except ValueError as e:
            print(f"No running daemon signalled: {e}")
    print("Stop requested. Managed workers will be terminated cleanly.")
    return 0


def cmd_pause(args: argparse.Namespace) -> int:
    state = state_manager.get_state()
    if state.project_status in (ProjectStatus.STOPPED, ProjectStatus.COMPLETED):
        print(f"Cannot pause while {state.project_status.value}")
        return 1
    state.project_status = ProjectStatus.PAUSED
    state_manager.save()
    print("Paused. No new tasks will start. Running tasks finish normally.")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    state = state_manager.get_state()
    if state.project_status != ProjectStatus.PAUSED:
        print(f"Not paused (status={state.project_status.value})")
        return 1
    state.project_status = ProjectStatus.RUNNING
    state_manager.save()
    print("Resumed.")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    daemon = FinisherDaemon()
    status = daemon.status()
    progress = status["progress"]
    tasks = status["tasks"]
    by_status: dict[str, int] = {}
    for t in tasks.values():
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1

    print("=" * 66)
    print("OWNEX FINISHER — EXECUTION REPORT")
    print("=" * 66)
    print(f"Project status : {status['project_status']}")
    print(f"Tasks total    : {len(tasks)}")
    print(f"Overall progress: {progress['overall']:.1f}%")
    print(f"  executed     : {progress['implemented']:.0f}")
    print(f"  verified     : {progress['verified']:.0f}")
    print(f"  blocked      : {progress['blocked']:.0f}")
    print(f"  failed       : {progress['failed']:.0f}")
    print(f"  remaining    : {progress['remaining']:.0f}")
    print("\nBy status:")
    for k, v in sorted(by_status.items()):
        print(f"  {k:15} {v}")
    gates = {g: v for g, v in status["human_gates"].items() if v.get("decision") is None}
    print(f"\nPending human gates: {len(gates)}")
    for g, v in gates.items():
        print(f"  {g} (task={v.get('task_id')}, type={v.get('type')})")

    from scripts.finisher.events import estimate_remaining, evaluate_alerts, read_events

    alerts = evaluate_alerts(state_manager.get_state())
    print(f"\nAlerts: {len(alerts)}")
    for a in alerts[:10]:
        print(f"  [{a['severity']}] {a['rule']}: {a['message']}")

    remaining = estimate_remaining(state_manager.get_state())
    print(f"\nRemaining: {remaining.get('remaining_tasks')} task(s), weight {remaining.get('remaining_weight')}")
    if remaining.get("projection_hours") is not None:
        print(f"  projection: ~{remaining['projection_hours']}h ({remaining['projection_basis']})")
    else:
        print(f"  projection withheld ({remaining.get('projection_basis')})")

    print("\nRecent events:")
    for e in read_events(limit=10):
        print(f"  {e.get('ts', '')[:19]} {e.get('type', ''):16} {e.get('message', '')[:90]}")

    locks = state_manager.get_state().locks or {}
    print(f"\nActive file locks: {len(locks)}")
    for lock_id, lock in locks.items():
        print(f"  {lock_id} owner={lock.get('owner')} task={lock.get('task_id')} paths={lock.get('paths')}")

    wts = worktree_manager.finisher_worktrees()
    print(f"\nFinisher worktrees: {len(wts)}")
    for wt in wts:
        dirty = "dirty" if worktree_manager.has_uncommitted(wt["path"]) else "clean"
        print(f"  {wt.get('branch')} -> {wt.get('path')} ({dirty})")

    print("\nNOTE: progress is Finisher's own execution progress, not verified")
    print("OWNEX product completion. Only tasks with passing verification")
    print("count as verified.")
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    """Activity timeline (§7F): newest-first event log. The file itself can
    be tailed live (`tail -f <state_dir>/events.jsonl`) while the daemon runs."""
    from scripts.finisher.events import _events_path, read_events

    events = read_events(limit=args.limit, task_id=args.task, event_type=args.event_type)
    if not events:
        print("No events recorded.")
        return 0
    for e in events:
        print(f"{e.get('ts', '')[:19]} {e.get('type', ''):16} {e.get('message', '')[:100]}")
    print(f"\n({len(events)} events from {_events_path()})")
    return 0


def cmd_locks(args: argparse.Namespace) -> int:
    """Inspect and release file locks (megaprompt §7 conflict resolution)."""
    from scripts.finisher.locks import PathLockManager

    daemon = FinisherDaemon()
    lm = PathLockManager(daemon.state)
    if args.release:
        released = lm.release(args.release)
        print(f"{'Released' if released else 'No such lock'}: {args.release}")
        return 0 if released else 1

    if args.reap:
        orphans = lm.orphan_locks()
        expired = lm.reap_expired()
        state_manager.save()
        print(f"Reaped {len(expired)} expired lock(s).")
        print(f"{len(orphans)} orphan lock(s) (owner has no worker record):")
        for lock in orphans:
            print(f"  {lock['lock_id']} owner={lock['owner']} paths={lock['paths']}")
        if orphans and args.force:
            for lock in orphans:
                lm.release(lock["lock_id"])
            state_manager.save()
            print(f"Force-released {len(orphans)} orphan lock(s).")
        return 0

    active = lm.active_locks()
    if not active:
        print("No active locks.")
        return 0
    for lock_id, lock in active.items():
        age = int(lock.get("expires_at", 0) - time.time())
        print(f"{lock_id}  owner={lock['owner']}  task={lock['task_id']}  paths={lock['paths']}  expires_in={age}s")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Environment preflight for overnight runs."""
    import shutil

    print("=" * 66)
    print("OWNEX FINISHER — DOCTOR")
    print("=" * 66)
    issues: list[str] = []

    print(f"python        : {sys.version.split()[0]}")
    print(f"repo root     : {REPO_ROOT}")
    print(f"state dir     : {FINISHER_STATE_DIR}")
    if not FINISHER_STATE_DIR.exists():
        issues.append("state dir missing (will be created on start)")

    lock = FINISHER_STATE_DIR / "finisher.lock"
    if lock.exists():
        print(f"instance lock : present ({lock.name}) — another daemon may be running")
    else:
        print("instance lock : none (safe to start)")

    oc = shutil.which("opencode")
    print(f"opencode      : {oc or 'NOT FOUND'}")
    if not oc:
        issues.append("opencode not on PATH — workers cannot launch")

    free_gb = shutil.disk_usage(REPO_ROOT).free / 1e9
    print(f"disk free     : {free_gb:.1f} GB")
    if free_gb < 2:
        issues.append(f"low disk ({free_gb:.1f} GB)")

    cp_dir = FINISHER_STATE_DIR / "checkpoints"
    n_cp = len(list(cp_dir.glob("*.json"))) if cp_dir.exists() else 0
    print(f"checkpoints   : {n_cp}")

    dirty = (
        subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10)
        .stdout.strip()
        .split("\n")
    )
    print(f"uncommitted   : {len([d for d in dirty if d])} paths (NOT touched by finisher)")

    models = model_router.discover_models()
    print(f"models found  : {len(models)}")
    for m in models[:8]:
        print(f"  {m.provider}/{m.model} free={m.free} ctx={m.context_window}")
    if not models:
        issues.append("no models discovered")

    print()
    if issues:
        print("ISSUES:")
        for i in issues:
            print(f"  - {i}")
        return 1
    print("All checks passed.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    daemon = FinisherDaemon()
    status = daemon.status()
    print(json.dumps(status, indent=2))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    gate_id = args.gate_id
    decision = "APPROVE" if args.command == "approve" else "REJECT"
    state_manager.resolve_human_gate(gate_id, decision)
    print(f"Gate {gate_id}: {decision}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    result = verification_engine.run_full_check()
    print(f"Verification: {'PASSED' if result.passed else 'FAILED'}")
    if result.evidence:
        for name, ev in result.evidence.items():
            status = "✓" if ev.get("passed") else "✗"
            print(f"  {status} {name}")
    return 0 if result.passed else 1


def cmd_tasks(args: argparse.Namespace) -> int:
    daemon = FinisherDaemon()
    status = daemon.status()
    for tid, task in status["tasks"].items():
        print(f"{task['status']:15} {tid:10} {task['title']}")
    return 0


def cmd_workers(args: argparse.Namespace) -> int:
    daemon = FinisherDaemon()
    status = daemon.status()
    for wid, worker in status["workers"].items():
        print(
            f"{worker['status']:15} {wid:20} PID:{worker.get('process_id', 'N/A')} Task:{worker.get('task_id', 'N/A')}"
        )
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    cp = checkpoint_manager.create_checkpoint(
        task_id=args.task_id,
        next_action=args.next_action or "manual checkpoint",
    )
    print(f"Checkpoint created: {cp.checkpoint_id}")
    return 0


def cmd_recover(args: argparse.Namespace) -> int:
    latest = checkpoint_manager.load_latest_checkpoint()
    if not latest:
        print("No checkpoint found")
        return 1

    report = checkpoint_manager.inspect_restore(latest)
    print(f"Latest checkpoint: {latest.checkpoint_id}")
    print(f"  Task: {latest.task_id}")
    print(f"  Commit at checkpoint: {report['target_commit']}")
    print(f"  Current HEAD:        {report['current_commit']}")
    print(f"  Uncommitted paths:   {report['uncommitted_files_lost']}")
    print("  NOTE: recovery resets TASK state only. It never runs git reset")
    print("        and never touches your working tree (Constitution rule 5).")

    if args.confirm:
        success = checkpoint_manager.restore_from_checkpoint(latest, destructive_allowed=True)
        if success:
            print(f"Task state restored from {latest.checkpoint_id}")
        else:
            print("Restore failed")
            return 1
    else:
        print("  Run with --confirm to reset task state from this checkpoint")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ownex-finisher", description="OWNEX Finisher - Autonomous Project Completion"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_start = subparsers.add_parser("start", help="Start the finisher daemon")
    p_start.add_argument("--overnight", action="store_true", help="Enable overnight mode")
    p_start.add_argument(
        "--max-duration", type=float, default=None, help="Overnight duration budget in seconds (min 60)"
    )
    p_start.add_argument("--max-tasks", type=int, default=None, help="Max worker launches this run (0 = unlimited)")
    p_start.set_defaults(func=cmd_start)

    p_status = subparsers.add_parser("status", help="Show current status")
    p_status.set_defaults(func=cmd_status)

    p_approve = subparsers.add_parser("approve", help="Approve a human gate")
    p_approve.add_argument("gate_id", help="Gate ID to approve")
    p_approve.set_defaults(func=cmd_approve)

    p_reject = subparsers.add_parser("reject", help="Reject a human gate")
    p_reject.add_argument("gate_id", help="Gate ID to reject")
    p_reject.set_defaults(func=cmd_approve)

    p_verify = subparsers.add_parser("verify", help="Run full verification suite")
    p_verify.set_defaults(func=cmd_verify)

    p_tasks = subparsers.add_parser("tasks", help="List all tasks")
    p_tasks.set_defaults(func=cmd_tasks)

    p_workers = subparsers.add_parser("workers", help="List all workers")
    p_workers.set_defaults(func=cmd_workers)

    p_pause = subparsers.add_parser("pause", help="Pause starting new tasks")
    p_pause.set_defaults(func=cmd_pause)

    p_resume = subparsers.add_parser("resume", help="Resume after pause")
    p_resume.set_defaults(func=cmd_resume)

    p_stop = subparsers.add_parser("stop", help="Controlled stop of the running daemon")
    p_stop.set_defaults(func=cmd_stop)

    p_report = subparsers.add_parser("report", help="Print the execution report")
    p_report.set_defaults(func=cmd_report)

    p_doctor = subparsers.add_parser("doctor", help="Preflight the environment")
    p_doctor.set_defaults(func=cmd_doctor)

    p_locks = subparsers.add_parser("locks", help="Inspect/release file locks")
    p_locks.add_argument("--release", metavar="LOCK_ID", help="Release a specific lock")
    p_locks.add_argument("--reap", action="store_true", help="Reap expired locks and list orphans")
    p_locks.add_argument("--force", action="store_true", help="With --reap, also release orphans")
    p_locks.set_defaults(func=cmd_locks)

    p_events = subparsers.add_parser("events", help="Show the activity timeline (newest first)")
    p_events.add_argument("--limit", type=int, default=30, help="Max events to show")
    p_events.add_argument("--task", default=None, help="Filter by task id")
    p_events.add_argument("--type", dest="event_type", default=None, help="Filter by event type")
    p_events.set_defaults(func=cmd_events)

    p_checkpoint = subparsers.add_parser("checkpoint", help="Create a checkpoint")
    p_checkpoint.add_argument("--task-id", help="Task ID")
    p_checkpoint.add_argument("--next-action", help="Next action description")
    p_checkpoint.set_defaults(func=cmd_checkpoint)

    p_recover = subparsers.add_parser("recover", help="Recover from checkpoint")
    p_recover.add_argument("--confirm", action="store_true", help="Confirm restoration")
    p_recover.set_defaults(func=cmd_recover)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
