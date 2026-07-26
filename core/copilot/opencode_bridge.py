from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.copilot.opencode_bridge")

PROJECT_DIR = Path.home() / "projects" / "Rastro"


class OpenCodeBridge:
    """Bridge between COPILOT and OpenCode for code modifications.

    COPILOT can request OpenCode to:
      - Implement features
      - Fix bugs
      - Refactor code
      - Answer codebase questions
      - Run tests
    """

    def __init__(self) -> None:
        self._binary = "opencode"
        self._project_dir = PROJECT_DIR

    async def run(self, task: str, model: str = "opencode/deepseek-v4-flash-free") -> dict[str, Any]:
        """Execute a task via OpenCode CLI."""
        import time

        t0 = time.monotonic()
        try:
            cmd = [self._binary, "run", task, "--model", model]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(self._project_dir))

            dur = (time.monotonic() - t0) * 1000

            return {
                "task": task[:200],
                "success": result.returncode == 0,
                "output": result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout,
                "error": result.stderr[-1000:]
                if result.stderr and len(result.stderr) > 1000
                else (result.stderr or ""),
                "duration_ms": round(dur, 1),
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "task": task[:200],
                "success": False,
                "error": "timeout (300s)",
                "duration_ms": (time.monotonic() - t0) * 1000,
            }
        except FileNotFoundError:
            return {"task": task[:200], "success": False, "error": "opencode binary not found"}
        except Exception as exc:
            return {
                "task": task[:200],
                "success": False,
                "error": str(exc),
                "duration_ms": (time.monotonic() - t0) * 1000,
            }

    async def ask(self, question: str) -> dict[str, Any]:
        """Ask OpenCode a codebase question (read-only)."""
        return await self.run(f"Answer this question about the codebase: {question}")

    async def implement(self, description: str) -> dict[str, Any]:
        """Request OpenCode to implement a feature."""
        return await self.run(f"Implement the following: {description}")

    async def fix(self, bug_description: str) -> dict[str, Any]:
        """Request OpenCode to fix a bug."""
        return await self.run(f"Fix the following bug: {bug_description}")

    async def refactor(self, description: str) -> dict[str, Any]:
        """Request OpenCode to refactor code."""
        return await self.run(f"Refactor the following: {description}")


_opencode_bridge: OpenCodeBridge | None = None


def get_opencode_bridge() -> OpenCodeBridge:
    global _opencode_bridge
    if _opencode_bridge is None:
        _opencode_bridge = OpenCodeBridge()
    return _opencode_bridge
