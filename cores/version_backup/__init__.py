"""Version Backup System — Robust version backup and rollback for OWNEX OMEGA.

Provides:
- VersionBackupSystem: central coordinator for version backups
- Pre-update snapshots
- Version history tracking
- Rollback to previous versions
- Multiple version installations
- Integrity verification
- Emergency recovery
"""

from __future__ import annotations

from cores.version_backup.backup_system import (
    BackupResult,
    BackupStatus,
    VersionBackupSystem,
    VersionSnapshot,
    VersionState,
    get_version_backup_system,
    reset_version_backup_system,
)

__all__ = [
    "VersionBackupSystem",
    "get_version_backup_system",
    "reset_version_backup_system",
    "VersionSnapshot",
    "VersionState",
    "BackupResult",
    "BackupStatus",
]
