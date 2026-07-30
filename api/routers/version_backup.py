"""Version Backup API Router.

Provides endpoints for version backup and rollback operations.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.version_backup import (
    BackupStatus,
    get_version_backup_system,
    VersionBackupSystem,
)

logger = logging.getLogger("ownex.api.version_backup")


router = APIRouter(prefix="/version-backup", tags=["version-backup"])


class CreateBackupRequest(BaseModel):
    """Request to create a version backup."""

    notes: str = ""


class RollbackRequest(BaseModel):
    """Request to rollback to a specific version."""

    version: str | None = None
    git_commit: str | None = None


@router.post("/backup")
async def create_backup(request: CreateBackupRequest) -> dict[str, Any]:
    """Create a backup of the current version."""
    backup_system = get_version_backup_system()

    try:
        result = backup_system.create_backup(notes=request.notes)

        if result.status == BackupStatus.SUCCESS:
            return {
                "success": True,
                "version": result.version,
                "backup_path": result.backup_path,
                "message": result.message,
                "manifest": result.manifest,
            }
        else:
            return {
                "success": False,
                "error": result.error,
            }

    except Exception as e:
        logger.error(f"[VERSION BACKUP] Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backups")
async def list_backups() -> dict[str, Any]:
    """List all available version backups."""
    backup_system = get_version_backup_system()

    try:
        backups = backup_system.list_backups()
        return {
            "success": True,
            "backups": backups,
            "total": len(backups),
        }

    except Exception as e:
        logger.error(f"[VERSION BACKUP] Error listing backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backup/{backup_path:path}/verify")
async def verify_backup(backup_path: str) -> dict[str, Any]:
    """Verify backup integrity."""
    backup_system = get_version_backup_system()

    try:
        verification = backup_system.verify_backup(backup_path)
        return verification

    except Exception as e:
        logger.error(f"[VERSION BACKUP] Error verifying backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback")
async def rollback_to_version(request: RollbackRequest) -> dict[str, Any]:
    """Rollback to a specific version."""
    backup_system = get_version_backup_system()

    try:
        result = backup_system.rollback_to_version(
            version=request.version,
            git_commit=request.git_commit,
        )

        return result

    except Exception as e:
        logger.error(f"[VERSION BACKUP] Error rolling back: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore-latest")
async def restore_latest() -> dict[str, Any]:
    """Restore from the latest backup."""
    backup_system = get_version_backup_system()

    try:
        result = backup_system.restore_latest()
        return result

    except Exception as e:
        logger.error(f"[VERSION BACKUP] Error restoring latest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-version")
async def get_current_version() -> dict[str, Any]:
    """Get current version information."""
    backup_system = get_version_backup_system()

    try:
        version = backup_system.get_current_version()
        commit = backup_system.get_current_commit()

        return {
            "version": version,
            "git_commit": commit,
        }

    except Exception as e:
        logger.error(f"[VERSION BACKUP] Error getting current version: {e}")
        raise HTTPException(status_code=500, detail=str(e))
