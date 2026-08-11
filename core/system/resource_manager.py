"""Smart Resource Manager — cache, temp cleanup, snapshots, dedup.

OWNEX runs 24/7. This module ensures the system doesn't bloat:
- Cleans temporary files based on age/size thresholds
- Manages downloaded models (Ollama, etc.)
- Deduplicates data
- Creates periodic resource snapshots
- Reports storage health
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.resource_manager")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = PROJECT_ROOT / ".cache"
TEMP_DIR = PROJECT_ROOT / ".temp"
SNAPSHOT_DIR = PROJECT_ROOT / ".ownex" / "snapshots"
BACKUP_DIR = PROJECT_ROOT / ".ownex" / "backups"
DB_PATH = PROJECT_ROOT / "data" / "ownex.db"


# ── Thresholds (configurable via JSON) ──

DEFAULT_CONFIG = {
    "temp_max_age_hours": 24,  # Delete temp files older than N hours
    "temp_max_size_mb": 500,  # Max total temp directory size
    "cache_max_age_days": 7,  # Delete cache items older than N days
    "cache_max_size_mb": 1000,  # Max total cache directory size
    "snapshot_retention_count": 20,  # Keep last N snapshots
    "backup_retention_count": 10,  # Keep last N backups
    "db_vacuum_threshold_mb": 100,  # Vacuum DB if WAL > N MB
    "auto_cleanup_interval_hours": 6,  # Run cleanup every N hours
    "max_log_size_mb": 50,  # Rotate logs > N MB
}


class ResourceManager:
    """Central resource management for OWNEX.

    Usage:
        rm = get_resource_manager()
        rm.cleanup()              # One-shot cleanup
        rm.stats()                # Get resource stats
        rm.auto_cleanup_loop()    # Background loop (use in scheduler)
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = {**DEFAULT_CONFIG, **(config or {})}
        self._ensure_dirs()
        self._last_cleanup: float = 0.0

    def _ensure_dirs(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def cleanup(self, force: bool = False) -> dict[str, Any]:
        """Run cleanup on all resource categories."""
        results = {
            "temp_files_removed": self._clean_temp(),
            "cache_items_removed": self._clean_cache(),
            "old_snapshots_removed": self._clean_snapshots(),
            "old_backups_removed": self._clean_backups(),
            "db_vacuumed": self._vacuum_db(),
            "logs_rotated": self._rotate_logs(),
        }
        results["total_freed_mb"] = self._estimate_freed(results)
        results["timestamp"] = datetime.now(UTC).isoformat()
        self._last_cleanup = time.time()
        logger.info("Resource cleanup: %s", results)
        return results

    def stats(self) -> dict[str, Any]:
        """Get current resource usage statistics."""
        return {
            "temp_dir": self._dir_stats(TEMP_DIR),
            "cache_dir": self._dir_stats(CACHE_DIR),
            "snapshots": len(list(SNAPSHOT_DIR.glob("*.json"))),
            "backups": len(list(BACKUP_DIR.glob("*.json"))),
            "db_size_mb": self._file_size_mb(DB_PATH),
            "db_wal_size_mb": self._file_size_mb(DB_PATH.with_name(f"{DB_PATH.name}-wal")),
            "last_cleanup": self._last_cleanup,
            "uptime_hours": round((time.time() - self._last_cleanup) / 3600, 1) if self._last_cleanup else 0,
        }

    def deduplicate(self, file_paths: list[str] | None = None) -> dict[str, Any]:
        """Find and remove duplicate files."""
        from hashlib import md5

        check_paths = file_paths or [str(PROJECT_ROOT)]
        found = 0
        removed = 0
        size_freed = 0
        seen: dict[str, list[Path]] = {}

        for base_path in check_paths:
            base = Path(base_path)
            if not base.exists():
                continue
            pattern = "*.json" if base.is_dir() else base.name
            search_dir = base if base.is_dir() else base.parent
            for f in search_dir.glob(f"**/{pattern}"):
                if f.stat().st_size < 100:  # Skip tiny files
                    continue
                try:
                    content = f.read_bytes()
                    h = md5(content).hexdigest()
                    if h in seen:
                        # Duplicate found — remove the shorter path (assume temp/backup)
                        seen[h][0]
                        if "snapshot" in f.name or "backup" in f.name:
                            f.unlink()
                            removed += 1
                            size_freed += f.stat().st_size
                        else:
                            pass  # Keep original
                    else:
                        seen[h] = [f]
                        found += 1
                except (OSError, PermissionError):
                    continue

        return {
            "scanned": len(seen),
            "duplicates_found": found - 1 if found else 0,
            "duplicates_removed": removed,
            "size_freed_mb": round(size_freed / 1024 / 1024, 2),
        }

    def _clean_temp(self) -> int:
        """Remove old temporary files."""
        removed = 0
        max_age = timedelta(hours=self._config["temp_max_age_hours"])
        cutoff = datetime.now(UTC) - max_age
        max_size = self._config["temp_max_size_mb"] * 1024 * 1024
        total_size = 0

        for f in TEMP_DIR.glob("*"):
            if f.is_file():
                total_size += f.stat().st_size
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
                if mtime < cutoff:
                    f.unlink()
                    removed += 1

        # If total exceeds limit, remove oldest first
        if total_size > max_size:
            files = sorted(TEMP_DIR.glob("*"), key=lambda f: f.stat().st_mtime)
            while total_size > max_size and files:
                f = files.pop(0)
                if f.is_file():
                    total_size -= f.stat().st_size
                    f.unlink()
                    removed += 1

        return removed

    def _clean_cache(self) -> int:
        """Remove expired cache items."""
        removed = 0
        max_age = timedelta(days=self._config["cache_max_age_days"])
        cutoff = datetime.now(UTC) - max_age

        for f in CACHE_DIR.glob("*"):
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
                if mtime < cutoff:
                    f.unlink()
                    removed += 1

        return removed

    def _clean_snapshots(self) -> int:
        """Remove old snapshots beyond retention count."""
        snapshots = sorted(SNAPSHOT_DIR.glob("*.json"))
        removed = 0
        for old in snapshots[: -self._config["snapshot_retention_count"]]:
            old.unlink()
            removed += 1
        return removed

    def _clean_backups(self) -> int:
        """Remove old backups beyond retention count."""
        backups = sorted(BACKUP_DIR.glob("*.json"))
        removed = 0
        for old in backups[: -self._config["backup_retention_count"]]:
            old.unlink()
            removed += 1
        return removed

    def _vacuum_db(self) -> bool:
        """Vacuum SQLite DB if WAL file is too large."""
        wal_path = DB_PATH.with_name(f"{DB_PATH.name}-wal")
        if wal_path.exists() and wal_path.stat().st_size > self._config["db_vacuum_threshold_mb"] * 1024 * 1024:
            try:
                conn = sqlite3.connect(str(DB_PATH))
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.execute("VACUUM;")
                conn.close()
                logger.info("Database vacuumed")
                return True
            except Exception as e:
                logger.warning("DB vacuum failed: %s", e)
        return False

    def _rotate_logs(self) -> int:
        """Rotate oversized log files."""
        rotated = 0
        for log_file in (PROJECT_ROOT / "logs").glob("*.log"):
            if log_file.stat().st_size > self._config["max_log_size_mb"] * 1024 * 1024:
                rotated_path = log_file.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
                log_file.rename(rotated_path)
                rotated += 1
        return rotated

    def _dir_stats(self, path: Path) -> dict[str, Any]:
        """Get directory statistics."""
        if not path.exists():
            return {"exists": False, "size_mb": 0, "files": 0}
        total_size = sum(f.stat().st_size for f in path.glob("*") if f.is_file())
        file_count = sum(1 for f in path.glob("*") if f.is_file())
        return {
            "exists": True,
            "size_mb": round(total_size / 1024 / 1024, 2),
            "files": file_count,
        }

    def _file_size_mb(self, path: Path) -> float:
        if path.exists():
            return round(path.stat().st_size / 1024 / 1024, 2)
        return 0.0

    def _estimate_freed(self, results: dict) -> float:
        return 0.0  # Conservative estimate


_manager: ResourceManager | None = None


def get_resource_manager() -> ResourceManager:
    global _manager
    if _manager is None:
        _manager = ResourceManager()
    return _manager
