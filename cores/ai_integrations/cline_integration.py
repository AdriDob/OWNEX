"""Cline Integration for OWNEX.

Integrates Cline (VS Code extension) as a development agent tool within the OWNEX system.
Follows the PRODUCT → DOMAIN → APPLICATION → INFRASTRUCTURE → EXTERNAL WORLD architecture.

Key features:
- Detect Cline extension installation and configuration
- Execute coding tasks via Cline's interfaces
- Track approval requirements and human gate interactions
- Capture results and modifications
- Support both automated and interactive modes
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.ai_integrations.cline")


@dataclass
class ClineStatus:
    """Runtime status of Cline integration."""

    installed: bool = False
    version: str = ""
    accessible: bool = False
    last_checked: str = ""
    latency_ms: float = 0.0
    error: str | None = None
    last_execution: str | None = None
    last_exit_code: int | None = None
    capabilities: list[str] = field(default_factory=lambda: [])
    requires_approval: bool = False
    auto_approve: bool = False

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
            "requires_approval": self.requires_approval,
            "auto_approve": self.auto_approve,
        }


class ClineIntegration:
    """Integration adapter for Cline VS Code extension.

    Cline can operate as:
    1. VS Code extension (requires VS Code host)
    2. Standalone CLI mode (if available)
    3. API/server mode (if configured)
    """

    def __init__(self):
        self.status = ClineStatus()
        self._detect()

    def _detect(self) -> None:
        """Detect Cline installation and configuration."""
        try:
            # Try to find cline in PATH or as CLI tool
            result = subprocess.run(
                ["cline", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                version_line = result.stderr or result.stdout
                if "cline" in version_line.lower():
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
                self.status.version = "installed (version check failed)"
                self.status.installed = True
                self.status.accessible = False
        except FileNotFoundError:
            # cline not in PATH - could be VS Code extension only
            self.status.version = ""
            self.status.installed = False
            self.status.accessible = False
        except subprocess.TimeoutExpired:
            self.status.version = ""
            self.status.installed = False
            self.status.accessible = False
        except Exception as e:
            logger.warning(f"Cline detection error: {e}")
            self.status.version = ""
            self.status.installed = False
            self.status.accessible = False

        self.status.last_checked = datetime.now(UTC).isoformat()

        # Check for VS Code extension installation
        # Cline typically publishes VS Code extension metrics
        code_extension_path = os.path.expanduser("~/.vscode/extensions/cline")
        if os.path.isdir(code_extension_path):
            # Extension is installed, check if it's functional
            self.status.installed = True
            # Even without CLI, the extension may be available via VS Code API
            self.status.accessible = self._check_vscode_extension()

        # If not found in VS Code extensions, check for standalone
        if not self.status.installed:
            # Try alternative detection
            self._try_alternative_detection()

    def _check_vscode_extension(self) -> bool:
        """Check if Cline VS Code extension is functional."""
        try:
            # Check package.json for the extension
            ext_package = os.path.expanduser("~/.vscode/extensions/cline*/package.json")
            import glob

            matches = glob.glob(ext_package)
            if matches:
                pkg_path = matches[0]
                with open(pkg_path) as f:
                    pkg_info = json.load(f)
                # Check if extension has API exposure
                return pkg_info.get("publisher") == "cline" or "cline" in str(pkg_info).lower()
        except Exception:
            pass
        return False

    def _try_alternative_detection(self) -> None:
        """Try alternative detection methods for Cline."""
        # Check if cline is available via npx or node modules
        try:
            result = subprocess.run(
                ["npx", "cline", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.status.version = "via npx"
                self.status.installed = True
                self.status.accessible = True
        except Exception:
            pass

        # Check via Python if there's a cline package
        try:
            import importlib

            importlib.import_module("cline")
            self.status.installed = True
            self.status.accessible = True
            self.status.version = "python package available"
        except ImportError:
            pass

    def available(self) -> bool:
        """Check if Cline is available for use."""
        return self.status.installed and self.status.accessible

    def capabilities(self) -> list[str]:
        """Return list of supported capabilities."""
        if not self.available():
            return []

        base_caps = [
            "multi_file_edits",
            "run_tests",
            "create_files",
            "edit_files",
            "search_code",
            "grep_pattern",
            "execute_bash",
            "capture_output",
            "approval_management",
            "diff_generation",
        ]

        # Version-specific capabilities
        self.status.version.lower()
        # Add capabilities based on what Cline supports
        base_caps.extend(
            [
                "git_operations",
                "terminal_execution",
                "dependency_management",
                "import_handling",
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
        require_approval: bool | None = None,
    ) -> dict[str, Any]:
        """Execute a coding task via Cline.

        Args:
            task: Description of the coding task to execute
            workdir: Working directory for execution
            timeout: Maximum execution time in seconds
            capture_output: Whether to capture stdout/stderr
            require_approval: Whether human approval is required (None = auto-detect)

        Returns:
            Dictionary with execution results
        """
        # Auto-detect approval requirements if not specified
        if require_approval is None:
            require_approval = self._default_approval_policy()

        exec_path = self._resolve_executable()
        if not exec_path or not self.available():
            return {
                "success": False,
                "error": "Cline no está instalado o no es accesible",
                "exit_code": -1,
                "output": "",
                "workdir": workdir or os.getcwd(),
                "requires_approval": require_approval,
            }

        # Build the command
        # Cline can be invoked via: cline "task description"
        # Or through its API if available
        cmd = [exec_path, "execute", task]

        # Add working directory if specified
        env = os.environ.copy()
        if workdir:
            cmd.extend(["--workdir", workdir])
            env["PWD"] = workdir

        # Add approval flag if required
        if require_approval:
            cmd.append("--approval-required")

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

            # Determine if approval was needed
            actual_approval = exit_code != 0 or "approval" in (output or "").lower()

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "output": output or "",
                "workdir": workdir or os.getcwd(),
                "latency_ms": round(latency_ms, 1),
                "requires_approval": require_approval,
                "approval_actual": actual_approval,
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
                "error": "Timeout excedido durante la ejecución de Cline",
                "requires_approval": require_approval,
                "status": self.status.to_dict(),
            }

        except Exception as e:
            end_time = datetime.now(UTC)
            latency_ms = 0
            self.status.last_execution = end_time.isoformat()
            self.status.last_exit_code = -1
            self.status.latency_ms = 0

            logger.error(f"Cline execution error: {e}")
            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "workdir": workdir or os.getcwd(),
                "error": str(e),
                "requires_approval": require_approval,
                "status": self.status.to_dict(),
            }

    def _default_approval_policy(self) -> bool:
        """Determine default approval policy based on task type and configuration."""
        # Cline typically requires approval for:
        # - File modifications outside safe directories
        # - Git operations (commits, pushes)
        # - Terminal execution with destructive commands
        # - API calls that modify state

        # Default: require approval for safety
        return True

    def inspect_repository(self, repo_path: str | None = None) -> dict[str, Any]:
        """Inspect a repository structure using Cline.

        Args:
            repo_path: Path to the repository to inspect

        Returns:
            Dictionary with repository structure and metadata
        """
        workdir = repo_path or os.getcwd()
        result = self.execute_task(
            "Inspect this repository structure and provide: 1) overall project summary, 2) main directories, 3) key files, 4) technology stack detected, 5) current status of development",
            workdir=workdir,
            timeout=120,
            require_approval=False,
        )

        return {
            "repo_path": workdir,
            "inspection": result,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def run_tests(self, test_command: str | None = None, workdir: str | None = None) -> dict[str, Any]:
        """Run tests using Cline.

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
            require_approval=True,
        )

    def get_status(self) -> ClineStatus:
        """Get current status of Cline integration."""
        # Refresh capabilities
        _ = self.capabilities()
        return self.status


# Singleton instance for registry
_cline_integration: ClineIntegration | None = None


def get_cline_integration() -> ClineIntegration:
    """Get the singleton Cline integration instance."""
    global _cline_integration
    if _cline_integration is None:
        _cline_integration = ClineIntegration()
    return _cline_integration


def init_cline_integration() -> ClineIntegration:
    """Initialize and register the Cline integration."""
    global _cline_integration
    _cline_integration = ClineIntegration()
    return _cline_integration
