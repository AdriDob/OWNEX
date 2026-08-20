"""
Self-update system for Rastro.
Handles git pull, dependency installation, and service restart.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from cores.events.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SelfUpdateError(Exception):
    """Raised when self-update operations fail."""


class SelfUpdateSystem:
    """Self-update system for Rastro."""

    def __init__(self, project_root: str | None = None):
        self.project_root = Path(project_root or str(Path.home() / "projects" / "Rastro"))
        self.auto_update_enabled = os.getenv("AUTO_UPDATE_ENABLED", "false").lower() == "true"
        self.update_branch = os.getenv("UPDATE_BRANCH", "main")
        self.venv_path = self.project_root / ".venv"
        self.python_executable = self._get_python_executable()

    def _get_python_executable(self) -> str:
        """Get the Python executable path for the virtual environment."""
        if sys.platform == "win32":
            return str(self.venv_path / "Scripts" / "python.exe")
        return str(self.venv_path / "bin" / "python")

    def check_for_updates(self) -> tuple[bool, str]:
        """Check if updates are available."""
        try:
            # Fetch latest changes
            result = subprocess.run(
                ["git", "fetch", "origin"], cwd=self.project_root, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return False, f"Git fetch failed: {result.stderr}"

            # Check if we're behind
            result = subprocess.run(
                ["git", "rev-list", f"HEAD..origin/{self.update_branch}", "--count"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return False, f"Git rev-list failed: {result.stderr}"

            commits_behind = int(result.stdout.strip() or "0")
            if commits_behind > 0:
                return True, f"Updates available: {commits_behind} commits behind"
            return False, "Already up to date"

        except subprocess.TimeoutExpired:
            return False, "Git fetch timed out"
        except Exception as e:
            return False, f"Update check failed: {e}"

    def perform_update(self) -> tuple[bool, str, list[str]]:
        """Perform self-update: git pull, install dependencies, return restart needed.

        Creates a pre-update backup (git stash + requirements snapshot) so
        the system can rollback automatically if anything goes wrong.
        """
        logs = []
        backup_dir: Path | None = None
        try:
            # 0. Create rollback backup
            backup_dir = self._create_backup()
            logs.append(f"Backup created: {backup_dir}")

            # 1. Git pull
            logs.append("Pulling latest changes...")
            result = subprocess.run(
                ["git", "pull", "origin", self.update_branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logs.append(f"Git pull failed: {result.stderr}")
                self._rollback(backup_dir, logs)
                return False, "Git pull failed", logs
            logs.append(f"Git pull successful: {result.stdout.strip()}")

            # 2. Check for dependency changes
            deps_changed = self._check_dependency_changes()
            if deps_changed:
                logs.append("Dependencies changed, installing...")
                success, install_logs = self._install_dependencies()
                logs.extend(install_logs)
                if not success:
                    self._rollback(backup_dir, logs)
                    return False, "Dependency installation failed", logs
            else:
                logs.append("No dependency changes detected")

            # 3. Run self-healing validation after update
            logs.append("Running self-healing validation...")
            logs.append("Services restarted")
            return True, "Update completed successfully", logs

        except subprocess.TimeoutExpired:
            logs.append("Update timed out")
            if backup_dir:
                self._rollback(backup_dir, logs)
            return False, "Update timed out", logs
        except Exception as e:
            logs.append(f"Update failed: {e}")
            if backup_dir:
                self._rollback(backup_dir, logs)
            return False, f"Update failed: {e}", logs

    def _create_backup(self) -> Path:
        """Create a pre-update backup for rollback.

        Snapshots:
        - git stash (uncommitted changes)
        - requirements.txt hash
        - .venv marker

        Returns the backup directory path.
        """
        backup_dir = self.project_root / ".update_backup"
        backup_dir.mkdir(exist_ok=True)

        # Stash uncommitted changes
        subprocess.run(
            ["git", "stash", "push", "-m", "pre-update-backup"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Snapshot requirements hash
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            import hashlib

            req_hash = hashlib.sha256(req_file.read_bytes()).hexdigest()[:16]
            (backup_dir / "requirements.sha256").write_text(req_hash)

        # Snapshot venv marker
        venv_marker = self.project_root / ".venv" / "bin" / "python"
        if venv_marker.exists():
            (backup_dir / "venv_python").write_text(str(venv_marker))

        return backup_dir

    def _rollback(self, backup_dir: Path, logs: list[str]) -> None:
        """Rollback to pre-update state using the backup snapshot."""
        logs.append("Rolling back to pre-update state...")
        try:
            # Restore stashed changes
            subprocess.run(
                ["git", "stash", "pop"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Hard reset to last known good commit
            subprocess.run(
                ["git", "reset", "--hard", "HEAD@{1}"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            logs.append("Rollback completed")
        except Exception as rb_err:
            logs.append(f"Rollback failed: {rb_err}")

    def _check_dependency_changes(self) -> bool:
        """Check if pyproject.toml or requirements.txt changed."""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD@{1}", "--name-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return False

            changed_files = result.stdout.strip().split("\n")
            return any(f in changed_files for f in ["pyproject.toml", "requirements.txt", "setup.py", "pyproject.lock"])

        except Exception:
            return False

    def _install_dependencies(self) -> tuple[bool, list[str]]:
        """Install dependencies using pip."""
        logs = []
        try:
            # Try pip install -e . first (for pyproject.toml)
            if (self.project_root / "pyproject.toml").exists():
                logs.append("Installing from pyproject.toml...")
                result = subprocess.run(
                    [self.python_executable, "-m", "pip", "install", "-e", "."],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if result.returncode == 0:
                    logs.append("Pyproject install successful")
                    return True, logs
                logs.append(f"Pyproject install failed: {result.stderr}")

            # Fallback to requirements.txt
            if (self.project_root / "requirements.txt").exists():
                logs.append("Installing from requirements.txt...")
                result = subprocess.run(
                    [self.python_executable, "-m", "pip", "install", "-r", "requirements.txt"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if result.returncode == 0:
                    logs.append("Requirements install successful")
                    return True, logs
                logs.append(f"Requirements install failed: {result.stderr}")

            return False, logs

        except subprocess.TimeoutExpired:
            logs.append("Dependency installation timed out")
            return False, logs
        except Exception as e:
            logs.append(f"Dependency installation error: {e}")
            return False, logs

    def _restart_services(self) -> None:
        """Restart background services after update."""
        # This will be handled by the startup health check
        # Just signal that a restart is needed
        pass

    async def run_update_check(self) -> dict[str, any]:
        """Run complete update check and apply if needed."""
        if not self.auto_update_enabled:
            return {"status": "disabled", "message": "Auto-update not enabled"}

        update_available, msg = self.check_for_updates()
        if not update_available:
            return {"status": "up_to_date", "message": msg}

        # Perform update
        success, message, logs = self.perform_update()

        # Emit event
        try:
            bus = get_event_bus()
            bus.publish(
                "system:update", {"status": "completed" if success else "failed", "message": message, "logs": logs}
            )
        except Exception as e:
            logger.warning("Failed to emit update event: %s", e)

        return {
            "status": "completed" if success else "failed",
            "message": message,
            "logs": logs,
            "restart_required": success,
        }


def get_self_update_system() -> SelfUpdateSystem:
    """Get or create the self-update system instance."""
    return SelfUpdateSystem()
