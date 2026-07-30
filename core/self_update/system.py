"""
Core self-update system for Rastro.
Handles git pull, dependency installation, and automatic restart.
"""
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from cores.events.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SelfUpdateError(Exception):
    """Raised when self-update operations fail."""


class GitUpdater:
    """Handles git operations for self-updates."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def check_git_status(self) -> Dict[str, Any]:
        """Check current git status and available updates."""
        try:
            # Check if we're in a git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return {"status": "not_git_repo", "error": "Not a git repository"}

            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            current_branch = result.stdout.strip() if result.returncode == 0 else "unknown"

            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            has_changes = bool(result.stdout.strip()) if result.returncode == 0 else False

            # Fetch latest from remote
            result = subprocess.run(
                ["git", "fetch", "origin", current_branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Check if we're behind
            result = subprocess.run(
                ["git", "rev-list", f"HEAD..origin/{current_branch}", "--count"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            commits_behind = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip().isdigit() else 0

            return {
                "status": "ok",
                "branch": current_branch,
                "has_uncommitted_changes": has_changes,
                "commits_behind": commits_behind,
                "update_available": commits_behind > 0
            }

        except Exception as e:
            logger.error("Git status check failed: %s", e)
            return {"status": "error", "error": str(e)}

    def pull_updates(self) -> Dict[str, Any]:
        """Pull latest updates from remote."""
        try:
            result = subprocess.run(
                ["git", "pull", "origin", "--ff-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

        except Exception as e:
            logger.error("Git pull failed: %s", e)
            return {"success": False, "error": str(e)}


class DependencyInstaller:
    """Handles dependency installation and updates."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def install_python_dependencies(self) -> Dict[str, Any]:
        """Install Python dependencies from requirements.txt or pyproject.toml."""
        try:
            # Try pip install -e first (editable install)
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", "."],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return {"success": True, "method": "editable", "output": result.stdout}

            # Fallback to requirements.txt
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                return {
                    "success": result.returncode == 0,
                    "method": "requirements",
                    "output": result.stdout if result.returncode == 0 else result.stderr
                }

            return {"success": False, "error": "No installation method succeeded"}

        except Exception as e:
            logger.error("Dependency installation failed: %s", e)
            return {"success": False, "error": str(e)}

    def check_dependencies(self) -> Dict[str, Any]:
        """Check if dependencies are satisfied."""
        try:
            # Check if we can import core modules
            test_imports = [
                "fastapi",
                "uvicorn",
                "sqlalchemy",
                "pydantic",
                "cores.events.event_bus"
            ]

            missing = []
            for module in test_imports:
                try:
                    __import__(module)
                except ImportError:
                    missing.append(module)

            return {
                "status": "ok" if not missing else "missing",
                "missing": missing,
                "total_checked": len(test_imports)
            }

        except Exception as e:
            logger.error("Dependency check failed: %s", e)
            return {"status": "error", "error": str(e)}


class ProcessManager:
    """Manages process restart for self-updates."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.python_executable = sys.executable

    def get_restart_command(self) -> List[str]:
        """Get the command to restart the application."""
        # Try to find the main entry point
        entry_points = [
            self.project_root / "run.py",
            self.project_root / "api" / "main.py",
            self.project_root / "main.py",
        ]

        for entry in entry_points:
            if entry.exists():
                return [self.python_executable, str(entry)]

        # Fallback to uvicorn
        return [
            self.python_executable, "-m", "uvicorn",
            "api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000"
        ]

    def restart_application(self) -> Dict[str, Any]:
        """Restart the application process."""
        try:
            cmd = self.get_restart_command()
            logger.info("Restarting with command: %s", " ".join(cmd))

            # Start new process
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root)

            proc = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

            # Give it a moment to start
            import time
            time.sleep(2)

            # Check if process is still alive
            if proc.poll() is None:
                return {
                    "success": True,
                    "pid": proc.pid,
                    "command": " ".join(cmd)
                }
            else:
                stdout, stderr = proc.communicate()
                return {
                    "success": False,
                    "error": f"Process died immediately: {stderr.decode()}"
                }

        except Exception as e:
            logger.error("Restart failed: %s", e)
            return {"success": False, "error": str(e)}


class SelfUpdateSystem:
    """Main self-update system orchestrating all update operations."""

    def __init__(self, project_root: str = "/home/adrie/projects/Rastro"):
        self.project_root = Path(project_root)
        self.git_updater = GitUpdater(self.project_root)
        self.dependency_installer = DependencyInstaller(self.project_root)
        self.process_manager = ProcessManager(self.project_root)
        self.update_history = []

    def check_for_updates(self) -> Dict[str, Any]:
        """Check for available updates."""
        logger.info("Checking for updates...")

        git_status = self.git_updater.check_git_status()
        deps_status = self.dependency_installer.check_dependencies()

        update_available = (
            git_status.get("update_available", False) or
            deps_status.get("status") == "missing"
        )

        return {
            "update_available": update_available,
            "git_status": git_status,
            "dependencies": deps_status,
            "timestamp": str(Path.home().stat().st_mtime)
        }

    def perform_full_update(self) -> Dict[str, Any]:
        """Perform a complete self-update cycle."""
        logger.info("Starting full self-update cycle")

        results = {
            "steps": [],
            "success": True,
            "restarted": False
        }

        # Step 1: Check git status
        git_status = self.git_updater.check_git_status()
        results["steps"].append({"step": "git_check", "result": git_status})

        # Step 2: Pull updates if available
        if git_status.get("update_available", False):
            logger.info("Updates available, pulling...")
            pull_result = self.git_updater.pull_updates()
            results["steps"].append({"step": "git_pull", "result": pull_result})

            if not pull_result.get("success", False):
                results["success"] = False
                results["error"] = "Git pull failed"
                return results

        # Step 3: Install/update dependencies
        logger.info("Installing dependencies...")
        deps_result = self.dependency_installer.install_python_dependencies()
        results["steps"].append({"step": "dependencies", "result": deps_result})

        if not deps_result.get("success", False):
            results["success"] = False
            results["error"] = "Dependency installation failed"
            return results

        # Step 4: Restart application
        logger.info("Restarting application...")
        restart_result = self.process_manager.restart_application()
        results["steps"].append({"step": "restart", "result": restart_result})
        results["restarted"] = restart_result.get("success", False)

        if not restart_result.get("success", False):
            results["success"] = False
            results["error"] = "Restart failed"

        # Record in history
        self.update_history.append({
            "timestamp": str(Path.home().stat().st_mtime),
            "results": results
        })

        # Emit update event
        self._emit_update_event(results)

        return results

    def _emit_update_event(self, results: Dict[str, Any]):
        """Emit an update event to the event bus."""
        try:
            bus = get_event_bus()
            event_data = {
                "event_type": "system:update:completed",
                "success": results.get("success", False),
                "restarted": results.get("restarted", False),
                "steps_completed": len(results.get("steps", [])),
                "error": results.get("error")
            }
            bus.publish("system:update", **event_data)
            logger.debug("Update event emitted")
        except Exception as e:
            logger.warning("Failed to emit update event: %s", e)


def get_self_update_system() -> SelfUpdateSystem:
    """Get or create the self-update system instance."""
    return SelfUpdateSystem()