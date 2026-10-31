"""Codex CLI Integration for OWNEX.

Integrates OpenAI Codex CLI as a development agent tool within the OWNEX system.
Follows the PRODUCT → DOMAIN → APPLICATION → INFRASTRUCTURE → EXTERNAL WORLD architecture.

Key features:
- Detect Codex CLI installation and version
- Execute coding tasks via CLI interfaces
- Capture output, errors and exit codes
- Track changes produced and test results
- Cancel executions when supported by the interface
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.ai_integrations.codex_cli")


@dataclass
class CodexCLIStatus:
    """Runtime status of Codex CLI integration."""

    installed: bool = False
    version: str = ""
    accessible: bool = False
    last_checked: str = ""
    latency_ms: float = 0.0
    error: str | None = None
    last_execution: str | None = None
    last_exit_code: int | None = None
    capabilities: list[str] = field(default_factory=lambda: [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "installed": self.installed,
            "version": self.version,
            "accessible": self.accessible,
            "last_checked": self.last_checked,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
            "last_execution": self.last_execution,
            "last_exit_code": self.last_exit_code,
            "capabilities": self.capabilities,
        }


class CodexCLIIntegration:
    """Integration adapter for OpenAI Codex CLI."""

    def __init__(self):
        self.status = CodexCLIStatus()
        self._exe_path: str | None = None
        self._detect()

    def _detect(self) -> None:
        """Detect Codex CLI installation and version."""
        try:
            # Try to find codex in PATH
            result = subprocess.run(
                ["codex", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Codex CLI outputs version on stderr or stdout
                version_line = result.stderr or result.stdout
                # Parse version - codex --version outputs something like "codex v1.0.0"
                if "codex" in version_line.lower():
                    parts = version_line.strip().split()
                    ver = parts[1] if len(parts) > 1 else "unknown"
                    self.status.version = ver
                    self.status.installed = True
                    self.status.accessible = True
                else:
                    self.status.version = "unknown (found via --version)"
                    self.status.installed = True
                    self.status.accessible = True
            else:
                # codex command exists but --version failed
                self.status.version = "installed (version check failed)"
                self.status.installed = True
                self.status.accessible = False
        except FileNotFoundError:
            # codex not in PATH
            self.status.version = ""
            self.status.installed = False
            self.status.accessible = False
        except subprocess.TimeoutExpired:
            self.status.version = ""
            self.status.installed = False
            self.status.accessible = False
        except Exception as e:
            logger.warning(f"Codex CLI detection error: {e}")
            self.status.version = ""
            self.status.installed = False
            self.status.accessible = False

        self.status.last_checked = datetime.now(UTC).isoformat()

    def _resolve_executable(self) -> str | None:
        """Resolve the full path to the codex executable."""
        if self.status.installed and self.status.accessible:
            # Try to find it
            if self._exe_path is not None:
                return self._exe_path

            # Check common locations
            paths_to_try = [
                # In PATH
                "codex",
                # Via npx (if node is available)
                sys.executable,
                # Check if it's a python package
            ]

            for p in paths_to_try:
                try:
                    test_result = subprocess.run(
                        [p, "--help"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if test_result.returncode == 0 and "codex" in (test_result.stdout or "").lower():
                        self._exe_path = p
                        return p
                except Exception:
                    continue

            # Try to locate via which or where
            try:
                result = subprocess.run(
                    ["which", "codex"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self._exe_path = result.stdout.strip()
                    return self._exe_path
            except Exception:
                pass

        return None

    def available(self) -> bool:
        """Check if Codex CLI is available for use."""
        return self.status.installed and self.status.accessible

    def capabilities(self) -> list[str]:
        """Return list of supported capabilities."""
        if not self.available():
            return []

        base_caps = [
            "inspect_repository",
            "modify_files",
            "run_tests",
            "create_files",
            "edit_files",
            "delete_files",
            "search_code",
            "grep_pattern",
            "list_directory",
            "execute_bash",
            "capture_output",
        ]

        # Add version-specific capabilities
        ver = self.status.version.lower()
        if "1" in ver or "2" in ver or "latest" in ver:
            base_caps.extend(
                [
                    "multi_file_edits",
                    "import_management",
                    "dependency_analysis",
                    "config_generation",
                ]
            )

        self.status.capabilities = base_caps
        return base_caps

    def execute_task(
        self,
        task: str,
        workdir: str | None = None,
        timeout: int = 300,
        capture_output: bool = True,
    ) -> dict[str, Any]:
        """Execute a coding task via Codex CLI.

        Args:
            task: Description of the coding task to execute
            workdir: Working directory for execution
            timeout: Maximum execution time in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            Dictionary with execution results
        """
        exec_path = self._resolve_executable()
        if not exec_path or not self.available():
            return {
                "success": False,
                "error": "Codex CLI no está instalado o no es accesible",
                "exit_code": -1,
                "output": "",
                "workdir": workdir or os.getcwd(),
            }

        # Build the command
        # Codex CLI typically uses: codex ask "task description"
        # Or: codex exec "task description"
        cmd = [exec_path, "ask", task]

        # Add working directory if specified
        env = os.environ.copy()
        if workdir:
            cmd.extend(["--workdir", workdir])
            env["PWD"] = workdir

        start_time = datetime.now(UTC)
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                env=env,
            )

            end_time = datetime.now(UTC)
            latency_ms = (end_time - start_time).total_seconds() * 1000

            output = result.stdout
            if capture_output and not output and result.stderr:
                output = result.stderr

            exit_code = result.returncode

            # Update status
            self.status.last_execution = end_time.isoformat()
            self.status.last_exit_code = exit_code
            if latency_ms > 0:
                self.status.latency_ms = latency_ms

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "output": output or "",
                "workdir": workdir or os.getcwd(),
                "latency_ms": round(latency_ms, 1),
                "status": self.status.to_dict(),
            }

        except subprocess.TimeoutExpired as e:
            end_time = datetime.now(UTC)
            latency_ms = (end_time - start_time).total_seconds() * 1000 if hasattr(e, "start_time") else 0

            self.status.last_execution = end_time.isoformat()
            self.status.last_exit_code = -1
            self.status.latency_ms = round(latency_ms, 1) if latency_ms > 0 else 0

            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "workdir": workdir or os.getcwd(),
                "timeout": timeout,
                "error": "Timeout excedido durante la ejecución de Codex CLI",
                "status": self.status.to_dict(),
            }

        except Exception as e:
            end_time = datetime.now(UTC)
            latency_ms = 0
            self.status.last_execution = end_time.isoformat()
            self.status.last_exit_code = -1
            self.status.latency_ms = 0

            logger.error(f"Codex CLI execution error: {e}")
            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "workdir": workdir or os.getcwd(),
                "error": str(e),
                "status": self.status.to_dict(),
            }

    def inspect_repository(self, repo_path: str | None = None) -> dict[str, Any]:
        """Inspect a repository structure using Codex CLI.

        Args:
            repo_path: Path to the repository to inspect

        Returns:
            Dictionary with repository structure and metadata
        """
        workdir = repo_path or os.getcwd()
        result = self.execute_task(
            f"Inspect this repository structure and provide: 1) overall project summary, 2) main directories, 3) key files, 4) technology stack detected, 5) current status of development",
            workdir=workdir,
            timeout=120,
        )

        return {
            "repo_path": workdir,
            "inspection": result,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def run_tests(self, test_command: str | None = None, workdir: str | None = None) -> dict[str, Any]:
        """Run tests using Codex CLI.

        Args:
            test_command: Specific test command to run
            workdir: Working directory

        Returns:
            Test execution results
        """
        if test_command is None:
            test_command = "Run all tests and provide summary of pass/fail counts, any failures, and recommendations"

        return self.execute_task(
            f"{test_command}. Report pass/fail counts, list failures with details, and suggest fixes.",
            workdir=workdir,
            timeout=180,
        )

    def get_status(self) -> CodexCLIStatus:
        """Get current status of Codex CLI integration."""
        # Refresh capabilities
        _ = self.capabilities()
        return self.status


# Singleton instance for registry
_codex_integration: CodexCLIIntegration | None = None


def get_codex_integration() -> CodexCLIIntegration:
    """Get the singleton Codex CLI integration instance."""
    global _codex_integration
    if _codex_integration is None:
        _codex_integration = CodexCLIIntegration()
    return _codex_integration


def init_codex_integration() -> CodexCLIIntegration:
    """Initialize and register the Codex CLI integration."""
    global _codex_integration
    _codex_integration = CodexCLIIntegration()
    return _codex_integration
