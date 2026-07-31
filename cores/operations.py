"""24/7 Operations — watchdog, recovery, backups, storage cleanup, doctor command.

Provides continuous operation capabilities for OWNEX.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from core.events.event_bus import get_core_event_bus

logger = logging.getLogger("ownex.operations")


class ComponentState(Enum):
    """Component health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STARTING = "starting"
    STOPPING = "stopping"


@dataclass
class ComponentHealth:
    """Health status of a component."""

    name: str
    state: ComponentState = ComponentState.UNKNOWN
    last_check: datetime = field(default_factory=lambda: datetime.now(UTC))
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3


@dataclass
class BackupInfo:
    """Backup metadata."""

    id: str
    path: Path
    created_at: datetime
    size_bytes: int
    components: list[str]
    checksum: str = ""


@dataclass
class DoctorCheck:
    """Individual health check result."""

    name: str
    passed: bool
    message: str
    severity: str  # info, warning, critical
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DoctorReport:
    """Complete doctor report."""

    timestamp: datetime
    overall_healthy: bool
    checks: list[DoctorCheck]
    summary: str
    recommendations: list[str]


class Watchdog:
    """Monitors critical components and attempts recovery."""

    def __init__(
        self,
        check_interval: int = 30,
        event_bus=None,
    ):
        self.check_interval = check_interval
        self._components: dict[str, ComponentHealth] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._recovery_handlers: dict[str, Callable[[], asyncio.coroutine]] = {}
        self.event_bus = event_bus or get_core_event_bus()

    def register_component(
        self,
        name: str,
        checker: Callable[[], asyncio.coroutine],
        recovery: Callable[[], asyncio.coroutine] | None = None,
        max_recovery_attempts: int = 3,
    ) -> None:
        """Register a component for monitoring."""
        self._components[name] = ComponentHealth(
            name=name,
            max_recovery_attempts=max_recovery_attempts,
        )
        self._recovery_handlers[name] = recovery
        # Run initial check
        asyncio.create_task(self._check_component(name, checker))

    async def start(self) -> None:
        """Start the watchdog."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Watchdog started (interval: %ds)", self.check_interval)

    async def stop(self) -> None:
        """Stop the watchdog."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Watchdog stopped")

    async def _monitor_loop(self) -> None:
        """Periodic monitoring loop."""
        while self._running:
            try:
                await self._check_all_components()
            except Exception as e:
                logger.error("Watchdog check failed: %s", e)

            await asyncio.sleep(self.check_interval)

    async def _check_all_components(self) -> None:
        """Check all registered components."""
        for name, component in self._components.items():
            # Component checkers are called during registration
            # Here we just evaluate state
            if component.state == ComponentState.UNHEALTHY:
                await self._attempt_recovery(name)

    async def _check_component(self, name: str, checker: Callable[[], asyncio.coroutine]) -> None:
        """Check a single component."""
        component = self._components[name]
        try:
            result = await checker()
            if isinstance(result, ComponentHealth):
                component.state = result.state
                component.message = result.message
                component.details = result.details
            elif isinstance(result, dict):
                component.state = ComponentState(result.get("state", "unknown"))
                component.message = result.get("message", "")
                component.details = result.get("details", {})
            else:
                component.state = ComponentState.HEALTHY
                component.message = "OK"
            component.last_check = datetime.now(UTC)
            component.recovery_attempts = 0
        except Exception as e:
            component.state = ComponentState.UNHEALTHY
            component.message = f"Check failed: {e}"
            component.last_check = datetime.now(UTC)
            logger.error("Component %s check failed: %s", name, e)

            self.event_bus.publish(
                "operations:component_unhealthy",
                {
                    "component": name,
                    "error": str(e),
                },
            )

    async def _attempt_recovery(self, name: str) -> None:
        """Attempt to recover a failed component."""
        component = self._components[name]
        recovery = self._recovery_handlers.get(name)

        if not recovery or component.recovery_attempts >= component.max_recovery_attempts:
            logger.warning("Recovery not available or max attempts reached for %s", name)
            return

        component.recovery_attempts += 1
        logger.info(
            "Attempting recovery %d/%d for %s", component.recovery_attempts, component.max_recovery_attempts, name
        )

        self.event_bus.publish(
            "operations:recovery_started",
            {
                "component": name,
                "attempt": component.recovery_attempts,
            },
        )

        try:
            await recovery()
            # Re-check after recovery
            component.state = ComponentState.STARTING
            self.event_bus.publish(
                "operations:recovery_success",
                {
                    "component": name,
                    "attempt": component.recovery_attempts,
                },
            )
        except Exception as e:
            logger.error("Recovery failed for %s: %s", name, e)
            self.event_bus.publish(
                "operations:recovery_failed",
                {
                    "component": name,
                    "attempt": component.recovery_attempts,
                    "error": str(e),
                },
            )


class BackupManager:
    """Manages system backups."""

    def __init__(self, backup_dir: Path = Path("backups")):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._backups: list[BackupInfo] = []
        self._max_backups = 30
        self.event_bus = get_core_event_bus()

    async def create_backup(self, name: str | None = None) -> BackupInfo:
        """Create a backup of critical data."""
        timestamp = datetime.now(UTC)
        backup_id = name or f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)

        components = []
        total_size = 0

        # Backup database
        db_path = Path("data/cateye.db")
        if db_path.exists():
            import shutil

            shutil.copy2(db_path, backup_path / "cateye.db")
            components.append("database")
            total_size += db_path.stat().st_size

        # Backup config
        config_dir = Path("config")
        if config_dir.exists():
            import shutil

            shutil.copytree(config_dir, backup_path / "config", dirs_exist_ok=True)
            components.append("config")
            for f in (backup_path / "config").rglob("*"):
                if f.is_file():
                    total_size += f.stat().st_size

        # Backup logs (last 1000 lines each)
        log_dir = Path("logs")
        if log_dir.exists():
            (backup_path / "logs").mkdir(exist_ok=True)
            for log_file in log_dir.glob("*.log"):
                try:
                    with open(log_file) as f:
                        lines = f.readlines()[-1000:]
                    with open(backup_path / "logs" / log_file.name, "w") as f:
                        f.writelines(lines)
                    components.append("logs")
                    total_size += (backup_path / "logs" / log_file.name).stat().st_size
                except Exception:
                    pass

        # Create manifest
        manifest = {
            "id": backup_id,
            "created_at": timestamp.isoformat(),
            "components": components,
            "size_bytes": total_size,
        }
        with open(backup_path / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Calculate checksum
        checksum = self._calculate_checksum(backup_path)

        info = BackupInfo(
            id=backup_id,
            path=backup_path,
            created_at=timestamp,
            size_bytes=total_size,
            components=components,
            checksum=checksum,
        )

        self._backups.append(info)
        self._prune_old_backups()

        self.event_bus.publish(
            "operations:backup_created",
            {
                "backup_id": backup_id,
                "size_bytes": total_size,
                "components": components,
            },
        )

        logger.info("Backup created: %s (%d bytes, components: %s)", backup_id, total_size, components)
        return info

    async def restore_backup(self, backup_id: str) -> bool:
        """Restore from a backup."""
        backup = next((b for b in self._backups if b.id == backup_id), None)
        if not backup:
            logger.error("Backup not found: %s", backup_id)
            return False

        # Verify checksum
        if self._calculate_checksum(backup.path) != backup.checksum:
            logger.error("Backup checksum mismatch: %s", backup_id)
            return False

        try:
            # Restore database
            db_backup = backup.path / "cateye.db"
            if db_backup.exists():
                import shutil

                shutil.copy2(db_backup, "data/cateye.db")

            # Restore config
            config_backup = backup.path / "config"
            if config_backup.exists():
                import shutil

                if Path("config").exists():
                    shutil.rmtree("config")
                shutil.copytree(config_backup, "config")

            self.event_bus.publish(
                "operations:backup_restored",
                {
                    "backup_id": backup_id,
                },
            )

            logger.info("Backup restored: %s", backup_id)
            return True
        except Exception as e:
            logger.error("Restore failed: %s", e)
            return False

    def list_backups(self) -> list[BackupInfo]:
        """List all backups."""
        return sorted(self._backups, key=lambda b: b.created_at, reverse=True)

    def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA256 checksum of a directory."""
        import hashlib

        sha256 = hashlib.sha256()
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)
        return sha256.hexdigest()

    def _prune_old_backups(self) -> None:
        """Remove old backups beyond max_backups."""
        if len(self._backups) > self._max_backups:
            old_backups = self._backups[: -self._max_backups]
            for backup in old_backups:
                try:
                    import shutil

                    shutil.rmtree(backup.path)
                    self._backups.remove(backup)
                    logger.info("Pruned old backup: %s", backup.id)
                except Exception as e:
                    logger.error("Failed to prune backup %s: %s", backup.id, e)


class StorageCleaner:
    """Manages storage cleanup and retention policies."""

    def __init__(
        self,
        max_disk_percent: float = 85.0,
        check_interval: int = 3600,
    ):
        self.max_disk_percent = max_disk_percent
        self.check_interval = check_interval

        self._cleanup_rules: list[Callable[[], asyncio.coroutine]] = []
        self._running = False
        self._task: asyncio.Task | None = None

        self.event_bus = get_core_event_bus()

    def add_cleanup_rule(self, rule: Callable[[], asyncio.coroutine]) -> None:
        """Add a cleanup rule."""
        self._cleanup_rules.append(rule)

    async def start(self) -> None:
        """Start periodic cleanup."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info("Storage cleaner started")

    async def stop(self) -> None:
        """Stop periodic cleanup."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup loop."""
        while self._running:
            try:
                await self._check_and_clean()
            except Exception as e:
                logger.error("Cleanup loop error: %s", e)

            await asyncio.sleep(self.check_interval)

    async def _check_and_clean(self) -> None:
        """Check disk usage and run cleanup if needed."""
        try:
            usage = shutil.disk_usage("/")
            percent_used = (usage.used / usage.total) * 100

            if percent_used > self.max_disk_percent:
                logger.warning("Disk usage high: %.1f%% (limit: %.1f%%)", percent_used, self.max_disk_percent)
                await self.run_cleanup()
        except Exception as e:
            logger.error("Disk check failed: %s", e)

    async def run_cleanup(self) -> dict[str, int]:
        """Run all cleanup rules."""
        results = {}

        for i, rule in enumerate(self._cleanup_rules):
            try:
                freed = await rule()
                results[f"rule_{i}"] = freed
                logger.info("Cleanup rule %d freed %d bytes", i, freed)
            except Exception as e:
                logger.error("Cleanup rule %d failed: %s", i, e)
                results[f"rule_{i}"] = -1

        total_freed = sum(v for v in results.values() if v > 0)

        self.event_bus.publish(
            "operations:cleanup_completed",
            {
                "freed_bytes": total_freed,
                "results": results,
            },
        )

        return results


class Doctor:
    """System diagnostics and health verification."""

    def __init__(self):
        self._checks: list[Callable[[], asyncio.coroutine]] = []
        self.event_bus = get_core_event_bus()

    def add_check(self, check: Callable[[], asyncio.coroutine]) -> None:
        """Add a diagnostic check."""
        self._checks.append(check)

    async def run(self, verbose: bool = False) -> DoctorReport:
        """Run all diagnostic checks."""
        checks = []

        for check in self._checks:
            try:
                result = await check()
                if isinstance(result, DoctorCheck):
                    checks.append(result)
                elif isinstance(result, dict):
                    checks.append(DoctorCheck(**result))
            except Exception as e:
                logger.error("Check failed: %s", e)
                checks.append(
                    DoctorCheck(
                        name=check.__name__,
                        passed=False,
                        message=f"Check error: {e}",
                        severity="critical",
                    )
                )

        # Also run built-in checks
        builtin_checks = await self._run_builtin_checks()
        checks.extend(builtin_checks)

        overall_healthy = all(c.passed for c in checks)

        critical_failures = [c for c in checks if not c.passed and c.severity == "critical"]
        warnings = [c for c in checks if not c.passed and c.severity == "warning"]

        if critical_failures:
            summary = f"CRITICAL: {len(critical_failures)} critical failures"
        elif warnings:
            summary = f"WARNING: {len(warnings)} warnings"
        else:
            summary = "All checks passed"

        recommendations = self._generate_recommendations(checks)

        report = DoctorReport(
            timestamp=datetime.now(UTC),
            overall_healthy=overall_healthy,
            checks=checks,
            summary=summary,
            recommendations=recommendations,
        )

        self.event_bus.publish(
            "operations:doctor_completed",
            {
                "healthy": overall_healthy,
                "checks": len(checks),
                "critical": len(critical_failures),
                "warnings": len(warnings),
            },
        )

        return report

    async def _run_builtin_checks(self) -> list[DoctorCheck]:
        """Run built-in diagnostic checks."""
        checks = []

        # Check disk space
        try:
            usage = shutil.disk_usage("/")
            percent = (usage.used / usage.total) * 100
            checks.append(
                DoctorCheck(
                    name="disk_space",
                    passed=percent < 90,
                    message=f"Disk usage: {percent:.1f}%",
                    severity="critical" if percent >= 90 else "warning" if percent >= 80 else "info",
                    details={"used_gb": usage.used / 1e9, "total_gb": usage.total / 1e9, "percent": percent},
                )
            )
        except Exception as e:
            checks.append(
                DoctorCheck(
                    name="disk_space",
                    passed=False,
                    message=f"Disk check failed: {e}",
                    severity="critical",
                )
            )

        # Check database connectivity
        try:
            from database import db

            session = db.SessionLocal()
            session.execute(db.text("SELECT 1"))
            session.close()
            checks.append(
                DoctorCheck(
                    name="database",
                    passed=True,
                    message="Database connection OK",
                    severity="info",
                )
            )
        except Exception as e:
            checks.append(
                DoctorCheck(
                    name="database",
                    passed=False,
                    message=f"Database error: {e}",
                    severity="critical",
                )
            )

        # Check API health
        try:
            from api.main import app

            checks.append(
                DoctorCheck(
                    name="api",
                    passed=True,
                    message=f"API loaded ({len(app.routes)} routes)",
                    severity="info",
                )
            )
        except Exception as e:
            checks.append(
                DoctorCheck(
                    name="api",
                    passed=False,
                    message=f"API error: {e}",
                    severity="critical",
                )
            )

        # Check event bus
        try:
            from core.events.event_bus import get_core_event_bus

            get_core_event_bus()
            checks.append(
                DoctorCheck(
                    name="event_bus",
                    passed=True,
                    message="Event bus operational",
                    severity="info",
                )
            )
        except Exception as e:
            checks.append(
                DoctorCheck(
                    name="event_bus",
                    passed=False,
                    message=f"Event bus error: {e}",
                    severity="critical",
                )
            )

        # Check operations components
        try:
            from cores.operations import get_operations_manager

            ops = get_operations_manager()
            checks.append(
                DoctorCheck(
                    name="operations",
                    passed=ops._running if hasattr(ops, "_running") else False,
                    message="Operations system running" if ops._running else "Operations system not running",
                    severity="info" if ops._running else "warning",
                )
            )
        except Exception as e:
            checks.append(
                DoctorCheck(
                    name="operations",
                    passed=False,
                    message=f"Operations error: {e}",
                    severity="warning",
                )
            )

        return checks

    def _generate_recommendations(self, checks: list[DoctorCheck]) -> list[str]:
        """Generate recommendations based on check results."""
        recommendations = []

        for check in checks:
            if not check.passed:
                if check.name == "disk_space" and check.details.get("percent", 0) > 85:
                    recommendations.append("Run storage cleanup or increase disk space")
                elif check.name == "database":
                    recommendations.append("Check database connection and migration status")
                elif check.name == "api":
                    recommendations.append("Check API server logs for errors")
                elif check.name == "event_bus":
                    recommendations.append("Verify event bus initialization order")
                elif check.name == "operations":
                    recommendations.append("Start operations system with initialize_operations()")

        if not recommendations:
            recommendations.append("System healthy - no actions required")

        return recommendations


class OperationsManager:
    """Main operations coordinator."""

    def __init__(
        self,
        backup_dir: Path = Path("backups"),
        watchdog_interval: int = 30,
        cleanup_interval: int = 3600,
    ):
        self.backup_dir = backup_dir
        self.watchdog_interval = watchdog_interval
        self.cleanup_interval = cleanup_interval

        self.event_bus = get_core_event_bus()

        self.watchdog = Watchdog(check_interval=watchdog_interval, event_bus=self.event_bus)
        self.backup_manager = BackupManager(backup_dir)
        self.storage_cleaner = StorageCleaner(
            max_disk_percent=85.0,
            check_interval=cleanup_interval,
        )
        self.doctor = Doctor()

        self._running = False
        self._shutdown_event = asyncio.Event()

        # Register default cleanup rules
        self._register_default_cleanup_rules()

        # Register default doctor checks
        self._register_default_doctor_checks()

    def _register_default_cleanup_rules(self) -> None:
        """Register default cleanup rules."""

        async def clean_old_logs() -> int:
            """Clean old log files."""
            freed = 0
            log_dir = Path("logs")
            if log_dir.exists():
                for log_file in log_dir.glob("*.log.*"):
                    if log_file.stat().st_mtime < time.time() - 7 * 86400:  # older than 7 days
                        size = log_file.stat().st_size
                        log_file.unlink()
                        freed += size
            return freed

        async def clean_old_backups() -> int:
            """Clean old backups beyond retention."""
            freed = 0
            backups = self.backup_manager.list_backups()
            if len(backups) > 30:
                for backup in backups[30:]:
                    size = backup.size_bytes
                    try:
                        import shutil

                        shutil.rmtree(backup.path)
                        freed += size
                    except Exception:
                        pass
            return freed

        async def clean_temp_files() -> int:
            """Clean temporary files."""
            freed = 0
            for temp_dir in [Path("/tmp"), Path("temp")]:
                if temp_dir.exists():
                    for f in temp_dir.glob("*"):
                        try:
                            if f.stat().st_mtime < time.time() - 86400:  # older than 1 day
                                if f.is_file():
                                    size = f.stat().st_size
                                    f.unlink()
                                    freed += size
                        except Exception:
                            pass
            return freed

        self.storage_cleaner.add_cleanup_rule(clean_old_logs)
        self.storage_cleaner.add_cleanup_rule(clean_old_backups)
        self.storage_cleaner.add_cleanup_rule(clean_temp_files)

    def _register_default_doctor_checks(self) -> None:
        """Register default doctor checks."""
        # Built-in checks are in Doctor._run_builtin_checks
        pass

    def register_component(
        self,
        name: str,
        checker: Callable[[], asyncio.coroutine],
        recovery: Callable[[], asyncio.coroutine] | None = None,
    ) -> None:
        """Register a component for watchdog monitoring."""
        self.watchdog.register_component(name, checker, recovery)

    def add_storage_cleanup_rule(self, rule: Callable[[], asyncio.coroutine]) -> None:
        """Add a storage cleanup rule."""
        self.storage_cleaner.add_cleanup_rule(rule)

    def add_doctor_check(self, check: Callable[[], asyncio.coroutine]) -> None:
        """Add a diagnostic check."""
        self.doctor.add_check(check)

    async def start(self) -> None:
        """Start all operations."""
        if self._running:
            return

        self._running = True

        await self.watchdog.start()
        await self.storage_cleaner.start()

        # Schedule daily backup
        asyncio.create_task(self._daily_backup())

        logger.info("Operations manager started")
        self.event_bus.publish("operations:started")

    async def stop(self) -> None:
        """Stop all operations."""
        if not self._running:
            return

        self._running = False

        await self.watchdog.stop()
        await self.storage_cleaner.stop()

        logger.info("Operations manager stopped")
        self.event_bus.publish("operations:stopped")

    async def _daily_backup(self) -> None:
        """Run daily backup at 2 AM."""
        while self._running:
            now = datetime.now()
            # Calculate seconds until 2 AM
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run.replace(day=next_run.day + 1)

            wait_seconds = (next_run - now).total_seconds()

            try:
                await asyncio.sleep(wait_seconds)
                if self._running:
                    await self.backup_manager.create_backup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Daily backup failed: %s", e)

    async def run_doctor(self, verbose: bool = False) -> DoctorReport:
        """Run system diagnostics."""
        return await self.doctor.run(verbose)

    async def create_backup(self, name: str | None = None) -> BackupInfo:
        """Create a manual backup."""
        return await self.backup_manager.create_backup(name)

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON
# ──────────────────────────────────────────────────────────────────────────

_operations_manager: OperationsManager | None = None


def get_operations_manager() -> OperationsManager:
    """Get or create the operations manager."""
    global _operations_manager
    if _operations_manager is None:
        _operations_manager = OperationsManager()
    return _operations_manager


async def initialize_operations(
    backup_dir: Path = Path("backups"),
    watchdog_interval: int = 30,
    cleanup_interval: int = 3600,
) -> OperationsManager:
    """Initialize the operations system."""
    global _operations_manager
    _operations_manager = OperationsManager(
        backup_dir=backup_dir,
        watchdog_interval=watchdog_interval,
        cleanup_interval=cleanup_interval,
    )
    await _operations_manager.start()
    logger.info("Operations system initialized")
    return _operations_manager
