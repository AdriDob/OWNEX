"""MERLIN Engine — Automation & Operations with EventBus, permission system, and security."""

from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.hermes.config import (
    HERMES_AUTO_BACKUP,
    HERMES_BACKUP_INTERVAL_H,
    HERMES_LOG_ACTIONS,
    HERMES_SAFE_MODE,
)
from apps.hermes.permissions import ActionHistory, ActionRecord, evaluate_action
from apps.hermes.publisher import HermesEventPublisher
from apps.hermes.security import validate_action
from apps.hermes.tools import get_tool_registry

logger = logging.getLogger("catseye.merlin.engine")

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
    "tools": {
        "label": "Desktop Tools",
        "description": "List all available desktop tools (winget, process, system, etc.)",
        "risk": "none",
        "destructive": False,
    },
    "snapshot": {
        "label": "System Snapshot",
        "description": "CPU, RAM, disk, network usage snapshot",
        "risk": "none",
        "destructive": False,
    },
    "top": {
        "label": "Top Processes",
        "description": "List top processes by RAM usage",
        "risk": "none",
        "destructive": False,
    },
    "ps": {
        "label": "Process List",
        "description": "List all running processes",
        "risk": "none",
        "destructive": False,
    },
    "packages": {
        "label": "Installed Packages",
        "description": "List installed packages via winget/choco/scoop",
        "risk": "none",
        "destructive": False,
    },
    "disks": {
        "label": "Disk Usage",
        "description": "Show disk usage for all volumes",
        "risk": "none",
        "destructive": False,
    },
    "services": {
        "label": "List Services",
        "description": "List all system services",
        "risk": "none",
        "destructive": False,
    },
    "kill": {
        "label": "Kill Process",
        "description": "Terminate a process by PID",
        "risk": "high",
        "destructive": True,
    },
}


@dataclass
class ActionResult:
    command: str
    status: str  # "ok" | "error" | "skipped" | "recommended"
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AutomationEngine:
    """MERLIN core engine. Executes (or recommends) authorized commands with EventBus + permission system."""

    def __init__(self, safe_mode: bool | None = None, event_bus: Any | None = None) -> None:
        self.safe_mode = HERMES_SAFE_MODE if safe_mode is None else safe_mode
        self._history: list[ActionResult] = []
        self._project_root = Path(__file__).resolve().parent.parent.parent
        self._tools = get_tool_registry()
        self._publisher = HermesEventPublisher(event_bus)
        self._action_history = ActionHistory()

    # ── Public API ────────────────────────────────────────────────

    def execute(self, command: str, force: bool = False, **kwargs: Any) -> ActionResult:
        """Execute a command respecting safe mode, permissions, and security checks.

        Args:
            command: The Hermes command name.
            force: If True, skip permission confirmation (for pre-approved actions).
            **kwargs: Arguments passed to the command handler.

        Returns:
            ActionResult with status and details.
        """
        cmd_def = AUTHORIZED_COMMANDS.get(command)
        if cmd_def is None:
            return ActionResult(
                command=command,
                status="error",
                message=f"Unknown command '{command}'. Use 'help' to list available commands.",
            )

        # 1. Security validation
        violations = validate_action(command, **kwargs)
        if violations:
            self._publisher.security_blocked(command, reason="; ".join(violations), details={"violations": violations})
            self._record_history(
                command,
                "blocked",
                risk=cmd_def["risk"],
                destructive=cmd_def["destructive"],
                message="; ".join(violations),
            )
            return ActionResult(
                command=command,
                status="error",
                message="Security check failed: " + "; ".join(violations),
                details={"violations": violations},
            )

        # 2. Permission evaluation
        perm = evaluate_action(command, self.safe_mode, force=force)
        self._publisher.action_requested(
            command, risk=perm.risk, destructive=perm.destructive, reason=perm.reason or "user requested"
        )

        if not perm.allowed:
            self._publisher.permission_required(command, risk=perm.risk, impact=perm.impact)
            self._publisher.action_failed(
                command, error=perm.reason or "Permission denied", details={"blocked_by": perm.blocked_by}
            )
            self._record_history(
                command,
                "denied",
                risk=perm.risk,
                destructive=perm.destructive,
                message=perm.reason or "Permission denied",
            )
            return ActionResult(
                command=command,
                status="recommended" if perm.blocked_by == "safe_mode" else "error",
                message=f"[HERMES] {perm.reason or 'Action blocked'} — use force=True to override.",
                details={
                    "risk": perm.risk,
                    "destructive": perm.destructive,
                    "reason": perm.reason,
                    "blocked_by": perm.blocked_by,
                },
            )

        # 3. Check handler exists
        handler = getattr(self, f"_cmd_{command}", None)
        if handler is None:
            return ActionResult(
                command=command,
                status="error",
                message=f"Command '{command}' has no handler registered.",
            )

        # 4. Execute
        self._publisher.action_started(command, **kwargs)
        try:
            result = handler(**kwargs)
        except Exception as exc:
            logger.exception("Hermes command '%s' failed", command)
            self._publisher.action_failed(command, error=str(exc), details={"kwargs": kwargs})
            self._record_history(
                command, "failed", risk=cmd_def["risk"], destructive=cmd_def["destructive"], message=str(exc)
            )
            return ActionResult(
                command=command,
                status="error",
                message=f"Command '{command}' failed: {exc}",
            )

        # 5. Record completion
        self._publisher.action_completed(command, status=result.status, message=result.message, details=result.details)
        self._record_history(
            command, result.status, risk=cmd_def["risk"], destructive=cmd_def["destructive"], message=result.message
        )
        self._history.append(result)
        if HERMES_LOG_ACTIONS:
            self._log_action(result)

        return result

    def _record_history(
        self, command: str, status: str, risk: str = "none", destructive: bool = False, message: str = ""
    ) -> None:
        self._action_history.record(
            ActionRecord(
                command=command,
                status=status,
                risk=risk,
                destructive=destructive,
                message=message,
            )
        )

    def get_action_history(self, limit: int = 20) -> list[ActionRecord]:
        return self._action_history.recent(limit=limit)

    def get_history(self, limit: int = 10) -> list[ActionResult]:
        return self._history[-limit:]

    def status_summary(self) -> dict[str, Any]:
        return {
            "engine": "MERLIN v0.4.0",
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
            info["health_score"] = round(summary.get("score", 0) * 100)
            info["checks_passed"] = summary.get("checks_passed", 0)
            info["checks_failed"] = summary.get("checks_failed", 0)
            info["categories"] = summary.get("categories", {})
            info["last_run"] = summary.get("last_run")
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
                from datetime import datetime

                created = latest.get("created_at", "")
                if created:
                    try:
                        age_h = (datetime.now(UTC) - datetime.fromisoformat(created)).total_seconds() / 3600
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

    # ── Desktop Tool Commands ────────────────────────────────────

    def _cmd_tools(self, **kwargs: Any) -> ActionResult:
        available = self._tools.list_available()
        names = [t["name"] for t in available if t["available"]]
        return ActionResult(
            command="tools",
            status="ok",
            message=f"{len(names)} tools available: {', '.join(names)}",
            details={"tools": available},
        )

    def _cmd_snapshot(self, **kwargs: Any) -> ActionResult:
        mon = self._tools.get("system")
        if mon is None:
            return ActionResult(command="snapshot", status="error", message="System monitor not available")
        result = mon.snapshot()
        if result.success:
            return ActionResult(command="snapshot", status="ok", message="System snapshot", details=result.data)
        return ActionResult(command="snapshot", status="error", message=result.message)

    def _cmd_top(self, limit: int = 10, **kwargs: Any) -> ActionResult:
        pm = self._tools.get("process")
        if pm is None:
            return ActionResult(command="top", status="error", message="Process manager not available")
        result = pm.top_memory(limit=limit)
        if result.success:
            return ActionResult(command="top", status="ok", message=result.message, details=result.data)
        return ActionResult(command="top", status="error", message=result.message)

    def _cmd_ps(self, **kwargs: Any) -> ActionResult:
        pm = self._tools.get("process")
        if pm is None:
            return ActionResult(command="ps", status="error", message="Process manager not available")
        result = pm.list_all()
        if result.success:
            return ActionResult(command="ps", status="ok", message=result.message, details=result.data)
        return ActionResult(command="ps", status="error", message=result.message)

    def _cmd_packages(self, manager: str = "winget", **kwargs: Any) -> ActionResult:
        tool = self._tools.get(manager)
        if tool is None:
            return ActionResult(
                command="packages",
                status="error",
                message=f"Package manager '{manager}' not available. Try: winget, choco, scoop",
            )
        result = tool.list_installed()
        if result.success:
            return ActionResult(command="packages", status="ok", message=result.message, details=result.data)
        return ActionResult(command="packages", status="error", message=result.message)

    def _cmd_disks(self, **kwargs: Any) -> ActionResult:
        fm = self._tools.get("files")
        if fm is None:
            return ActionResult(command="disks", status="error", message="File manager not available")
        result = fm.disk_usage()
        if result.success:
            return ActionResult(command="disks", status="ok", message=result.message, details=result.data)
        return ActionResult(command="disks", status="error", message=result.message)

    def _cmd_kill(self, pid: int, **kwargs: Any) -> ActionResult:
        pm = self._tools.get("process")
        if pm is None:
            return ActionResult(command="kill", status="error", message="Process manager not available")
        result = pm.kill(pid)
        return ActionResult(
            command="kill",
            status="ok" if result.success else "error",
            message=result.message,
            details=result.data,
        )

    def _cmd_services(self, **kwargs: Any) -> ActionResult:
        sm = self._tools.get("service")
        if sm is None:
            return ActionResult(command="services", status="error", message="Service manager not available")
        result = sm.list_all()
        if result.success:
            return ActionResult(command="services", status="ok", message=result.message, details=result.data)
        return ActionResult(command="services", status="error", message=result.message)

    # ── Internal ──────────────────────────────────────────────────

    def _log_action(self, result: ActionResult) -> None:
        try:
            log_path = Path.home() / ".orion" / "merlin_actions.jsonl"
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
            logger.warning("Failed to log MERLIN action: %s", exc)


def _is_today(iso_ts: str) -> bool:
    try:
        return datetime.fromisoformat(iso_ts).date() == datetime.now(UTC).date()
    except Exception:
        return False


def run_health_check() -> dict[str, Any]:
    """Scheduler entry point — runs health check and returns status."""
    engine = AutomationEngine()
    result = engine.execute("health")
    return {"command": "health", "status": result.status, "message": result.message}
