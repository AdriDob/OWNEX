from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from core.self_update.models import UpdateInfo, UpdateResult, UpdateStatus

logger = logging.getLogger("ownex.self_update")


class SelfUpdateEngine:
    """Autonomous self-updater for OWNEX — checks, pulls, installs, restarts."""

    name = "self_update"

    def __init__(self, project_dir: str | None = None) -> None:
        self.project_dir = Path(project_dir or os.getcwd())
        self.status = UpdateStatus.IDLE
        self._log: list[str] = []

    def _log_msg(self, msg: str) -> None:
        self._log.append(msg)
        logger.info("[UPDATE] %s", msg)

    def _read_version(self) -> str:
        version_file = self.project_dir / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
        return "unknown"

    def check_for_update(self) -> UpdateInfo:
        """Check if a newer version is available on the remote."""
        self.status = UpdateStatus.CHECKING
        self._log.clear()

        current = self._read_version()
        self._log_msg(f"Current version: {current}")

        try:
            result = subprocess.run(
                ["git", "fetch", "origin", "main"],
                capture_output=True,
                text=True,
                cwd=str(self.project_dir),
                timeout=30,
            )
            if result.returncode != 0:
                self._log_msg(f"Git fetch failed: {result.stderr}")
                return UpdateInfo(current_version=current)

            behind_result = subprocess.run(
                ["git", "rev-list", "HEAD..origin/main", "--count"],
                capture_output=True,
                text=True,
                cwd=str(self.project_dir),
                timeout=10,
            )
            commits_behind = 0
            if behind_result.returncode == 0:
                commits_behind = int(behind_result.stdout.strip() or "0")

            self._log_msg(f"Commits behind: {commits_behind}")

            return UpdateInfo(
                current_version=current,
                commits_behind=commits_behind,
                has_update=commits_behind > 0,
            )
        except Exception as e:
            self._log_msg(f"Check failed: {e}")
            return UpdateInfo(current_version=current)

    def update(self, auto_restart: bool = False) -> UpdateResult:
        """Full update cycle: check → pull → install deps → migrate → restart."""
        self._log.clear()
        self.status = UpdateStatus.CHECKING

        info = self.check_for_update()
        if not info.has_update:
            self._log_msg("Already up to date")
            return UpdateResult(success=True, log=self._log)

        self._log_msg(f"Update available: {info.commits_behind} commits behind")

        result = UpdateResult(success=True, log=self._log)

        self.status = UpdateStatus.PULLING
        if self._git_pull():
            result.pulled = True
        else:
            result.success = False
            result.error = "Git pull failed"
            return result

        self.status = UpdateStatus.INSTALLING
        if self._install_deps():
            result.dependencies_installed = True
        else:
            self._log_msg("Dependency install had warnings (non-fatal)")

        self.status = UpdateStatus.MIGRATING
        if self._run_migrations():
            result.migrated = True

        if auto_restart:
            self.status = UpdateStatus.RESTARTING
            self._restart()
            result.restarted = True

        self.status = UpdateStatus.DONE
        self._log_msg("Update complete")
        return result

    def _git_pull(self) -> bool:
        self._log_msg("Pulling latest changes...")
        try:
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                capture_output=True,
                text=True,
                cwd=str(self.project_dir),
                timeout=60,
            )
            if result.returncode == 0:
                self._log_msg("Git pull successful")
                return True
            self._log_msg(f"Git pull failed: {result.stderr}")
            return False
        except Exception as e:
            self._log_msg(f"Git pull error: {e}")
            return False

    def _install_deps(self) -> bool:
        self._log_msg("Installing dependencies...")
        venv_python = self.project_dir / ".venv" / "bin" / "python"
        python_cmd = str(venv_python) if venv_python.exists() else sys.executable

        try:
            result = subprocess.run(
                [python_cmd, "-m", "pip", "install", "-e", ".", "--quiet"],
                capture_output=True,
                text=True,
                cwd=str(self.project_dir),
                timeout=120,
            )
            if result.returncode == 0:
                self._log_msg("Dependencies installed")
                return True
            self._log_msg(f"Pip install warning: {result.stderr[:200]}")
            return False
        except Exception as e:
            self._log_msg(f"Install error: {e}")
            return False

    def _run_migrations(self) -> bool:
        self._log_msg("Checking for migrations...")
        migrate_script = self.project_dir / "scripts" / "migrate.py"
        if not migrate_script.exists():
            self._log_msg("No migration script found (skipping)")
            return True

        venv_python = self.project_dir / ".venv" / "bin" / "python"
        python_cmd = str(venv_python) if venv_python.exists() else sys.executable

        try:
            result = subprocess.run(
                [python_cmd, str(migrate_script)],
                capture_output=True,
                text=True,
                cwd=str(self.project_dir),
                timeout=30,
            )
            if result.returncode == 0:
                self._log_msg("Migrations complete")
                return True
            self._log_msg(f"Migration warning: {result.stderr[:200]}")
            return False
        except Exception as e:
            self._log_msg(f"Migration error: {e}")
            return False

    def _restart(self) -> None:
        self._log_msg("Restarting OWNEX...")
        os.execv(sys.executable, [sys.executable, "-m", "api.main"])

    def health(self) -> dict[str, str]:
        return {
            "status": "ok",
            "name": self.name,
            "current_version": self._read_version(),
            "status": self.status,
            "project_dir": str(self.project_dir),
        }
