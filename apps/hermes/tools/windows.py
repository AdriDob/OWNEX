"""Windows-specific tools — registry, scheduled tasks, environment."""

from __future__ import annotations

import logging
import platform
import subprocess

from apps.hermes.tools.base import BaseTool, ToolResult

logger = logging.getLogger("catseye.hermes.tools.windows")


class PowerShellRunner(BaseTool):
    name = "powershell"
    description = "Execute arbitrary PowerShell commands safely"

    def check_available(self) -> ToolResult:
        if platform.system() != "Windows":
            return ToolResult(False, "PowerShell only available on Windows")
        try:
            r = subprocess.run(
                ["powershell", "-Command", "$PSVersionTable.PSVersion"], capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return ToolResult(True, f"PowerShell available: {r.stdout.strip()}")
            return ToolResult(False, r.stderr.strip())
        except FileNotFoundError:
            return ToolResult(False, "PowerShell not found")

    def run(self, command: str, timeout: int = 60) -> ToolResult:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if r.returncode == 0:
                return ToolResult(True, "Command executed", {"stdout": r.stdout[:5000], "stderr": r.stderr[:1000]})
            return ToolResult(False, r.stderr.strip()[:500], {"stdout": r.stdout[:2000]})
        except subprocess.TimeoutExpired:
            return ToolResult(False, f"Command timed out after {timeout}s")
        except Exception as exc:
            return ToolResult(False, str(exc))


class ScheduledTasks(BaseTool):
    name = "tasks"
    description = "List and manage Windows scheduled tasks"
    requires_windows = True

    def check_available(self) -> ToolResult:
        if platform.system() != "Windows":
            return ToolResult(False, "Scheduled Tasks only available on Windows")
        return ToolResult(True, "schtasks available")

    def list_all(self) -> ToolResult:
        try:
            r = subprocess.run(
                ["schtasks", "/query", "/fo", "LIST", "/v"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode == 0:
                tasks = [task for task in r.stdout.split("\n") if task.strip()][:200]
                return ToolResult(True, f"{len(tasks)} tasks", {"tasks": tasks})
            return ToolResult(False, r.stderr.strip())
        except subprocess.TimeoutExpired:
            return ToolResult(False, "schtasks timed out")

    def create(self, name: str, command: str, schedule: str = "daily", time: str = "09:00") -> ToolResult:
        try:
            r = subprocess.run(
                ["schtasks", "/create", "/tn", name, "/tr", command, "/sc", schedule, "/st", time, "/f"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0:
                return ToolResult(True, f"Task '{name}' created")
            return ToolResult(False, r.stderr.strip())
        except Exception as exc:
            return ToolResult(False, str(exc))

    def delete(self, name: str) -> ToolResult:
        try:
            r = subprocess.run(
                ["schtasks", "/delete", "/tn", name, "/f"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0:
                return ToolResult(True, f"Task '{name}' deleted")
            return ToolResult(False, r.stderr.strip())
        except Exception as exc:
            return ToolResult(False, str(exc))


class EnvironmentManager(BaseTool):
    name = "env"
    description = "Manage environment variables (user scope)"
    requires_windows = True

    def check_available(self) -> ToolResult:
        return ToolResult(True, "Environment tools available")

    def get(self, name: str) -> ToolResult:
        import os

        value = os.environ.get(name, "")
        if value:
            return ToolResult(True, f"{name}={value}", {"name": name, "value": value})
        return ToolResult(False, f"Variable '{name}' not set")

    def set_user(self, name: str, value: str) -> ToolResult:
        try:
            r = subprocess.run(
                ["powershell", "-Command", f"[Environment]::SetEnvironmentVariable('{name}', '{value}', 'User')"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0:
                return ToolResult(True, f"Set user env {name}={value}")
            return ToolResult(False, r.stderr.strip())
        except Exception as exc:
            return ToolResult(False, str(exc))
