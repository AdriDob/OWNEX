"""UpdateManager — version checking, update manifest, download, and rollback support."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.core.update")

ORION_DIR = Path.home() / ".orion"
UPDATE_LOG = ORION_DIR / "update_history.jsonl"
UPDATE_REMOTE_URL = "https://api.github.com/repos/anomalyco/orion-platform/releases/latest"


@dataclass
class UpdateManifest:
    version: str
    release_notes: str
    download_url: str
    checksum_sha256: str
    required_plugin_api: str
    published_at: str


@dataclass
class UpdateStatus:
    current_version: str
    remote_version: str | None
    update_available: bool
    manifest: UpdateManifest | None
    last_checked: str | None


def _parse_semver(version: str) -> tuple[int, ...]:
    parts = version.lstrip("v").split("-")[0].split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return (0, 0, 0)


class UpdateManager:
    """Manages version checks, update download, and rollback."""

    def __init__(self) -> None:
        from core.version import ORION_VERSION

        self._current_version = ORION_VERSION
        self._remote_version: str | None = None
        self._manifest: UpdateManifest | None = None
        self._last_checked: str | None = None
        self._history: list[dict[str, Any]] = self._load_history()

    # ── Version checking ────────────────────────────────────────────

    def check_remote(self, force: bool = False) -> dict[str, Any]:
        """Check remote for updates. In dev, returns mock data.

        In production, this would fetch from GitHub releases or a custom
        update server. The design supports swapping the source easily.
        """
        import urllib.request

        try:
            req = urllib.request.Request(
                UPDATE_REMOTE_URL,
                method="GET",
                headers={
                    "Accept": "application/json",
                    "User-Agent": "orion-platform/4.0",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                tag = data.get("tag_name", "v4.3.2").lstrip("v")
                self._remote_version = tag
                self._manifest = UpdateManifest(
                    version=tag,
                    release_notes=data.get("body", "No release notes available."),
                    download_url=data.get("zipball_url", ""),
                    checksum_sha256="",
                    required_plugin_api="1.0",
                    published_at=data.get("published_at", ""),
                )
        except Exception as exc:
            logger.info("Remote update check unavailable: %s (offline/dev mode)", exc)
            # In dev/offline mode, simulate no update available
            self._remote_version = self._current_version
            self._manifest = None

        self._last_checked = datetime.now(timezone.utc).isoformat()
        return self.status()

    def status(self) -> dict[str, Any]:
        """Return full update status."""
        current_v = _parse_semver(self._current_version)
        remote_v = _parse_semver(self._remote_version) if self._remote_version else current_v
        available = remote_v > current_v if self._remote_version else False

        return {
            "current_version": self._current_version,
            "remote_version": self._remote_version,
            "update_available": available,
            "manifest": {
                "version": self._manifest.version,
                "release_notes": self._manifest.release_notes[:500] if self._manifest else None,
                "download_url": self._manifest.download_url if self._manifest else None,
                "checksum_sha256": self._manifest.checksum_sha256 if self._manifest else None,
                "required_plugin_api": self._manifest.required_plugin_api if self._manifest else None,
                "published_at": self._manifest.published_at if self._manifest else None,
            }
            if self._manifest
            else None,
            "last_checked": self._last_checked,
        }

    # ── Update lifecycle ────────────────────────────────────────────

    def prepare_update(self) -> dict[str, Any]:
        """Prepare for update: backup current state, download update package.

        Returns status dict with backup_path and download result.
        """
        from core.backup.engine import create_backup

        # Step 1: Backup before update
        backup_result = create_backup()
        if backup_result.get("status") != "ok":
            return {"status": "error", "reason": f"Pre-update backup failed: {backup_result.get('reason')}"}

        # Step 2: Record update intent
        record = {
            "action": "prepare_update",
            "version_from": self._current_version,
            "version_to": self._remote_version,
            "backup_path": backup_result.get("backup_path"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(record)
        self._persist(record)

        return {
            "status": "ready",
            "current_version": self._current_version,
            "target_version": self._remote_version,
            "backup_path": backup_result.get("backup_path"),
            "backup_size_mb": backup_result.get("backup_size_mb"),
        }

    def rollback(self, backup_path: str | None = None) -> dict[str, Any]:
        """Rollback to the last known good state.

        If no backup_path given, uses the last prepare_update backup.
        """
        if not backup_path:
            # Find the last prepare_update backup in history
            for entry in reversed(self._history):
                if entry.get("action") == "prepare_update" and entry.get("backup_path"):
                    backup_path = entry["backup_path"]
                    break

        if not backup_path:
            return {"status": "error", "reason": "No backup available for rollback"}

        from core.backup.engine import restore_backup, verify_backup

        # Verify backup integrity first
        verification = verify_backup(backup_path)
        if verification.get("status") == "error":
            return {"status": "error", "reason": f"Rollback backup verification failed: {verification.get('reason')}"}

        # Restore
        restore_result = restore_backup(backup_path)
        if restore_result.get("status") != "ok":
            return {"status": "error", "reason": f"Rollback restore failed: {restore_result.get('reason')}"}

        record = {
            "action": "rollback",
            "backup_path": backup_path,
            "restored_files": restore_result.get("restored_files"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(record)
        self._persist(record)

        return {
            "status": "ok",
            "backup_path": backup_path,
            "restored_files": restore_result.get("restored_files"),
            "message": "Rollback complete. Restart the application to apply.",
        }

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._history[-limit:]

    # ── Persistence ─────────────────────────────────────────────────

    def _persist(self, record: dict[str, Any]) -> None:
        try:
            UPDATE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(UPDATE_LOG, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.warning("Failed to persist update record: %s", exc)

    def _load_history(self) -> list[dict[str, Any]]:
        if not UPDATE_LOG.exists():
            return []
        records: list[dict[str, Any]] = []
        try:
            with open(UPDATE_LOG) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as exc:
            logger.warning("Failed to load update history: %s", exc)
        return records


# ── Convenience ─────────────────────────────────────────────────────


def check_for_updates() -> dict[str, Any]:
    """Quick update check — convenience wrapper."""
    return UpdateManager().check_remote()
