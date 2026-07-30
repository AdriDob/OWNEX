"""OWNEX Backup Engine — full system backup with manifest, SHA256, and rotation."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core import OWNEX_DIR
from core.version import OWNEX_VERSION

logger = logging.getLogger("ownex.core.backup")

BACKUP_DIR = OWNEX_DIR / "backups"
DEFAULT_KEEP = 10
OWNEX_VERSION = "5.0.0"


def _default_exclude(name: str) -> bool:
    """Exclude temp files, caches, and node_modules from backup."""
    return (
        name.startswith("__pycache__")
        or name == "node_modules"
        or name.endswith(".pyc")
        or name == "backups"
        or name.startswith(".")
    )


def _checksum(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _scan_files(base: Path) -> list[dict[str, Any]]:
    """Recursively scan all files under base, returning relative paths + metadata."""
    entries: list[dict[str, Any]] = []
    if not base.exists():
        return entries
    for root, dirs, files in os.walk(str(base)):
        rel_root = Path(root).relative_to(base)
        dirs[:] = [d for d in dirs if not _default_exclude(d)]
        for name in sorted(files):
            if _default_exclude(name):
                continue
            full = Path(root) / name
            rel = str(rel_root / name) if str(rel_root) != "." else name
            try:
                stat = full.stat()
                entries.append(
                    {
                        "path": rel,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "checksum": _checksum(full),
                    }
                )
            except Exception:
                logger.warning("Cannot read %s, skipping", full)
    return entries


def _build_manifest(files: list[dict[str, Any]]) -> dict[str, Any]:
    total_size = sum(f["size"] for f in files)
    manifest_checksum = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {
        "version": OWNEX_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "total_files": len(files),
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "manifest_checksum": manifest_checksum,
        "files": files,
    }


def _checkpoint_wal() -> None:
    """Run WAL checkpoint on all known SQLite databases for consistency."""
    known_dbs = [
        OWNEX_DIR / "ownex.db",
        OWNEX_DIR / "database" / "ownex.db",
        OWNEX_DIR / "database" / "ownex_core.db",
        OWNEX_DIR / "database" / "memory.db",
        OWNEX_DIR / "database" / "evidence_graph.db",
        OWNEX_DIR / "database" / "atlas.db",
        OWNEX_DIR / "database" / "odyssey.db",
    ]
    for db_path in known_dbs:
        if not db_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
            logger.debug("WAL checkpoint: %s", db_path.name)
        except Exception as exc:
            logger.warning("WAL checkpoint failed for %s: %s", db_path.name, exc)


def create_backup() -> dict[str, Any]:
    """Create a full ORION backup. Returns status dict with path and manifest."""
    _checkpoint_wal()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S%f")
    archive_path = BACKUP_DIR / f"OWNEX_BACKUP_{timestamp}.zip"

    files = _scan_files(OWNEX_DIR)
    if not files:
        return {"status": "error", "reason": "No files found in OWNEX_DIR"}

    manifest = _build_manifest(files)
    backup_path = str(archive_path)

    try:
        import zipfile

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write manifest first
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            for entry in files:
                full = OWNEX_DIR / entry["path"]
                try:
                    zf.write(full, arcname=entry["path"])
                except Exception as exc:
                    logger.warning("Failed to add %s to backup: %s", entry["path"], exc)

        archive_size = archive_path.stat().st_size
        logger.info("Backup created: %s (%d bytes, %d files)", backup_path, archive_size, len(files))

        return {
            "status": "ok",
            "backup_path": backup_path,
            "size": archive_size,
            "size_mb": round(archive_size / (1024 * 1024), 2),
            "total_files": len(files),
            "total_size_mb": manifest["total_size_mb"],
            "checksum": manifest["manifest_checksum"],
            "created_at": manifest["created_at"],
        }
    except Exception as exc:
        logger.exception("Backup creation failed")
        return {"status": "error", "reason": str(exc)}


def verify_backup(archive_path: str) -> dict[str, Any]:
    """Verify backup integrity: checksums, manifest, file count."""
    path = Path(archive_path)
    if not path.exists():
        return {"status": "error", "reason": f"Backup not found: {archive_path}"}

    try:
        import zipfile

        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()

            if "manifest.json" not in names:
                return {"status": "error", "reason": "Missing manifest.json in backup"}

            manifest = json.loads(zf.read("manifest.json"))
            expected_files = {f["path"] for f in manifest.get("files", [])}
            actual_files = set(names) - {"manifest.json"}

            missing = expected_files - actual_files
            extra = actual_files - expected_files

            checksum_errors = []
            for f in manifest.get("files", []):
                if f["path"] in actual_files:
                    try:
                        content = zf.read(f["path"])
                        actual_checksum = hashlib.sha256(content).hexdigest()
                        if actual_checksum != f["checksum"]:
                            checksum_errors.append(f["path"])
                    except Exception:
                        checksum_errors.append(f["path"])

            return {
                "status": "ok" if not missing and not checksum_errors else "corrupted",
                "total_files_expected": len(expected_files),
                "total_files_actual": len(actual_files),
                "missing_files": sorted(missing),
                "extra_files": sorted(extra),
                "checksum_errors": checksum_errors,
                "manifest": {
                    "version": manifest.get("version"),
                    "created_at": manifest.get("created_at"),
                    "total_size_mb": manifest.get("total_size_mb"),
                },
            }
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def list_backups() -> list[dict[str, Any]]:
    """List all available OWNEX backups with metadata."""
    if not BACKUP_DIR.exists():
        return []

    backups = []
    for f in sorted(BACKUP_DIR.glob("OWNEX_BACKUP_*.zip"), reverse=True):
        stat = f.stat()
        backups.append(
            {
                "path": str(f),
                "filename": f.name,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            }
        )
    return backups


def prune_backups(keep: int = DEFAULT_KEEP) -> dict[str, Any]:
    """Remove old backups, keeping only the N most recent."""
    backups = sorted(BACKUP_DIR.glob("OWNEX_BACKUP_*.zip"), reverse=True)
    if len(backups) <= keep:
        return {"status": "ok", "deleted": 0, "kept": len(backups), "limit": keep}

    to_delete = backups[keep:]
    deleted_count = 0
    for f in to_delete:
        try:
            f.unlink()
            deleted_count += 1
            logger.info("Pruned old backup: %s", f.name)
        except Exception as exc:
            logger.warning("Failed to delete %s: %s", f.name, exc)

    return {
        "status": "ok",
        "deleted": deleted_count,
        "kept": len(backups) - deleted_count,
        "limit": keep,
    }


def restore_backup(archive_path: str, target_dir: str | None = None) -> dict[str, Any]:
    """Restore ORION from a backup archive."""
    path = Path(archive_path)
    if not path.exists():
        return {"status": "error", "reason": f"Backup not found: {archive_path}"}

    dest = Path(target_dir) if target_dir else OWNEX_DIR
    try:
        import zipfile

        with zipfile.ZipFile(path, "r") as zf:
            # Skip manifest.json during extraction
            names = [n for n in zf.namelist() if n != "manifest.json"]
            for name in names:
                try:
                    zf.extract(name, dest)
                except Exception as exc:
                    logger.warning("Failed to restore %s: %s", name, exc)

        logger.info("Restored %d files from %s to %s", len(names), archive_path, dest)
        return {"status": "ok", "restored_files": len(names), "target": str(dest)}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def backup_status() -> dict[str, Any]:
    """Full backup status for health/status endpoints."""
    backups = list_backups()
    return {
        "total_backups": len(backups),
        "latest_backup": backups[0] if backups else None,
        "total_backup_size_mb": round(sum(b["size_mb"] for b in backups), 2),
        "backup_dir": str(BACKUP_DIR),
        "ownex_dir": str(OWNEX_DIR),
        "prune_keep": DEFAULT_KEEP,
    }
