"""Device Identity Service — Singleton service for managing device identities."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from cores.device_identity.models import DeviceRegistration, generate_device_id

logger = logging.getLogger("ownex.device_identity")


class DeviceIdentityService:
    """Service for managing device identities across Desktop, Mobile, Watch."""

    def __init__(self, storage_path: str | None = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # Default to OWNEX data directory
            data_dir = os.environ.get("OWNEX_DATA_DIR")
            base = Path(data_dir) if data_dir else Path(__file__).resolve().parents[3] / "data"
            self.storage_path = base / "device_identity"

        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._devices: dict[str, dict] = {}
        self._load()

    def _get_file_path(self, device_id: str) -> Path:
        return self.storage_path / f"{device_id}.json"

    def _load(self) -> None:
        """Load all device identities from storage."""
        try:
            for file_path in self.storage_path.glob("*.json"):
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                        self._devices[data["device_id"]] = data
                except Exception as e:
                    logger.warning(f"Failed to load device identity from {e}: {e}")
        except Exception as e:
            logger.warning(f"Failed to load device identities: {e}")

    def _save(self, device: dict) -> None:
        """Save a device identity to storage."""
        try:
            file_path = self._get_file_path(device["device_id"])
            with open(file_path, "w") as f:
                json.dump(device, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save device identity: {e}")

    def register(self, registration: DeviceRegistration) -> dict:
        """Register a new device or update existing one."""
        device_id = registration.device_id or generate_device_id()

        device_data = {
            "device_id": device_id,
            "platform": registration.platform,
            "name": registration.name,
            "push_token": registration.push_token,
            "capabilities": registration.capabilities or [],
            "metadata": registration.metadata or {},
            "registered_at": registration.metadata.get("registered_at")
            or __import__("datetime").datetime.now().isoformat(),
            "last_seen": __import__("datetime").datetime.now().isoformat(),
        }

        self._devices[device_id] = device_data
        self._save(device_data)
        logger.info(f"Registered device: {device_id} ({registration.platform})")
        return device_data

    def get(self, device_id: str) -> dict | None:
        """Get device identity by ID."""
        return self._devices.get(device_id)

    def get_all(self) -> list[dict]:
        """Get all registered devices."""
        return list(self._devices.values())

    def update_last_seen(self, device_id: str) -> bool:
        """Update last seen timestamp for a device."""
        if device_id in self._devices:
            self._devices[device_id]["last_seen"] = __import__("datetime").datetime.now().isoformat()
            self._save(self._devices[device_id])
            return True
        return False

    def update_push_token(self, device_id: str, push_token: str) -> bool:
        """Update push token for a device."""
        if device_id in self._devices:
            self._devices[device_id]["push_token"] = push_token
            self._save(self._devices[device_id])
            return True
        return False

    def delete(self, device_id: str) -> bool:
        """Delete a device identity."""
        if device_id in self._devices:
            del self._devices[device_id]
            file_path = self.storage_path / f"{device_id}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        return False

    def get_by_platform(self, platform: str) -> list[dict]:
        """Get all devices for a specific platform."""
        return [d for d in self._devices.values() if d.get("platform") == platform]

    def cleanup_old(self, max_age_days: int = 90) -> int:
        """Remove devices not seen for max_age_days."""
        import time

        time.time() - (max_age_days * 86400)
        removed = 0
        to_remove = []

        for device_id, device in self._devices.items():
            try:
                last_seen = __import__("datetime").datetime.fromisoformat(device.get("last_seen", "")).timestamp()
                if last_seen < time.time() - (max_age_days * 86400):
                    to_remove.append(device_id)
            except Exception:
                pass

        for device_id in to_remove:
            self.delete(device_id)
            removed += 1

        return removed


# Singleton instance
_device_identity_service = None


def get_device_identity_service() -> DeviceIdentityService:
    """Get singleton instance of DeviceIdentityService."""
    global _device_identity_service
    if _device_identity_service is None:
        _device_identity_service = DeviceIdentityService()
    return _device_identity_service
