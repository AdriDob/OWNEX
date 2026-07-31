"""Automated Cloud Backup Scheduler.

Provides cron-based scheduling for automatic cloud backups.
"""

from __future__ import annotations

import logging

from cores.cloud_backup import CloudBackupConfig, get_cloud_backup_manager
from cores.version_backup import get_version_backup_system

logger = logging.getLogger("ownex.cloud_backup_scheduler")


class CloudBackupScheduler:
    """Scheduler for automated cloud backups."""

    def __init__(self, cloud_config: CloudBackupConfig | None = None):
        self.cloud_config = cloud_config
        self.cloud_manager = None
        self.version_backup_system = get_version_backup_system()

        if cloud_config:
            self.cloud_manager = get_cloud_backup_manager(cloud_config)

    def schedule_daily_backup(self, hour: int = 2, minute: int = 0) -> dict[str, str]:
        """Schedule a daily backup at specified time."""
        logger.info(f"[CLOUD BACKUP SCHEDULER] Scheduling daily backup at {hour:02d}:{minute:02d}")

        try:
            import schedule
            from croniter import croniter

            cron_expression = f"{minute} {hour} * * *"
            logger.info(f"[CLOUD BACKUP SCHEDULER] Cron expression: {cron_expression}")

            return {
                "success": True,
                "schedule": "daily",
                "cron_expression": cron_expression,
                "time": f"{hour:02d}:{minute:02d}",
            }

        except ImportError:
            logger.error("[CLOUD BACKUP SCHEDULER] croniter or schedule not installed")
            return {
                "success": False,
                "error": "croniter or schedule not installed",
            }

    def execute_scheduled_backup(self) -> dict[str, any]:
        """Execute a scheduled backup (local + cloud)."""
        logger.info("[CLOUD BACKUP SCHEDULER] Executing scheduled backup")

        # Step 1: Create local backup
        local_result = self.version_backup_system.create_backup(
            notes="Scheduled automatic backup"
        )

        if local_result.status.value != "success":
            return {
                "success": False,
                "error": "Local backup creation failed",
                "local_error": local_result.error,
            }

        # Step 2: Upload to cloud
        if self.cloud_manager:
            cloud_result = self.cloud_manager.sync_to_cloud(local_result.backup_path)

            if cloud_result.get("success"):
                logger.info(f"[CLOUD BACKUP SCHEDULER] Backup synced to cloud: {local_result.backup_path}")
                return {
                    "success": True,
                    "local_backup": local_result.backup_path,
                    "cloud_backup": cloud_result.get("backup_name"),
                    "cloud_provider": cloud_result.get("cloud_provider"),
                }
            else:
                logger.error(f"[CLOUD BACKUP SCHEDULER] Cloud sync failed: {cloud_result.get('error')}")
                return {
                    "success": False,
                    "error": "Cloud sync failed",
                    "cloud_error": cloud_result.get("error"),
                    "local_backup": local_result.backup_path,
                }
        else:
            logger.warning("[CLOUD BACKUP SCHEDULER] No cloud manager configured, local backup only")
            return {
                "success": True,
                "local_backup": local_result.backup_path,
                "cloud_backup": None,
                "cloud_provider": None,
            }

    def schedule_weekly_backup(self, day_of_week: int = 0, hour: int = 2, minute: int = 0) -> dict[str, str]:
        """Schedule a weekly backup on specified day (0 = Monday)."""
        logger.info(f"[CLOUD BACKUP SCHEDULER] Scheduling weekly backup on day {day_of_week} at {hour:02d}:{minute:02d}")

        try:
            cron_expression = f"{minute} {hour} * * {day_of_week}"
            logger.info(f"[CLOUD BACKUP SCHEDULER] Cron expression: {cron_expression}")

            return {
                "success": True,
                "schedule": "weekly",
                "cron_expression": cron_expression,
                "day_of_week": day_of_week,
                "time": f"{hour:02d}:{minute:02d}",
            }

        except ImportError:
            logger.error("[CLOUD BACKUP SCHEDULER] croniter not installed")
            return {
                "success": False,
                "error": "croniter not installed",
            }

    def cleanup_old_cloud_backups(self) -> dict[str, any]:
        """Clean up old cloud backups based on retention policy."""
        if not self.cloud_manager:
            return {
                "success": False,
                "error": "No cloud manager configured",
            }

        logger.info("[CLOUD BACKUP SCHEDULER] Cleaning up old cloud backups")
        return self.cloud_manager.cleanup_old_backups()

    def get_backup_schedule_status(self) -> dict[str, any]:
        """Get current backup schedule status."""
        return {
            "cloud_provider": self.cloud_config.provider.value if self.cloud_config else None,
            "cloud_configured": self.cloud_manager is not None,
            "local_backup_system": self.version_backup_system is not None,
            "last_backup": self._get_last_backup_info(),
        }

    def _get_last_backup_info(self) -> dict[str, any]:
        """Get information about the last backup."""
        backups = self.version_backup_system.list_backups()

        if not backups:
            return {
                "exists": False,
            }

        last_backup = max(backups, key=lambda b: b["created_at"])

        return {
            "exists": True,
            "version": last_backup["version"],
            "created_at": last_backup["created_at"],
            "size": last_backup["size"],
            "notes": last_backup["notes"],
        }


# Singleton instance
_cloud_backup_scheduler: CloudBackupScheduler | None = None


def get_cloud_backup_scheduler(cloud_config: CloudBackupConfig | None = None) -> CloudBackupScheduler:
    """Get singleton cloud backup scheduler instance."""
    global _cloud_backup_scheduler
    if _cloud_backup_scheduler is None:
        _cloud_backup_scheduler = CloudBackupScheduler(cloud_config)
    return _cloud_backup_scheduler


def reset_cloud_backup_scheduler() -> None:
    """Reset cloud backup scheduler instance (for testing)."""
    global _cloud_backup_scheduler
    _cloud_backup_scheduler = None
