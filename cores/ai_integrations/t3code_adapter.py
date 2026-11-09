"""T3 Code Integration for OWNEX.

Integrates T3 Code as a remote agent control and monitoring tool within the OWNEX system.
T3 Code is a free, open-source interface for controlling AI coding agents (OpenCode, Codex, Claude Code, Cursor, etc.).

Key features:
- Detect T3 Code installation and version
- Connect to T3 Code local server or cloud
- Monitor agent sessions and status
- Remote control from Wear OS / mobile interfaces
- Capture diffs and execution results
- Telemetry can be disabled via T3CODE_TELEMETRY_ENABLED env var

Follows the PRODUCT -> DOMAIN -> APPLICATION -> INFRASTRUCTURE -> EXTERNAL WORLD architecture.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.ai_integrations.t3code_adapter")


@dataclass
class T3CodeStatus:
    """Runtime status of T3 Code integration."""

    installed: bool = False
    version: str = ""
    server_running: bool = False
    accessible: bool = False
    last_checked: str = ""
    latency_ms: float = 0.0
    last_execution: str | None = None
    last_exit_code: int | None = None
    current_session: str | None = None
    telemetry_enabled: bool = True
    error: str | None = None
    last_session_list: list | None = field(default_factory=lambda: [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "installed": self.installed,
            "version": self.version,
            "server_running": self.server_running,
            "accessible": self.accessible,
            "last_checked": self.last_checked,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
            "last_execution": self.last_execution,
            "last_exit_code": self.last_exit_code,
            "current_session": self.current_session,
            "telemetry_enabled": self.telemetry_enabled,
            "last_session_list": self.last_session_list,
        }


class T3CodeIntegration:
    """Integration adapter for T3 Code remote agent control."""

    def __init__(self):
        self.status = T3CodeStatus()
        self._exe_path: str | None = None
        self._server_url: str | None = "http://localhost:9000"
        self._detect()

    def _check_telemetry(self) -> bool:
        """Check if telemetry is enabled (respect T3CODE_TELEMETRY_ENABLED env var)."""
        env_val = os.environ.get("T3CODE_TELEMETRY_ENABLED", "")
        if env_val.lower() in ("0", "false", "no"):
            return False
        if env_val.lower() in ("1", "true", "yes"):
            return True
        # Default: respect user preference, default True for compatibility
        return True

    def _detect(self) -> None:
        """Detect T3 Code installation and server status."""
        self.status.telemetry_enabled = self._check_telemetry()
        self.status.last_checked = datetime.now(UTC).isoformat()

        # T3 Code can be used via CLI or as a local server
        # Check if t3code CLI is available
        try:
            result = subprocess.run(
                ["t3code", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # T3 Code version output
                version_line = result.stderr or result.stdout
                if "t3code" in version_line.lower() or "t3" in version_line.lower():
                    parts = version_line.strip().split()
                    ver = parts[1] if len(parts) > 1 else "unknown"
                    self.status.version = ver
                    self.status.installed = True
                    self.status.accessible = True
                else:
                    # Generic version output
                    self.status.version = version_line.strip() or "unknown"
                    self.status.installed = True
                    self.status.accessible = True
            else:
                # codex command exists but --version failed
                self.status.version = "installed (version check failed)"
                self.status.installed = True
                self.status.accessible = False
        except FileNotFoundError:
            # t3code not in PATH
            self.status.version = ""
            self.status.installed = False
            self.status.accessible = False
        except subprocess.TimeoutExpired:
            self.status.version = ""
            self.status.installed = False
            self.status.accessible = False
        except Exception as e:
            logger.warning(f"T3 Code detection error: {e}")
            self.status.version = ""
            self.status.installed = False
            self.status.accessible = False

        # Check if local server is running
        try:
            import urllib.request

            result = urllib.request.urlopen(
                f"{self._server_url}/health", timeout=3
            )
            self.status.server_running = result.status == 200
        except Exception:
            self.status.server_running = False

    def available(self) -> bool:
        """Check if T3 Code is available for use."""
        return self.status.installed and self.status.accessible

    def capabilities(self) -> list[str]:
        """Return list of supported capabilities."""
        if not self.available():
            return []

        base_caps = [
            "session_status",
            "agent_monitoring",
            "remote_control",
            "diff_visualization",
            "execution_logging",
            "session_list",
        ]

        # Add version-specific capabilities if version is known
        ver = self.status.version.lower()
        if ver and ver != "unknown":
            base_caps.extend(
                [
                    "multi_agent_monitoring",
                    "cross_platform_control",
                    "wear_os_integration",
                ]
            )

        self.status.capabilities = base_caps
        return base_caps

    def list_sessions(self) -> dict[str, Any]:
        """List active agent sessions from T3 Code."""
        if not self.available():
            return {
                "success": False,
                "error": "T3 Code no esta instalado o no es accesible",
                "sessions": [],
            }

        try:
            import urllib.request

            url = f"{self._server_url}/api/sessions"
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/json")

            start_time = datetime.now(UTC)
            response = urllib.request.urlopen(req, timeout=10)
            end_time = datetime.now(UTC)
            latency_ms = (end_time - start_time).total_seconds() * 1000

            data = json.loads(response.read().decode("utf-8"))

            self.status.last_session_list = data.get("sessions", [])
            self.status.last_exit_code = 0

            return {
                "success": True,
                "sessions": self.status.last_session_list,
                "latency_ms": round(latency_ms, 1),
                "server_url": self._server_url,
            }
        except Exception as e:
            logger.error(f"T3 Code session list error: {e}")
            self.status.last_exit_code = -1
            self.status.error = str(e)
            return {
                "success": False,
                "error": str(e),
                "sessions": [],
            }

    def get_session_status(self, session_id: str) -> dict[str, Any]:
        """Get status of a specific agent session."""
        if not self.available():
            return {
                "success": False,
                "error": "T3 Code no esta instalado o no es accesible",
                "session_status": None,
            }

        try:
            import urllib.request

            url = f"{self._server_url}/api/sessions/{session_id}/status"
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/json")

            start_time = datetime.now(UTC)
            response = urllib.request.urlopen(req, timeout=10)
            end_time = datetime.now(UTC)
            latency_ms = (end_time - start_time).total_seconds() * 1000

            data = json.loads(response.read().decode("utf-8"))

            self.status.current_session = session_id
            self.status.last_exit_code = 0

            return {
                "success": True,
                "session_status": data,
                "latency_ms": round(latency_ms, 1),
                "server_url": self._server_url,
            }
        except Exception as e:
            logger.error(f"T3 Code session status error: {e}")
            self.status.last_exit_code = -1
            self.status.error = str(e)
            return {
                "success": False,
                "error": str(e),
                "session_status": None,
            }

    def execute_remote_task(
        self,
        task: str,
        session_id: str | None = None,
        workdir: str | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Execute a task via a T3 Code agent session."""
        if not self.available():
            return {
                "success": False,
                "error": "T3 Code no esta instalado o no es accesible",
                "exit_code": -1,
                "output": "",
                "workdir": workdir or os.getcwd(),
            }

        try:
            import urllib.request
            import urllib.error

            # Prepare the task payload
            payload = {
                "task": task,
                "workdir": workdir or os.getcwd(),
                "timeout": timeout,
            }
            if session_id:
                payload["session_id"] = session_id

            url = f"{self._server_url}/api/execute"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )

            start_time = datetime.now(UTC)
            response = urllib.request.urlopen(req, timeout=timeout + 30)
            end_time = datetime.now(UTC)
            latency_ms = (end_time - start_time).total_seconds() * 1000

            data = json.loads(response.read().decode("utf-8"))

            self.status.last_execution = end_time.isoformat()
            self.status.last_exit_code = data.get("exit_code", 0)
            if latency_ms > 0:
                self.status.latency_ms = latency_ms

            return {
                "success": data.get("success", False),
                "exit_code": data.get("exit_code", -1),
                "output": data.get("output", ""),
                "workdir": workdir or os.getcwd(),
                "latency_ms": round(latency_ms, 1),
                "status": self.status.to_dict(),
            }
        except urllib.error.HTTPError as e:
            logger.error(f"T3 Code execution HTTP error: {e}")
            self.status.last_exit_code = -1
            self.status.error = f"HTTP {e.code}: {e.reason}"
            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "workdir": workdir or os.getcwd(),
                "error": self.status.error,
                "status": self.status.to_dict(),
            }
        except Exception as e:
            logger.error(f"T3 Code execution error: {e}")
            self.status.last_exit_code = -1
            self.status.error = str(e)
            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "workdir": workdir or os.getcwd(),
                "error": str(e),
                "status": self.status.to_dict(),
            }

    def get_status(self) -> T3CodeStatus:
        """Get current status of T3 Code integration."""
        # Refresh capabilities
        _ = self.capabilities()
        return self.status

    def toggle_telemetry(self, enabled: bool | None = None) -> dict[str, Any]:
        """Toggle telemetry enabled/disabled."""
        if enabled is None:
            # Toggle current state
            self.status.telemetry_enabled = not self.status.telemetry_enabled
        else:
            self.status.telemetry_enabled = enabled

        # Apply the environment variable
        os.environ["T3CODE_TELEMETRY_ENABLED"] = (
            "1" if self.status.telemetry_enabled else "0"
        )

        return {
            "success": True,
            "telemetry_enabled": self.status.telemetry_enabled,
            "message": (
                "Telemetry enabled" if self.status.telemetry_enabled else "Telemetry disabled"
            ),
        }

    def set_server_url(self, url: str) -> dict[str, Any]:
        """Set the T3 Code server URL."""
        # Normalize URL
        url = url.rstrip("/")
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"

        self._server_url = url
        # Quick health check
        try:
            import urllib.request

            req = urllib.request.Request(f"{url}/health")
            response = urllib.request.urlopen(req, timeout=3)
            self.status.server_running = response.status == 200
        except Exception:
            self.status.server_running = False

        return {
            "success": True,
            "server_url": self._server_url,
            "server_running": self.status.server_running,
        }


# Singleton instance for registry
_t3code_integration: T3CodeIntegration | None = None


def get_t3code_integration() -> T3CodeIntegration:
    """Get the singleton T3 Code integration instance."""
    global _t3code_integration
    if _t3code_integration is None:
        _t3code_integration = T3CodeIntegration()
    return _t3code_integration


def init_t3code_integration() -> T3CodeIntegration:
    """Initialize and register the T3 Code integration."""
    global _t3code_integration
    _t3code_integration = T3CodeIntegration()
    return _t3code_integration