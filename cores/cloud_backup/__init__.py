"""Cloud Backup System — Backup to S3, GCS, and other cloud providers.

Provides:
- CloudBackupProvider: abstract base for cloud backup providers
- S3BackupProvider: AWS S3 backup implementation
- GCSBackupProvider: Google Cloud Storage backup implementation
- CloudBackupManager: coordinator for cloud backup operations
- CloudBackupScheduler: automated scheduling for cloud backups
"""

from __future__ import annotations

from cores.cloud_backup.cloud_backup import (
    CloudBackupConfig,
    CloudBackupManager,
    CloudBackupProvider,
    CloudProvider,
    GCSBackupProvider,
    S3BackupProvider,
    get_cloud_backup_manager,
    reset_cloud_backup_manager,
)
from cores.cloud_backup.scheduler import (
    CloudBackupScheduler,
    get_cloud_backup_scheduler,
    reset_cloud_backup_scheduler,
)

__all__ = [
    "CloudBackupProvider",
    "S3BackupProvider",
    "GCSBackupProvider",
    "CloudBackupManager",
    "CloudBackupScheduler",
    "CloudBackupConfig",
    "CloudProvider",
    "get_cloud_backup_manager",
    "reset_cloud_backup_manager",
    "get_cloud_backup_scheduler",
    "reset_cloud_backup_scheduler",
]
