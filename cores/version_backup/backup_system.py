"""OWNEX OMEGA Version Backup System.

Provides robust version backup and rollback capabilities for safe updates.
Supports:
- Pre-update snapshots
- Version history tracking
- Rollback to previous versions
- Multiple version installations
- Integrity verification
- Emergency recovery

INTEGRATED WITH RECOVERY SYSTEM:
- Shared SQLite storage (recovery_history.db) for version backup metadata
- Unified local storage for recovery and version backup systems
- Uses RecoveryStore for persistence instead of versions.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.version_backup")


class BackupStatus(Enum):
    """Status of backup operations."""

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"


class VersionState(Enum):
    """State of a version installation."""

    ACTIVE = "active"
    BACKUP = "backup"
    ROLLBACK = "rollback"
    CORRUPTED = "corrupted"


@dataclass
class VersionSnapshot:
    """Snapshot of a specific version."""

    version: str
    git_commit: str
    created_at: str
    state: VersionState
    backup_path: str
    manifest: dict[str, Any] = field(default_factory=dict)
    checksum: str = ""
    size: int = 0
    notes: str = ""


@dataclass
class BackupResult:
    """Result of a backup operation."""

    status: BackupStatus
    version: str
    backup_path: str = ""
    message: str = ""
    error: str = ""
    manifest: dict[str, Any] = field(default_factory=dict)


class VersionBackupSystem:
    """Version backup and rollback system for OWNEX OMEGA."""

    def __init__(self, ownex_dir: Path | None = None, backup_dir: Path | None = None):
        self.ownex_dir = ownex_dir or Path.cwd()
        self.backup_dir = backup_dir or self.ownex_dir / ".ownex_backups"
        self.current_symlink = self.backup_dir / "current"
        self.max_backups = 10  # Keep max 10 backups

        self._ensure_backup_dir()

        # ⚡ INTEGRATED WITH RECOVERY SYSTEM
        # Use RecoveryStore for shared SQLite storage
        try:
            from cores.recovery.persistence import get_recovery_store
            self._recovery_store = get_recovery_store()
            logger.info("[VERSION BACKUP] Using shared SQLite storage (recovery_history.db)")
        except ImportError:
            logger.warning("[VERSION BACKUP] RecoveryStore not available, using fallback storage")
            self._recovery_store = None

    def _ensure_backup_dir(self) -> None:
        """Ensure backup directory exists."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def get_current_version(self) -> str:
        """Get current version from git or version file."""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=self.ownex_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Failed to get git version: {e}")

        # Fallback to version file
        version_file = self.ownex_dir / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()

        return "unknown"

    def get_current_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.ownex_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Failed to get git commit: {e}")

        return "unknown"

    def create_backup(self, notes: str = "") -> BackupResult:
        """Create a backup of the current version."""
        logger.info(f"[VERSION BACKUP] Creating backup: {notes}")

        version = self.get_current_version()
        commit = self.get_current_commit()
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_name = f"OWNEX_v{version}_{timestamp}"
        backup_path = self.backup_dir / backup_name

        try:
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)

            # Copy essential files
            essential_files = [
                "database",
                "config.json",
                ".env",
                "identity_vault.key",
                "targets",
                ".ai",
                "cores",
                "api",
                "frontend",
                "scripts",
                "requirements.txt",
                "pyproject.toml",
                "package.json",
                "package-lock.json",
            ]

            manifest = {
                "version": version,
                "git_commit": commit,
                "created_at": datetime.now(UTC).isoformat(),
                "backup_name": backup_name,
                "notes": notes,
                "files": [],
            }

            total_size = 0

            for file_pattern in essential_files:
                source = self.ownex_dir / file_pattern
                if not source.exists():
                    continue

                dest = backup_path / file_pattern
                if source.is_dir():
                    shutil.copytree(source, dest, ignore=shutil.ignore_patterns(
                        "__pycache__", "*.pyc", ".git", "node_modules", ".venv", "dist", "build"
                    ))
                    # Calculate size
                    for item in source.rglob("*"):
                        if item.is_file():
                            total_size += item.stat().st_size
                else:
                    shutil.copy2(source, dest)
                    total_size += source.stat().st_size

                manifest["files"].append({
                    "path": file_pattern,
                    "type": "directory" if source.is_dir() else "file",
                })

            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)
            manifest["checksum"] = checksum
            manifest["size"] = total_size
            manifest["total_files"] = len(manifest["files"])

            # Save manifest
            manifest_path = backup_path / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            # Create snapshot record
            snapshot = VersionSnapshot(
                version=version,
                git_commit=commit,
                created_at=datetime.now(UTC).isoformat(),
                state=VersionState.BACKUP,
                backup_path=str(backup_path),
                manifest=manifest,
                checksum=checksum,
                size=total_size,
                notes=notes,
            )

            # Save to version history
            self._save_snapshot(snapshot)

            # Clean old backups
            self._cleanup_old_backups()

            logger.info(f"[VERSION BACKUP] Backup created: {backup_path}")

            return BackupResult(
                status=BackupStatus.SUCCESS,
                version=version,
                backup_path=str(backup_path),
                message="Backup created successfully",
                manifest=manifest,
            )

        except Exception as e:
            logger.error(f"[VERSION BACKUP] Failed to create backup: {e}")
            return BackupResult(
                status=BackupStatus.FAILED,
                version=version,
                error=str(e),
            )

    def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA256 checksum of a directory."""
        sha256_hash = hashlib.sha256()

        for item in sorted(path.rglob("*")):
            if item.is_file():
                with open(item, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def _save_snapshot(self, snapshot: VersionSnapshot) -> None:
        """Save snapshot to version history using shared SQLite storage."""
        if self._recovery_store:
            # Use shared SQLite storage (RecoveryStore)
            self._recovery_store.save_version_backup(
                version=snapshot.version,
                git_commit=snapshot.git_commit,
                backup_path=snapshot.backup_path,
                manifest=snapshot.manifest,
                checksum=snapshot.checksum,
                size=snapshot.size,
                notes=snapshot.notes,
                state=snapshot.state.value,
            )
        else:
            # Fallback to JSON storage
            logger.warning("[VERSION BACKUP] Using fallback JSON storage")
            history = self._load_history()
            history.append(snapshot)

            # Save to JSON
            with open(self.backup_dir / "versions.json", "w") as f:
                json.dump([s.__dict__ for s in history], f, indent=2)

    def _load_history(self) -> list[VersionSnapshot]:
        """Load version history from shared SQLite storage."""
        if self._recovery_store:
            # Use shared SQLite storage (RecoveryStore)
            backups = self._recovery_store.get_version_backups(limit=100)
            return [
                VersionSnapshot(
                    version=b["version"],
                    git_commit=b["git_commit"],
                    created_at=b["created_at"],
                    state=VersionState(b["state"]),
                    backup_path=b["backup_path"],
                    manifest=b.get("manifest", {}),
                    checksum=b["checksum"],
                    size=b["size"],
                    notes=b.get("notes", ""),
                )
                for b in backups
            ]
        else:
            # Fallback to JSON storage
            version_file = self.backup_dir / "versions.json"
            if not version_file.exists():
                return []

            with open(version_file) as f:
                data = json.load(f)

            return [VersionSnapshot(**item) for item in data]

    def _cleanup_old_backups(self) -> None:
        """Clean up old backups, keeping only max_backups."""
        if self._recovery_store:
            # Use shared SQLite storage (RecoveryStore)
            deleted_count = self._recovery_store.cleanup_old_version_backups(max_count=self.max_backups)
            if deleted_count > 0:
                logger.info(f"[VERSION BACKUP] Cleaned up {deleted_count} old backups via RecoveryStore")
        else:
            # Fallback to JSON storage
            history = self._load_history()

            if len(history) <= self.max_backups:
                return

            # Sort by created_at, oldest first
            history.sort(key=lambda s: s.created_at)

            # Remove oldest backups
            to_remove = history[:-self.max_backups]

            for snapshot in to_remove:
                backup_path = Path(snapshot.backup_path)
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                    logger.info(f"[VERSION BACKUP] Removed old backup: {backup_path}")

            # Update history
            history = history[-self.max_backups:]

            with open(self.backup_dir / "versions.json", "w") as f:
                json.dump([s.__dict__ for s in history], f, indent=2)

    def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups."""
        history = self._load_history()

        return [
            {
                "version": s.version,
                "git_commit": s.git_commit,
                "created_at": s.created_at,
                "state": s.state.value,
                "backup_path": s.backup_path,
                "size": s.size,
                "notes": s.notes,
            }
            for s in history
        ]

    def verify_backup(self, backup_path: str) -> dict[str, Any]:
        """Verify backup integrity."""
        backup_path = Path(backup_path)

        if not backup_path.exists():
            return {"valid": False, "error": "Backup path does not exist"}

        manifest_path = backup_path / "manifest.json"

        if not manifest_path.exists():
            return {"valid": False, "error": "Manifest not found"}

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Verify checksum
        expected_checksum = manifest.get("checksum", "")
        actual_checksum = self._calculate_checksum(backup_path)

        if expected_checksum != actual_checksum:
            return {
                "valid": False,
                "error": f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}",
            }

        # Verify essential files exist
        missing_files = []
        for file_info in manifest.get("files", []):
            file_path = backup_path / file_info["path"]
            if not file_path.exists():
                missing_files.append(file_info["path"])

        if missing_files:
            return {
                "valid": False,
                "error": f"Missing files: {', '.join(missing_files)}",
            }

        return {
            "valid": True,
            "version": manifest.get("version"),
            "git_commit": manifest.get("git_commit"),
            "created_at": manifest.get("created_at"),
            "size": manifest.get("size"),
        }

    def rollback_to_version(self, version: str | None = None, git_commit: str | None = None) -> dict[str, Any]:
        """Rollback to a specific version."""
        logger.info(f"[VERSION BACKUP] Rolling back to version: {version or git_commit}")

        history = self._load_history()

        # Find target snapshot
        target_snapshot = None
        for snapshot in history:
            if version and snapshot.version == version:
                target_snapshot = snapshot
                break
            if git_commit and snapshot.git_commit == git_commit:
                target_snapshot = snapshot
                break

        if not target_snapshot:
            return {
                "success": False,
                "error": f"Version not found in backup history: {version or git_commit}",
            }

        # Verify backup
        verification = self.verify_backup(target_snapshot.backup_path)
        if not verification["valid"]:
            return {
                "success": False,
                "error": f"Backup verification failed: {verification.get('error')}",
            }

        try:
            # Create pre-rollback backup
            logger.info("[VERSION BACKUP] Creating pre-rollback backup")
            pre_rollback = self.create_backup(notes="Pre-rollback backup")

            if pre_rollback.status != BackupStatus.SUCCESS:
                logger.warning("[VERSION BACKUP] Pre-rollback backup failed, continuing anyway")

            # Restore from backup
            backup_path = Path(target_snapshot.backup_path)

            # Restore essential files
            for file_info in target_snapshot.manifest.get("files", []):
                source = backup_path / file_info["path"]
                dest = self.ownex_dir / file_info["path"]

                if not source.exists():
                    logger.warning(f"[VERSION BACKUP] File not in backup: {file_info['path']}")
                    continue

                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()

                if source.is_dir():
                    shutil.copytree(source, dest)
                else:
                    shutil.copy2(source, dest)

            # Restore git state
            if target_snapshot.git_commit != "unknown":
                try:
                    subprocess.run(
                        ["git", "checkout", target_snapshot.git_commit],
                        cwd=self.ownex_dir,
                        capture_output=True,
                        timeout=30,
                    )
                    logger.info(f"[VERSION BACKUP] Git restored to commit: {target_snapshot.git_commit}")
                except Exception as e:
                    logger.warning(f"[VERSION BACKUP] Failed to restore git state: {e}")

            # Update snapshot state
            target_snapshot.state = VersionState.ROLLBACK
            self._save_snapshot(target_snapshot)

            logger.info(f"[VERSION BACKUP] Rollback completed to version: {target_snapshot.version}")

            return {
                "success": True,
                "version": target_snapshot.version,
                "git_commit": target_snapshot.git_commit,
                "message": "Rollback completed successfully",
            }

        except Exception as e:
            logger.error(f"[VERSION BACKUP] Rollback failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def restore_latest(self) -> dict[str, Any]:
        """Restore from the latest backup."""
        history = self._load_history()

        if not history:
            return {
                "success": False,
                "error": "No backups available",
            }

        # Get latest backup
        latest = max(history, key=lambda s: s.created_at)

        return self.rollback_to_version(version=latest.version)


# Singleton instance
_backup_system: VersionBackupSystem | None = None


def get_version_backup_system() -> VersionBackupSystem:
    """Get singleton version backup system instance."""
    global _backup_system
    if _backup_system is None:
        _backup_system = VersionBackupSystem()
    return _backup_system


def reset_version_backup_system() -> None:
    """Reset version backup system instance (for testing)."""
    global _backup_system
    _backup_system = None
