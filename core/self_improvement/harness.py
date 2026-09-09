"""Objective execution harness for the self-improvement loop.

The harness runs a solution inside a policy-limited sandbox (temp workdir,
whitelisted commands, no network) and produces a Rollout with real stdout,
stderr, exit code and timing. Verification is deterministic per task category:
a CODE task runs a verification script that imports the solution and checks
behavior; a TEST task runs pytest; a DEBUG task runs the patched snippet and
compares stdout. No subjective LLM grading — the checks are real executables.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from core.self_improvement.config import SelfImprovementConfig
from core.self_improvement.models import Rollout, Task, TaskCategory
from core.self_improvement.policies import ExecutionPolicy

PYTHON = sys.executable


class Harness:
    """Sandboxed executor that validates and runs a solution."""

    def __init__(self, config: SelfImprovementConfig, workdir: Path | None = None) -> None:
        self.config = config
        self.policy = ExecutionPolicy(config)
        self._workdir = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="ownex_harness_"))
        self._workdir.mkdir(parents=True, exist_ok=True)

    def cleanup(self) -> None:
        """Remove the sandbox workdir (best-effort)."""
        try:
            for child in list(self._workdir.iterdir()):
                if child.is_file():
                    child.unlink(missing_ok=True)
            self._workdir.rmdir()
        except OSError:
            pass

    def run(self, task: Task, solution: str, attempt: int = 0) -> Rollout:
        """Write the solution into the sandbox, run its verification, and return a Rollout."""
        started = time.time()
        rollout = Rollout(task_id=task.id, attempt=attempt, solution=solution)

        try:
            self.policy.enforce_solution(solution)
        except Exception as exc:
            rollout.error = f"policy: {exc}"
            rollout.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            rollout.duration_ms = int((time.time() - started) * 1000)
            return rollout

        # Write solution file. For TEST tasks pytest only collects test_*.py
        # files, so use a collectible name.
        filename = "test_solution.py" if task.category == TaskCategory.TEST else "solution.py"
        solution_path = self._workdir / filename
        solution_path.write_text(solution, encoding="utf-8")
        rollout.created_files.append(str(solution_path))

        cmd = self._verification_command(task)
        if not cmd:
            rollout.error = f"no verification strategy for category {task.category.value}"
            rollout.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            rollout.duration_ms = int((time.time() - started) * 1000)
            return rollout

        violations = self.policy.validate_command(cmd)
        if violations:
            rollout.error = f"policy: {'; '.join(violations)}"
            rollout.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            rollout.duration_ms = int((time.time() - started) * 1000)
            return rollout

        try:
            proc = subprocess.run(
                cmd,
                cwd=self._workdir,
                capture_output=True,
                text=True,
                timeout=self.config.rollout_timeout_seconds,
                env=self._sandbox_env(),
            )
            rollout.stdout = proc.stdout[:4000]
            rollout.stderr = proc.stderr[:2000]
            rollout.exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            rollout.error = "timeout"
            rollout.exit_code = -9
        except OSError as exc:
            rollout.error = f"os error: {exc}"
        except Exception as exc:  # noqa: BLE001 — harness must never raise
            rollout.error = f"harness error: {exc}"

        rollout.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rollout.duration_ms = int((time.time() - started) * 1000)
        return rollout

    def _sandbox_env(self) -> dict[str, str]:
        """Minimal environment: no network vars, fixed HOME, empty PATH additions."""
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(self._workdir),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "LC_ALL": "C.UTF-8",
            "TMPDIR": str(self._workdir),
        }
        if self.config.allow_network:
            return {**__import__("os").environ, **env}
        return env

    def _verification_command(self, task: Task) -> list[str]:
        """Build the objective verification command for a task category."""
        category = task.category
        if category == TaskCategory.CODE:
            verifier = self._workdir / "verify.py"
            verifier.write_text(self._code_verifier(task), encoding="utf-8")
            return [PYTHON, str(verifier)]
        if category == TaskCategory.TEST:
            return [PYTHON, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", str(self._workdir)]
        if category == TaskCategory.DEBUG:
            return [PYTHON, str(self._workdir / "solution.py")]
        if category == TaskCategory.ANALYSIS:
            verifier = self._workdir / "verify.py"
            verifier.write_text(self._analysis_verifier(task), encoding="utf-8")
            return [PYTHON, str(verifier)]
        if category == TaskCategory.GENERATION:
            verifier = self._workdir / "verify.py"
            verifier.write_text(self._generation_verifier(task), encoding="utf-8")
            return [PYTHON, str(verifier)]
        if category == TaskCategory.SECURITY:
            verifier = self._workdir / "verify.py"
            verifier.write_text(self._security_verifier(task), encoding="utf-8")
            return [PYTHON, str(verifier)]
        if category == TaskCategory.REASONING:
            verifier = self._workdir / "verify.py"
            verifier.write_text(self._reasoning_verifier(task), encoding="utf-8")
            return [PYTHON, str(verifier)]
        return []

    # ── Per-category verifiers ────────────────────────────────────
    # Each verifier is a self-contained Python script that exits 0 when the
    # solution satisfies the task, and 1 otherwise. The verifier imports the
    # user's solution.py to make checks real (not text-matching).

    def _code_verifier(self, task: Task) -> str:
        return (
            "import importlib.util, sys, json\n"
            "spec = importlib.util.spec_from_file_location('solution', 'solution.py')\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules['solution'] = mod\n"
            "spec.loader.exec_module(mod)\n"
            "# The task metadata can pin an expected callable result.\n"
            f"meta = json.loads(r'{self._json_meta(task)}')\n" + "if 'call' in meta:\n"
            "    fn = getattr(mod, meta['call'], None)\n"
            "    if fn is None:\n"
            "        print('missing callable', meta['call']); sys.exit(1)\n"
            "    for args, expected in meta.get('cases', []):\n"
            "        got = fn(*args)\n"
            "        if got != expected:\n"
            "            print(f'FAIL {meta[\"call\"]}({args}) => {got!r}, want {expected!r}')\n"
            "            sys.exit(1)\n"
            "print('CODE_OK')\n"
            "sys.exit(0)\n"
        )

    def _analysis_verifier(self, task: Task) -> str:
        return self._tpl(
            "import importlib.util, sys, json\n"
            "spec = importlib.util.spec_from_file_location('solution', 'solution.py')\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules['solution'] = mod\n"
            "spec.loader.exec_module(mod)\n"
            "accepted = __ACCEPTED__\n"
            "out = (mod.verdict if hasattr(mod, 'verdict') else getattr(mod, 'answer', '')).strip().lower()\n"
            "if out in accepted:\n"
            "    print('ANALYSIS_OK')\n"
            "    sys.exit(0)\n"
            "print(f'BAD verdict: {out!r}')\n"
            "sys.exit(1)\n",
            accepted=self._meta(task, "accepted", ["a"]),
        )

    def _generation_verifier(self, task: Task) -> str:
        return self._tpl(
            "import importlib.util, sys, json\n"
            "spec = importlib.util.spec_from_file_location('solution', 'solution.py')\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules['solution'] = mod\n"
            "spec.loader.exec_module(mod)\n"
            "keys = __KEYS__\n"
            "data = getattr(mod, 'payload', None)\n"
            "if data is None:\n"
            "    raw = getattr(mod, 'RESULT', '{}')\n"
            "    data = json.loads(raw) if isinstance(raw, str) else raw\n"
            "missing = [k for k in keys if k not in data]\n"
            "if missing:\n"
            "    print('missing keys', missing); sys.exit(1)\n"
            "print('GENERATION_OK')\n"
            "sys.exit(0)\n",
            keys=self._meta(task, "keys", ["x", "y"]),
        )

    def _security_verifier(self, task: Task) -> str:
        return self._tpl(
            "import importlib.util, sys\n"
            "spec = importlib.util.spec_from_file_location('solution', 'solution.py')\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules['solution'] = mod\n"
            "spec.loader.exec_module(mod)\n"
            "accepted = __ACCEPTED__\n"
            "out = (getattr(mod, 'vuln_type', '') or '').strip().lower()\n"
            "if out in accepted:\n"
            "    print('SECURITY_OK')\n"
            "    sys.exit(0)\n"
            "print(f'BAD vuln: {out!r}')\n"
            "sys.exit(1)\n",
            accepted=self._meta(task, "accepted", ["sqli"]),
        )

    def _reasoning_verifier(self, task: Task) -> str:
        return self._tpl(
            "import importlib.util, sys\n"
            "spec = importlib.util.spec_from_file_location('solution', 'solution.py')\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules['solution'] = mod\n"
            "spec.loader.exec_module(mod)\n"
            "expected = __EXPECTED__\n"
            "out = (getattr(mod, 'answer', '') or '').strip()\n"
            "if out == expected:\n"
            "    print('REASONING_OK')\n"
            "    sys.exit(0)\n"
            "print(f'BAD answer: {out!r}, want {expected!r}')\n"
            "sys.exit(1)\n",
            expected=self._meta(task, "answer", "0"),
        )

    # ── helpers ───────────────────────────────────────────────────

    def _meta(self, task: Task, key: str, default: Any) -> Any:
        return task.metadata.get(key, default)

    def _json_meta(self, task: Task) -> str:
        import json

        return json.dumps(task.metadata)

    def _tpl(self, template: str, **values: Any) -> str:
        """Sentinel-based templating so generated f-string braces are untouched."""
        for key, value in values.items():
            template = template.replace(f"__{key.upper()}__", repr(value))
        return template
