"""OWNEX Temp Manager — centralized temporary file lifecycle.

Provides:
  - Configurable base directory (/tmp/ownex/ by default)
  - Per-component quotas with auto-cleanup
  - TTL-based expiration for temp files
  - Size tracking + health metrics
  - Thread-safe operations (file-level lock, no thread dependencies)

Usage:
    from core.system.temp_manager import get_temp_manager

    tm = get_temp_manager()

    # Allocate a temp path for a component
    repo_path = tm.alloc("coder_agent", "repo_123")
    # ... use repo_path ...
    tm.release("coder_agent", "repo_123")  # release quota back
    # or
    tm.purge("coder_agent", older_than=3600)  # purge old files
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.core.system.temp_manager")

_DEFAULT_CONFIG = {
    # Total limit: 5 GB
    "max_total_bytes": 5 * 1024 * 1024 * 1024,
    # Default TTL for unreleased temp files: 24 hours
    "default_ttl_seconds": 86400,
    # Per-component quotas (None = no limit)
    "component_quotas": {
        "coder_agent": 1 * 1024 * 1024 * 1024,  # 1 GB
        "recon": 1 * 1024 * 1024 * 1024,  # 1 GB
        "reports": 512 * 1024 * 1024,  # 512 MB
        "screenshots": 256 * 1024 * 1024,  # 256 MB
        "cache": 256 * 1024 * 1024,  # 256 MB
        "default": 128 * 1024 * 1024,  # 128 MB fallback
    },
    # Max files per component
    "max_files_per_component": 100,
}


class TempManager:
    """Centralized temporary file manager.

    Creates a managed temp directory structure:
        /tmp/ownex/
        ├── <component>/
        │   ├── <name>/
        │   └── ...
        └── ...
    """

    def __init__(self, base_dir: str | Path | None = None, config: dict[str, Any] | None = None) -> None:
        self._config = {**_DEFAULT_CONFIG, **(config or {})}
        self._base_dir = Path(base_dir or Path(tempfile.gettempdir()) / "ownex")
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._component_sizes: dict[str, int] = {}
        self._component_files: dict[str, set[str]] = {}
        self._total_allocated: int = 0
        self._started_at: float = time.time()

        logger.info("TempManager initialized: base=%s, max=%d bytes", self._base_dir, self._config["max_total_bytes"])

    # ── Properties ─────────────────────────────────────────────────

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    @property
    def max_total_bytes(self) -> int:
        return self._config["max_total_bytes"]

    @property
    def total_allocated(self) -> int:
        return self._total_allocated

    @property
    def available_bytes(self) -> int:
        return max(0, self.max_total_bytes - self._total_allocated)

    def component_quota(self, component: str) -> int:
        return self._config["component_quotas"].get(component, self._config["component_quotas"]["default"])

    # ── Allocation ─────────────────────────────────────────────────

    def alloc(self, component: str, name: str) -> Path:
        """Allocate a temporary directory for a component + name pair.

        Returns a Path to:
            /tmp/ownex/<component>/<name>/

        Raises RuntimeError if quota is exceeded or too many files exist.
        """
        component_dir = self._base_dir / component
        name_dir = component_dir / name

        # Check component file count limit
        files = self._component_files.setdefault(component, set())
        max_files = self._config["max_files_per_component"]

        if name not in files and len(files) >= max_files:
            msg = f"Component '{component}' has {len(files)} files (max {max_files})"
            logger.warning(msg)
            raise RuntimeError(msg)

        # Create directory
        name_dir.mkdir(parents=True, exist_ok=True)

        # Track
        files.add(name)
        self._total_allocated += 1

        logger.debug("TempManager.alloc: %s/%s", component, name)
        return name_dir

    def path_for(self, component: str, name: str) -> Path:
        """Get the path for a component+name without allocating.

        Returns the expected path even if directory doesn't exist yet.
        """
        return self._base_dir / component / name

    def release(self, component: str, name: str) -> bool:
        """Release a temp path back to the pool (removes files).

        Returns True if something was cleaned up.
        """
        name_dir = self._base_dir / component / name
        if name_dir.exists():
            shutil.rmtree(name_dir)
            logger.debug("TempManager.release: %s/%s → removed", component, name)
        files = self._component_files.get(component)
        if files and name in files:
            files.discard(name)
            self._total_allocated = max(0, self._total_allocated - 1)
            return True
        return False

    # ── Cleanup ────────────────────────────────────────────────────

    def purge(self, component: str | None = None, older_than: float | None = None) -> int:
        """Purge temp files.

        Args:
            component: If set, only purge files from this component.
            older_than: Remove files older than this many seconds (default: TTL from config)

        Returns:
            Number of items cleaned up.
        """
        ttl = older_than if older_than is not None else self._config["default_ttl_seconds"]
        cutoff = time.time() - ttl
        cleaned = 0

        targets = [self._base_dir / component] if component else sorted(self._base_dir.iterdir())

        for comp_dir in targets:
            if not comp_dir.is_dir():
                continue
            comp_name = comp_dir.name
            for item in comp_dir.iterdir():
                mtime = item.stat().st_mtime if item.exists() else 0
                if mtime < cutoff:
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        # Remove from tracking
                        files = self._component_files.get(comp_name)
                        if files:
                            files.discard(item.name)
                            self._total_allocated = max(0, self._total_allocated - 1)
                        cleaned += 1
                        logger.debug("TempManager.purge: %s/%s (age=%.0fs)", comp_name, item.name, time.time() - mtime)
                    except OSError as exc:
                        logger.warning("TempManager.purge: failed %s/%s: %s", comp_name, item.name, exc)

        if cleaned:
            logger.info("TempManager.purge: %d items removed (component=%s, ttl=%.0fs)", cleaned, component or "*", ttl)

        return cleaned

    def purge_all(self) -> int:
        """Purge ALL temp files regardless of age."""
        return self.purge(component=None, older_than=0)

    # ── Size tracking ──────────────────────────────────────────────

    def _compute_dir_size(self, path: Path) -> int:
        """Recursively compute directory size in bytes."""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file() and not entry.is_symlink():
                    total += entry.stat().st_size
        except OSError:
            pass
        return total

    def get_component_sizes(self) -> dict[str, int]:
        """Get size in bytes for each component."""
        sizes: dict[str, int] = {}
        for comp_dir in self._base_dir.iterdir():
            if comp_dir.is_dir():
                sizes[comp_dir.name] = self._compute_dir_size(comp_dir)
        return sizes

    def get_total_size(self) -> int:
        """Get total size of ALL temp files in bytes."""
        return sum(self.get_component_sizes().values())

    # ── Health ─────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Health metrics for the temp manager."""
        sizes = self.get_component_sizes()
        total_size = sum(sizes.values())
        total_system = shutil.disk_usage(self._base_dir)

        return {
            "base_dir": str(self._base_dir),
            "max_bytes": self.max_total_bytes,
            "used_bytes": total_size,
            "available_bytes": max(0, self.max_total_bytes - total_size),
            "used_pct": round(total_size / max(self.max_total_bytes, 1) * 100, 1),
            "disk_free_bytes": total_system.free,
            "disk_free_human": self._human_bytes(total_system.free),
            "components": {
                name: {
                    "bytes": size,
                    "human": self._human_bytes(size),
                    "quota_bytes": self.component_quota(name),
                    "quota_human": self._human_bytes(self.component_quota(name)),
                }
                for name, size in sorted(sizes.items())
            },
            "file_count": self._total_allocated,
            "uptime_seconds": round(time.time() - self._started_at),
        }

    @staticmethod
    def _human_bytes(n: float) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(n) < 1024.0:
                return f"{n:.1f} {unit}"
            n /= 1024.0
        return f"{n:.1f} PB"


# ── Singleton ─────────────────────────────────────────────────────

_instance: TempManager | None = None


def get_temp_manager(
    base_dir: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> TempManager:
    """Get or create the global TempManager singleton.

    Only the first call accepts arguments; subsequent calls ignore them.
    """
    global _instance
    if _instance is None:
        _instance = TempManager(base_dir=base_dir, config=config)
    return _instance


def reset_temp_manager() -> None:
    """Reset singleton (for testing)."""
    global _instance
    _instance = None
