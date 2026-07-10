"""Hermes Automation Engine — core logic with safe mode and permission control."""

from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.hermes.config import (
    HERMES_AUTO_BACKUP,
    HERMES_BACKUP_INTERVAL_H,
    HERMES_LOG_ACTIONS,
    HERMES_SAFE_MODE,
)

logger = logging.getLogger("catseye.hermes.engine")

AUTHORIZED_COMMANDS: dict[str, dict[str, Any]] = {
    "backup": {
        "label": "System Backup",
        "description": "Run database and config backup via run.py --backup",
        "risk": "low",
        "destructive": False,
    },
    "status": {
        "label": "System Status",
        "description": "Report health of all core services and apps",
        "risk": "none",
        "destructive": False,
    },
    "health": {
        "label": "Health Check",
        "description": "Run full health check and return scores",
        "risk": "none",
        "destructive": False,
    },
    "logs": {
        "label": "Recent Logs",
        "description": "Show last N lines of audit and scheduler logs",
        "risk": "none",
        "destructive": False,
    },
    "doctor": {
        "label": "System Doctor",
        "description": "Run diagnostics: DB integrity, disk space, process health",
        "risk": "low",
        "destructive": False,
    },
    "help": {
        "label": "List Commands",
        "description": "Show available Hermes commands and their risk levels",
        "risk": "none",
        "destructive": False,
    },
}


@dataclass
class ActionResult:
    command: str
    status: str  # "ok" | "error" | "skipped" | "recommended"
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutomationEngine:
    """Hermes core engine. Executes (or recommends) authorized commands."""

    def __init__(self, safe_mode: bool | None = None) -> None:
        self.safe_mode = HERMES_SAFE_MODE if safe_mode is None else safe_mode
        self._history: list[ActionResult] = []
        self._project_root = Path(__file__).resolve().parent.parent.parent

    # ── Public API ────────────────────────────────────────────────

    def execute(self, command: str, **kwargs: Any) -> ActionResult:
        """Execute a command respecting safe mode and permissions."""
        cmd_def = AUTHORIZED_COMMANDS.get(command)
        if cmd_def is None:
            return ActionResult(
                command=command,
                status="error",
                message=f"Unknown command '{command}'. Use 'help' to list available commands.",
            )

        if self.safe_mode and cmd_def["destructive"]:
            return ActionResult(
                command=command,
                status="recommended",
                message=f"[SAFE MODE] Action '{command}' was recommended but not executed. Set HERMES_SAFE_MODE=false to allow.",
                details={"command": command, "risk": cmd_def["risk"], "destructive": True},
            )

        handler = getattr(self, f"_cmd_{command}", None)
        if handler is None:
            return ActionResult(
                command=command,
                status="error",
                message=f"Command '{command}' has no handler registered.",
            )

        try:
            result = handler(**kwargs)
        except Exception as exc:
            logger.exception("Hermes command '%s' failed", command)
            result = ActionResult(
                command=command,
                status="error",
                message=f"Command '{command}' failed: {exc}",
            )

        self._history.append(result)
        if HERMES_LOG_ACTIONS:
            self._log_action(result)

        return result

    def get_history(self, limit: int = 10) -> list[ActionResult]:
        return self._history[-limit:]

    def status_summary(self) -> dict[str, Any]:
        return {
            "engine": "Hermes v0.1.0",
            "safe_mode": self.safe_mode,
            "auto_backup": HERMES_AUTO_BACKUP,
            "backup_interval_h": HERMES_BACKUP_INTERVAL_H,
            "actions_today": len([a for a in self._history if _is_today(a.timestamp)]),
            "total_actions": len(self._history),
            "available_commands": list(AUTHORIZED_COMMANDS.keys()),
        }

    # ── Command Handlers ──────────────────────────────────────────

    def _cmd_backup(self, **kwargs: Any) -> ActionResult:
        try:
            result = subprocess.run(
                [sys.executable, "run.py", "--backup"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self._project_root,
            )
            if result.returncode == 0:
                return ActionResult(
                    command="backup",
                    status="ok",
                    message="Backup completed successfully",
                    details={"stdout": result.stdout.strip()},
                )
            return ActionResult(
                command="backup",
                status="error",
                message=f"Backup failed (exit {result.returncode})",
                details={"stderr": result.stderr.strip()},
            )
        except subprocess.TimeoutExpired:
            return ActionResult(
                command="backup",
                status="error",
                message="Backup timed out after 5 minutes",
            )

    def _cmd_status(self, **kwargs: Any) -> ActionResult:
        info: dict[str, Any] = {"python": sys.version.split()[0], "cwd": str(self._project_root)}
        try:
            import importlib

            for mod_name in ("cores.events.event_bus", "api.scheduler", "cores.identity_vault"):
                try:
                    importlib.import_module(mod_name)
                    info[mod_name.split(".")[-1]] = "loaded"
                except ImportError:
                    info[mod_name.split(".")[-1]] = "not_available"
        except Exception as exc:
            info["error"] = str(exc)
        return ActionResult(
            command="status",
            status="ok",
            message="System status collected",
            details=info,
        )

    def _cmd_health(self, **kwargs: Any) -> ActionResult:
        """Delegate to Health Center if available, otherwise report basic info."""
        info: dict[str, Any] = {}
        try:
            from core.health.engine import get_health_center

            center = get_health_center()
            summary = center.summary()
            info["health_score"] = summary.get("score", "unknown")
            info["checks"] = summary.get("checks", [])
        except ImportError:
            info["health_score"] = "health_center_not_available"
        except Exception as exc:
            info["health_score"] = f"error: {exc}"
        return ActionResult(
            command="health",
            status="ok",
            message="Health check complete",
            details=info,
        )

    def _cmd_logs(self, lines: int = 50, **kwargs: Any) -> ActionResult:
        log_dirs = [
            Path.home() / ".orion" / "audit.jsonl",
            self._project_root / "logs",
        ]
        entries: list[str] = []
        for log_path in log_dirs:
            if log_path.is_file():
                try:
                    with open(log_path) as f:
                        all_lines = f.readlines()
                        tail = [line.rstrip() for line in all_lines[-lines:]]
                        entries.extend(tail)
                except Exception as exc:
                    entries.append(f"Error reading {log_path}: {exc}")
            elif log_path.is_dir():
                for lf in sorted(log_path.glob("*.log*"))[-3:]:
                    try:
                        with open(lf) as f:
                            all_lines = f.readlines()
                            tail = [line.rstrip() for line in all_lines[-lines:]]
                            entries.extend(tail)
                    except Exception as exc:
                        entries.append(f"Error reading {lf}: {exc}")
        return ActionResult(
            command="logs",
            status="ok",
            message=f"Retrieved {len(entries)} log entries",
            details={"entries": entries[:lines]},
        )

    def _cmd_doctor(self, **kwargs: Any) -> ActionResult:
        findings: dict[str, Any] = {}
        issues: list[str] = []

        # ── Disk ────────────────────────────────────────────────────
        try:
            import shutil

            usage = shutil.disk_usage(self._project_root)
            findings["disk_free_gb"] = round(usage.free / (1024**3), 2)
            findings["disk_total_gb"] = round(usage.total / (1024**3), 2)
            findings["disk_usage_pct"] = round(usage.used / usage.total * 100, 1)
            if usage.free / (1024**3) < 1:
                issues.append("Disk space critically low (< 1GB free)")
        except Exception as exc:
            findings["disk_error"] = str(exc)

        # ── Databases ───────────────────────────────────────────────
        from core.maintenance.engine import MaintenanceEngine

        try:
            summary = MaintenanceEngine().summary()
            findings["databases"] = summary.get("databases", [])
            findings["total_db_count"] = summary.get("total_db_count", 0)
            findings["total_db_size_mb"] = summary.get("total_size_mb", 0)
            for db in summary.get("databases", []):
                if db.get("size_mb", 0) > 200:
                    issues.append(f"{db['name']} > 200MB — consider VACUUM")
        except Exception as exc:
            findings["db_error"] = str(exc)

        # ── Backup health ────────────────────────────────────────────
        try:
            from core.backup.engine import backup_status

            bs = backup_status()
            findings["total_backups"] = bs.get("total_backups", 0)
            findings["latest_backup"] = bs.get("latest_backup")
            latest = bs.get("latest_backup")
            if latest:
                from datetime import datetime, timezone

                created = latest.get("created_at", "")
                if created:
                    try:
                        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(created)).total_seconds() / 3600
                        findings["backup_age_hours"] = round(age_h, 1)
                        if age_h > 48:
                            issues.append(f"Last backup {round(age_h, 1)}h ago — run --backup")
                    except Exception:
                        pass
            else:
                issues.append("No backups found — run --backup")
        except Exception as exc:
            findings["backup_error"] = str(exc)

        # ── Update check ─────────────────────────────────────────────
        try:
            from core.update.engine import UpdateManager

            up = UpdateManager().status()
            findings["current_version"] = up.get("current_version")
            findings["update_available"] = up.get("update_available", False)
            if up.get("update_available"):
                issues.append(f"Update available: {up.get('remote_version')} (current: {up.get('current_version')})")
        except Exception as exc:
            findings["update_error"] = str(exc)

        # ── System ──────────────────────────────────────────────────
        findings["safe_mode"] = self.safe_mode
        findings["python"] = sys.version
        findings["cwd"] = str(self._project_root)

        # ── Health score 0-100 ───────────────────────────────────────
        score = 100
        score -= len(issues) * 10
        score = max(0, min(100, score))
        findings["health_score"] = score

        return ActionResult(
            command="doctor",
            status="ok",
            message=f"Health score: {score}/100" + (f" — issues: {'; '.join(issues)}" if issues else ""),
            details={"findings": findings, "issues": issues},
        )

    def _cmd_help(self, **kwargs: Any) -> ActionResult:
        commands = []
        for name, cmd in AUTHORIZED_COMMANDS.items():
            commands.append(
                {
                    "name": name,
                    "description": cmd["description"],
                    "risk": cmd["risk"],
                    "destructive": cmd["destructive"],
                }
            )
        return ActionResult(
            command="help",
            status="ok",
            message=f"Available commands ({len(commands)}): {', '.join(c['name'] for c in commands)}",
            details={"safe_mode": self.safe_mode, "commands": commands},
        )

    # ── Internal ──────────────────────────────────────────────────

    def _log_action(self, result: ActionResult) -> None:
        try:
            log_path = Path.home() / ".orion" / "hermes_actions.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            import json

            with open(log_path, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "command": result.command,
                            "status": result.status,
                            "message": result.message,
                            "timestamp": result.timestamp,
                            "safe_mode": self.safe_mode,
                        }
                    )
                    + "\n"
                )
        except Exception as exc:
            logger.warning("Failed to log Hermes action: %s", exc)


def _is_today(iso_ts: str) -> bool:
    try:
        return datetime.fromisoformat(iso_ts).date() == datetime.now(timezone.utc).date()
    except Exception:
        return False


def run_health_check() -> dict[str, Any]:
    """Scheduler entry point — runs health check and returns status."""
    engine = AutomationEngine()
    result = engine.execute("health")
    return {"command": "health", "status": result.status, "message": result.message}
