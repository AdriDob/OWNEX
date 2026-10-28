from __future__ import annotations

import logging
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.copilot.opencode_bridge")

PROJECT_DIR = Path.home() / "projects" / "Rastro"

DEFAULT_MODEL = "opencode/deepseek-v4-flash-free"
DEFAULT_TIMEOUT_S = 300
OUTPUT_TAIL_CHARS = 3000

# Side-by-side v1/v2: el binario se elige por env, default v1 estable.
# OPENCODE_BINARY=opencode (default, producción) | opencode2 (beta, observación).
# El contrato (run/propose/implement + runs dir + diffs) queda igual.


def resolve_opencode_binary(explicit: str | None = None) -> str:
    """Binario opencode a usar: explícito > env OPENCODE_BINARY > default v1."""
    if explicit:
        return explicit
    return os.environ.get("OPENCODE_BINARY", "opencode").strip() or "opencode"


# Disciplina obligatoria antepuesta a todo task con escritura (fase execute).
# La constitución completa vive en .ai/AGENT_CHARTER.md del repo (cwd del run).
AGENT_LOOP_PREAMBLE = """\
Before acting, obey the repo Agent Loop (.ai/AGENT_CHARTER.md):
1. PLAN FIRST: inspect real code/tests/contracts — never assume.
2. GOLDEN RULE: prove the feature does not already exist and work; if it does, do NOT rewrite — verify and report.
3. Minimal atomic changes; reuse existing code; zero tech debt; no mocks in production paths.
4. VERIFY: run the related tests + linters for every touched file.
5. Report: what changed, where (file:line), how verified, what was NOT touched.
"""

# Fase propose: análisis sin escritura. El router verifica con git que nada cambió.
PROPOSE_PREAMBLE = """\
STRICTLY READ-ONLY TASK. Do NOT create, modify or delete any file. Do NOT run
write-shaped commands. Analyze the real repository and return: findings with
evidence (file:line), classification (NEW/EXTEND/FIX/COMPLETE per existing
code), and a minimal implementation plan with tests. End with NEXT ACTION.
"""


def _runs_dir() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", Path.home() / ".ownex"))
    path = base / "opencode_runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _git(args: list[str], cwd: Path) -> str:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=30, cwd=str(cwd))
        return out.stdout if out.returncode == 0 else ""
    except Exception:
        return ""


class OpenCodeBridge:
    """Bridge between COPILOT and OpenCode for code modifications.

    COPILOT can request OpenCode to:
      - Implement features
      - Fix bugs
      - Refactor code
      - Answer codebase questions
      - Run tests
    """

    def __init__(self, binary: str | None = None) -> None:
        self._binary = resolve_opencode_binary(binary)
        self._project_dir = PROJECT_DIR

    def _record_run_dir(self, run_id: str) -> Path:
        run_dir = _runs_dir() / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    @staticmethod
    def _tail(text: str, limit: int = OUTPUT_TAIL_CHARS) -> str:
        return text[-limit:] if len(text) > limit else text

    async def run(
        self,
        task: str,
        model: str = DEFAULT_MODEL,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        mode: str = "execute",
    ) -> dict[str, Any]:
        """Execute a task via OpenCode CLI.

        mode="propose": read-only analysis (router verifies no files changed).
        mode="execute": full Agent Loop discipline prepended.
        Full output always lands in OWNEX_DATA_DIR/opencode_runs/<id>/.
        """
        run_id = uuid.uuid4().hex[:12]
        t0 = time.monotonic()
        preamble = PROPOSE_PREAMBLE if mode == "propose" else AGENT_LOOP_PREAMBLE
        full_task = f"{preamble}\n{task}"
        run_dir = self._record_run_dir(run_id)
        (run_dir / "prompt.txt").write_text(full_task, encoding="utf-8")
        status_before = _git(["status", "--short"], self._project_dir)
        try:
            cmd = [self._binary, "run", full_task, "--model", model]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, cwd=str(self._project_dir))

            dur = (time.monotonic() - t0) * 1000
            (run_dir / "output.log").write_text(
                f"--- STDOUT ---\n{result.stdout}\n--- STDERR ---\n{result.stderr}\n",
                encoding="utf-8",
            )
            status_after = _git(["status", "--short"], self._project_dir)
            diff_stat = _git(["diff", "--stat"], self._project_dir)
            (run_dir / "diff.patch").write_text(_git(["diff"], self._project_dir), encoding="utf-8")
            changed = sorted({line[3:].split(" -> ")[-1] for line in status_after.splitlines() if line.strip()})
            return {
                "run_id": run_id,
                "task": task[:200],
                "mode": mode,
                "model": model,
                "binary": self._binary,
                "success": result.returncode == 0,
                "output": self._tail(result.stdout),
                "output_truncated": len(result.stdout) > OUTPUT_TAIL_CHARS,
                "output_file": str(run_dir / "output.log"),
                "error": self._tail(result.stderr, 1000),
                "duration_ms": round(dur, 1),
                "returncode": result.returncode,
                "files_changed": changed,
                "tree_dirty_before": bool(status_before.strip()),
                "diff_stat": diff_stat[-2000:],
                "diff_file": str(run_dir / "diff.patch"),
            }
        except subprocess.TimeoutExpired:
            return {
                "run_id": run_id,
                "task": task[:200],
                "mode": mode,
                "success": False,
                "error": f"timeout ({timeout_s}s)",
                "output_file": str(run_dir / "output.log"),
                "duration_ms": (time.monotonic() - t0) * 1000,
            }
        except FileNotFoundError:
            return {
                "run_id": run_id,
                "task": task[:200],
                "mode": mode,
                "success": False,
                "error": "opencode binary not found",
            }
        except Exception as exc:
            return {
                "run_id": run_id,
                "task": task[:200],
                "mode": mode,
                "success": False,
                "error": str(exc),
                "duration_ms": (time.monotonic() - t0) * 1000,
            }

    async def ask(self, question: str, model: str = DEFAULT_MODEL) -> dict[str, Any]:
        """Ask OpenCode a codebase question (read-only)."""
        return await self.run(f"Answer this question about the codebase: {question}", model=model, mode="propose")

    async def propose(self, description: str, model: str = DEFAULT_MODEL) -> dict[str, Any]:
        """Read-only plan for a change (phase 1 of two-phase flow)."""
        return await self.run(f"Propose (do not implement yet): {description}", model=model, mode="propose")

    async def implement(self, description: str, model: str = DEFAULT_MODEL) -> dict[str, Any]:
        """Request OpenCode to implement a feature (phase 2: needs approval)."""
        return await self.run(f"Implement the following: {description}", model=model, mode="execute")

    async def fix(self, bug_description: str, model: str = DEFAULT_MODEL) -> dict[str, Any]:
        """Request OpenCode to fix a bug (phase 2: needs approval)."""
        return await self.run(f"Fix the following bug: {bug_description}", model=model, mode="execute")

    async def refactor(self, description: str, model: str = DEFAULT_MODEL) -> dict[str, Any]:
        """Request OpenCode to refactor code (phase 2: needs approval)."""
        return await self.run(f"Refactor the following: {description}", model=model, mode="execute")


_opencode_bridge: OpenCodeBridge | None = None


def get_opencode_bridge() -> OpenCodeBridge:
    global _opencode_bridge
    if _opencode_bridge is None:
        _opencode_bridge = OpenCodeBridge()
    return _opencode_bridge
