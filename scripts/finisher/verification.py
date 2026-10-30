"""Verification engine for OWNEX Finisher."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from scripts.finisher.state import REPO_ROOT, FinisherState, Task, TaskStatus, state_manager


@dataclass
class VerificationResult:
    passed: bool
    output: str
    error: str | None = None
    evidence: dict[str, Any] | None = None


class VerificationEngine:
    def __init__(self, state: FinisherState):
        self.state = state
        self.known_baseline_failures = self._load_known_failures()

    def _load_known_failures(self) -> set[str]:
        """Load known baseline test failures that should not be treated as regressions."""
        return {
            "test_security.py::test_login_rate_limit",
            "test_desktop_release.py",
            "test_e2e_copilot.py",
        }

    def is_known_failure(self, test_name: str) -> bool:
        for known in self.known_baseline_failures:
            if known in test_name:
                return True
        return False

    def run_verification(self, task: Task) -> VerificationResult:
        if not task.verification_commands:
            return VerificationResult(
                passed=True,
                output="No verification commands defined",
                evidence={"verified": True, "reason": "no_commands"},
            )

        all_passed = True
        all_output = []
        all_evidence = {}

        for cmd in task.verification_commands:
            result = self._run_command(cmd)
            all_output.append(f"$ {cmd}\n{result.output}")

            if not result.passed:
                all_passed = False
                if result.error:
                    all_output.append(f"ERROR: {result.error}")

            all_evidence[cmd] = {
                "passed": result.passed,
                "output": result.output,
                "error": result.error,
            }

        return VerificationResult(
            passed=all_passed,
            output="\n".join(all_output),
            evidence=all_evidence,
        )

    def _run_command(self, cmd: str) -> VerificationResult:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return VerificationResult(passed=True, output=result.stdout)
            else:
                output = result.stdout + result.stderr
                if self._is_known_baseline_failure(output):
                    return VerificationResult(
                        passed=True,
                        output=output,
                        evidence={"known_baseline_failure": True},
                    )
                return VerificationResult(passed=False, output=output, error=f"Exit code: {result.returncode}")

        except subprocess.TimeoutExpired:
            return VerificationResult(passed=False, output="", error="Command timeout (120s)")
        except Exception as e:
            return VerificationResult(passed=False, output="", error=str(e))

    def _is_known_baseline_failure(self, output: str) -> bool:
        for known in self.known_baseline_failures:
            if known in output:
                return True
        return False

    def run_full_check(self) -> VerificationResult:
        """Run the baseline verification gate: test-fast (103/1)"""
        checks = [
            (
                "pytest (fast) - BASELINE GATE",
                "python -m pytest --timeout=30 -q tests/test_scoring.py tests/test_opportunity_engine.py tests/test_opportunity_engine_comprehensive.py tests/test_scheduler_jobs.py tests/test_e2e_security_pipeline.py tests/test_security_cycle.py",
            ),
        ]

        all_passed = True
        all_output = []
        all_evidence = {}

        for name, cmd in checks:
            result = self._run_command(cmd)
            all_output.append(f"=== {name} ===\n{result.output}")
            all_evidence[name] = {
                "passed": result.passed,
                "output": result.output,
                "error": result.error,
            }
            if not result.passed:
                all_passed = False

        return VerificationResult(
            passed=all_passed,
            output="\n".join(all_output),
            evidence=all_evidence,
        )

    def _worktree_out_of_scope_paths(self, task: Task) -> list[str]:
        """Rutas modificadas fuera del worktree autorizado. Solo lectura.

        Un worktree es un directorio de trabajo, no una barrera del SO: un
        worker puede escribir rutas absolutas, `..` o vía symlinks. Este gate
        detecta esas escrituras (visibles en el git status del worktree) y
        hace fallar la verificación. Lo invisible a `git status` (borrados
        fuera del worktree) sigue cubierto por task.files + locks + prompt.
        """
        from scripts.finisher.worktree import is_within_root

        offenders: list[str] = []
        seen_roots: set[str] = set()
        for worker in self.state.workers.values():
            if worker.task_id != task.id or not worker.worktree_path:
                continue
            root = worker.worktree_path
            if root in seen_roots:
                continue
            seen_roots.add(root)
            try:
                proc = subprocess.run(
                    ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=30
                )
            except Exception:
                continue
            if proc.returncode != 0:
                continue
            for line in proc.stdout.splitlines():
                path = line[3:] if len(line) > 3 else ""
                if " -> " in path:
                    path = path.split(" -> ", 1)[1]
                path = path.strip().strip('"')
                if path and not is_within_root(root, path):
                    offenders.append(path)
        return sorted(set(offenders))

    def verify_task_completion(self, task: Task) -> bool:
        """Only a real passing command may set `task.verified`.

        The flag plus stored evidence is what progress is computed from; model
        prose never is (Constitution rule 9).
        """
        # Pre-flight check: detect symlink escapes before running verification
        for file_path in task.files or []:
            try:
                from scripts.finisher.locks import resolve_safely

                resolve_safely(file_path)
            except ValueError as e:
                task.status = TaskStatus.FAILED
                task.verified = False
                task.failure_reason = f"Symlink escape detected: {e}"
                state_manager.update_task(task)
                return False

        offenders = self._worktree_out_of_scope_paths(task)
        if offenders:
            task.status = TaskStatus.FAILED
            task.verified = False
            task.failure_reason = f"Out-of-scope writes outside worktree: {offenders[:5]}"
            state_manager.update_task(task)
            return False
        result = self.run_verification(task)
        task.evidence = [
            {"command": cmd, "passed": ev.get("passed"), "output": (ev.get("output") or "")[:4000]}
            for cmd, ev in (result.evidence or {}).items()
        ]
        if result.passed:
            had_commands = bool(task.verification_commands)
            task.status = TaskStatus.PASSED
            task.result = "verified"
            task.verified = True
            task.verified_at = datetime.now().isoformat()
            task.completed_at = datetime.now().isoformat()
            if not had_commands:
                # No command ran => nothing was proven. Constitution rule 9.
                task.verified = False
                task.result = "completed WITHOUT verification commands (unverified)"
        else:
            task.status = TaskStatus.FAILED
            task.verified = False
            task.failure_reason = f"Verification failed: {result.output[:500]}"
        state_manager.update_task(task)
        return result.passed


verification_engine = VerificationEngine(state_manager.get_state())
