"""Backup Targets — local, rclone, and external storage support."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess  # noqa: S404 — intentional CLI invocation
from dataclasses import dataclass
from typing import Any

from core import ORION_DIR

logger = logging.getLogger("orion.core.backup.targets")

BACKUP_DIR = ORION_DIR / "backups"
TARGETS_CONFIG = ORION_DIR / "backup_targets.json"

BACKUP_TARGETS: dict[str, dict[str, Any]] = {}


@dataclass
class TargetStatus:
    name: str
    type: str
    enabled: bool
    available: bool
    last_sync: str | None = None
    error: str | None = None


def load_targets() -> dict[str, dict[str, Any]]:
    global BACKUP_TARGETS
    if BACKUP_TARGETS:
        return BACKUP_TARGETS
    if TARGETS_CONFIG.exists():
        try:
            BACKUP_TARGETS = json.loads(TARGETS_CONFIG.read_text())
        except Exception as exc:
            logger.warning("Failed to load backup targets: %s", exc)
            BACKUP_TARGETS = {}
    return BACKUP_TARGETS


def save_targets() -> None:
    TARGETS_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    TARGETS_CONFIG.write_text(json.dumps(BACKUP_TARGETS, indent=2))


def register_target(name: str, target_type: str, config: dict[str, Any]) -> dict[str, Any]:
    load_targets()
    BACKUP_TARGETS[name] = {"type": target_type, "enabled": True, "config": config}
    save_targets()
    return {"status": "ok", "name": name, "type": target_type}


def remove_target(name: str) -> dict[str, Any]:
    load_targets()
    if name in BACKUP_TARGETS:
        del BACKUP_TARGETS[name]
        save_targets()
        return {"status": "ok", "name": name}
    return {"status": "error", "reason": f"Target '{name}' not found"}


def list_targets() -> list[dict[str, Any]]:
    load_targets()
    results: list[dict[str, Any]] = []
    for name, cfg in BACKUP_TARGETS.items():
        status = check_target(name)
        results.append(
            {
                "name": name,
                "type": cfg.get("type", "unknown"),
                "enabled": cfg.get("enabled", True),
                "available": status.available,
                "last_sync": status.last_sync,
                "error": status.error,
            }
        )
    # Always include local target
    local_status = check_target("local")
    results.insert(
        0,
        {
            "name": "local",
            "type": "local",
            "enabled": True,
            "available": local_status.available,
            "last_sync": local_status.last_sync,
            "error": local_status.error,
        },
    )
    return results


def check_target(name: str) -> TargetStatus:
    if name == "local":
        return TargetStatus(name="local", type="local", enabled=True, available=BACKUP_DIR.exists())

    load_targets()
    cfg = BACKUP_TARGETS.get(name)
    if not cfg:
        return TargetStatus(name=name, type="unknown", enabled=False, available=False, error="Target not registered")

    ttype = cfg.get("type", "")
    enabled = cfg.get("enabled", True)

    if ttype == "rclone":
        rclone_path = shutil.which("rclone")
        if not rclone_path:
            return TargetStatus(
                name=name, type="rclone", enabled=enabled, available=False, error="rclone not installed"
            )
        remote = cfg.get("config", {}).get("remote", "")
        if not remote:
            return TargetStatus(
                name=name, type="rclone", enabled=enabled, available=False, error="No remote configured"
            )
        try:
            r = subprocess.run(
                [rclone_path, "lsf", remote, "--max-depth", "1"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0:
                return TargetStatus(name=name, type="rclone", enabled=enabled, available=True)
            return TargetStatus(
                name=name, type="rclone", enabled=enabled, available=False, error=r.stderr.strip()[:200]
            )
        except subprocess.TimeoutExpired:
            return TargetStatus(name=name, type="rclone", enabled=enabled, available=False, error="Timeout")
        except OSError as exc:
            return TargetStatus(name=name, type="rclone", enabled=enabled, available=False, error=str(exc)[:200])

    return TargetStatus(name=name, type=ttype, enabled=enabled, available=False, error=f"Unknown target type: {ttype}")


def sync_to_target(name: str, backup_path: str) -> dict[str, Any]:
    if name == "local":
        return {"status": "ok", "message": "Local backup already created", "target": "local"}

    load_targets()
    cfg = BACKUP_TARGETS.get(name)
    if not cfg:
        return {"status": "error", "reason": f"Target '{name}' not found"}
    if not cfg.get("enabled", True):
        return {"status": "error", "reason": f"Target '{name}' is disabled"}

    ttype = cfg.get("type", "")

    if ttype == "rclone":
        return _sync_rclone(name, cfg.get("config", {}), backup_path)

    return {"status": "error", "reason": f"Unsupported target type: {ttype}"}


def sync_to_all(backup_path: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name in BACKUP_TARGETS:
        if BACKUP_TARGETS[name].get("enabled", True):
            results.append(sync_to_target(name, backup_path))
    return results


def _sync_rclone(name: str, config: dict[str, Any], backup_path: str) -> dict[str, Any]:
    rclone_path = shutil.which("rclone")
    if not rclone_path:
        return {"status": "error", "reason": "rclone not installed", "target": name}

    remote = config.get("remote", "")
    dest_path = config.get("path", "orion-backups")
    if not remote:
        return {"status": "error", "reason": "No remote configured", "target": name}

    dest = f"{remote}:{dest_path}" if dest_path else f"{remote}:"
    try:
        r = subprocess.run(
            [rclone_path, "copy", backup_path, dest, "--progress"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if r.returncode == 0:
            logger.info("Backup synced to rclone target '%s': %s", name, dest)
            return {"status": "ok", "target": name, "destination": dest}
        return {"status": "error", "reason": r.stderr.strip()[:300], "target": name}
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": "Timeout (5min)", "target": name}
    except OSError as exc:
        return {"status": "error", "reason": str(exc)[:200], "target": name}
