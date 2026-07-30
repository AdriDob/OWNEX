"""Persist license key + hardware binding to disk."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("ownex.license.store")


def _get_license_file() -> Path:
    from cores.platform.system import get_data_dir
    return get_data_dir() / "license.json"


class LicenseStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _get_license_file()

    def save(self, license_key: str, hardware_id: str, signature_b64: str | None = None) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "license_key": license_key,
            "hardware_id": hardware_id,
            "signature_b64": signature_b64 or "",
            "activated_at": __import__("time").time(),
        }
        self._path.write_text(json.dumps(data, indent=2))

    def load(self) -> dict | None:
        logger.info("[HW] LicenseStore.load: path = %s", self._path)
        logger.info("[HW] LicenseStore.load: exists = %s", self._path.exists())
        if not self._path.exists():
            logger.info("[HW] LicenseStore.load: returning None (no file)")
            return None
        try:
            data = json.loads(self._path.read_text())
            logger.info("[HW] LicenseStore.load: loaded = %s", {k: (v[:16] + "..." if isinstance(v, str) and len(v) > 16 else v) for k, v in data.items()})
            stored_hw = data.get("hardware_id", "")
            logger.info("[HW] LicenseStore.load: stored_hardware_id = %s", stored_hw)
            logger.info("[HW] LicenseStore.load: stored_hardware_id[:7] = %s", stored_hw[:7] if stored_hw else "(empty)")
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[HW] LicenseStore.load: FAILED: %s", exc)
            return None

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()

    @property
    def is_activated(self) -> bool:
        data = self.load()
        if not data:
            return False
        return bool(data.get("license_key"))


_store: LicenseStore | None = None


def get_license_store() -> LicenseStore:
    global _store
    if _store is None:
        _store = LicenseStore()
    return _store
