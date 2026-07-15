from __future__ import annotations

import logging
import tarfile
import time
from pathlib import Path

from core import ORION_DIR

logger = logging.getLogger("cateye.backup")

BACKUP_PATHS = [
    "catseye.db",
    "config.json",
    "audit.jsonl",
    "identity_vault.key",
    "evidence/",
]


def create_backup(output_dir: str | None = None) -> Path | None:
    dest = Path(output_dir) if output_dir else ORION_DIR
    dest.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    archive = dest / f"cateye_backup_{timestamp}.tar.gz"

    with tarfile.open(archive, "w:gz") as tar:
        for rel_path in BACKUP_PATHS:
            full = ORION_DIR / rel_path
            if full.exists():
                tar.add(full, arcname=rel_path)
                logger.info("Backup: added %s", rel_path)
    logger.info("Backup created: %s (%d bytes)", archive, archive.stat().st_size)
    return archive


def restore_backup(archive_path: str) -> bool:
    archive = Path(archive_path)
    if not archive.exists():
        logger.error("Backup not found: %s", archive_path)
        return False
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(path=ORION_DIR, filter="data")
    logger.info("Restored from %s", archive_path)
    return True
