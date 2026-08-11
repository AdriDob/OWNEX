from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.copilot.hermes_bridge")

HERMES_SCRIPT = Path.home() / "projects" / "Rastro" / "run.py"


class HermesBridge:
    """Bridge between COPILOT and Hermes automation agent.

    COPILOT can request Hermes to execute system commands:
      - backup, status, health, logs, doctor, help
    """

    async def execute(self, command: str, args: list[str] | None = None) -> dict[str, Any]:
        """Execute a Hermes command and return structured result."""
        try:
            cmd = ["python", str(HERMES_SCRIPT), "--hermes", command]
            if args:
                cmd.extend(args)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            return {
                "command": command,
                "success": result.returncode == 0,
                "stdout": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
                "stderr": result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"command": command, "success": False, "error": "timeout"}
        except FileNotFoundError:
            return {"command": command, "success": False, "error": "Hermes script not found"}
        except Exception as exc:
            return {"command": command, "success": False, "error": str(exc)}

    async def backup(self) -> dict[str, Any]:
        return await self.execute("backup")

    async def status(self) -> dict[str, Any]:
        return await self.execute("status")

    async def health(self) -> dict[str, Any]:
        return await self.execute("health")

    async def doctor(self) -> dict[str, Any]:
        return await self.execute("doctor")

    async def logs(self, lines: int = 50) -> dict[str, Any]:
        return await self.execute("logs", ["--lines", str(lines)])


_hermes_bridge: HermesBridge | None = None


def get_hermes_bridge() -> HermesBridge:
    global _hermes_bridge
    if _hermes_bridge is None:
        _hermes_bridge = HermesBridge()
    return _hermes_bridge
