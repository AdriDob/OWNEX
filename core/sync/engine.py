"""Multi-device sync engine — encrypted config/preferences/decisions sync.

Architecture:
  - Collects syncable data (config, preferences, decisions, notification state)
  - Encrypts with AES-256-GCM using a shared sync key
  - Syncs via configurable transport (HTTP PUT/GET or file export/import)
  - Never syncs: vault, private keys, secrets

Usage:
  engine = SyncEngine()
  engine.push()        # push local state to sync targets
  engine.pull()        # pull and merge remote state
  engine.status()      # check sync health
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from core import ORION_DIR

logger = logging.getLogger("orion.core.sync")

SYNC_CACHE = ORION_DIR / "sync_cache.json"
SYNC_KEY_FILE = ORION_DIR / "sync_key"
SYNC_CONFIG = ORION_DIR / "sync_config.json"

# Fields that are safe to sync (no secrets)
SYNCABLE_CONFIG_KEYS = [
    "general",
    "ai",
    "appearance",
    "accessibility",
    "missionControl.limits",
    "missionControl.speed",
    "missionControl.parallelism",
    "missionControl.depth",
]

SYNCABLE_DOMAINS = {
    "settings": {"label": "Configuración", "priority": "high"},
    "preferences": {"label": "Preferencias", "priority": "high"},
    "decisions": {"label": "Decisiones", "priority": "medium"},
    "notification_state": {"label": "Estado de notificaciones", "priority": "low"},
}


class SyncEngine:
    def __init__(self) -> None:
        self._sync_key: str | None = None
        self._load_key()

    # ── Key management ────────────────────────────────

    def _load_key(self) -> None:
        if SYNC_KEY_FILE.exists():
            try:
                self._sync_key = SYNC_KEY_FILE.read_text().strip()
            except OSError:
                self._sync_key = None

    def set_key(self, key: str) -> None:
        SYNC_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        SYNC_KEY_FILE.write_text(key)
        SYNC_KEY_FILE.chmod(0o600)
        self._sync_key = key
        logger.info("Sync key set")

    def has_key(self) -> bool:
        return bool(self._sync_key)

    # ── Encryption ────────────────────────────────────

    def _encrypt(self, data: bytes) -> bytes:
        if not self._sync_key:
            raise RuntimeError("Sync key not set")
        try:
            from cores.vault_crypto import encrypt

            return encrypt(data, self._sync_key.encode())
        except ImportError:
            from base64 import urlsafe_b64encode
            from hashlib import sha256

            from cryptography.fernet import Fernet

            key = urlsafe_b64encode(sha256(self._sync_key.encode()).digest())
            f = Fernet(key)
            return f.encrypt(data)

    def _decrypt(self, data: bytes) -> bytes:
        if not self._sync_key:
            raise RuntimeError("Sync key not set")
        try:
            from cores.vault_crypto import decrypt

            return decrypt(data, self._sync_key.encode())
        except ImportError:
            from base64 import urlsafe_b64encode
            from hashlib import sha256

            from cryptography.fernet import Fernet

            key = urlsafe_b64encode(sha256(self._sync_key.encode()).digest())
            f = Fernet(key)
            return f.decrypt(data)

    # ── Data collection ───────────────────────────────

    def _collect_syncable_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "device_id": self._get_device_id(),
            "synced_at": time.time(),
            "version": 1,
        }

        settings = self._load_settings()
        if settings:
            data["settings"] = settings

        decisions = self._load_decisions()
        if decisions:
            data["decisions"] = decisions

        notifications = self._load_notification_state()
        if notifications:
            data["notification_state"] = notifications

        return data

    def _get_device_id(self) -> str:
        try:
            from core.secrets.manager import get_secrets_manager

            mgr = get_secrets_manager()
            device = mgr.get_or_raise("device_id") if hasattr(mgr, "get_or_raise") else ""
            if device:
                return device
        except Exception:
            pass
        import socket

        return socket.gethostname()

    def _load_settings(self) -> dict[str, Any] | None:
        try:
            from desktop.settings import DesktopSettings

            ds = DesktopSettings()
            raw = ds._data if hasattr(ds, "_data") else {}
            return {
                k: v
                for k, v in raw.items()
                if any(k.startswith(p) for p in ["general", "ai_", "appearance", "accessibility"])
            }
        except Exception:
            return None

    def _load_decisions(self) -> list[dict[str, Any]] | None:
        try:
            from core.decision_journal import get_decisions

            return get_decisions(limit=100)
        except Exception:
            return None

    def _load_notification_state(self) -> dict[str, Any] | None:
        try:
            from cores.notifications.hub import get_hub

            hub = get_hub()
            return {"digest_mode": hub.is_digest_mode(), "dedup_window": hub.get_dedup_window()}
        except Exception:
            return None

    # ── Sync operations ───────────────────────────────

    def prepare_sync_package(self) -> dict[str, Any]:
        data = self._collect_syncable_data()
        raw = json.dumps(data, default=str).encode()
        encrypted = self._encrypt(raw)
        return {
            "status": "ok",
            "size_bytes": len(raw),
            "size_encrypted": len(encrypted),
            "checksum": __import__("hashlib").sha256(raw).hexdigest(),
            "domains": list(data.keys()),
            "device_id": data.get("device_id"),
            "synced_at": data.get("synced_at"),
        }

    def push(self, endpoint: str | None = None) -> dict[str, Any]:
        if not self._sync_key:
            return {"status": "error", "reason": "Sync key not set. Use set_key() first."}

        data = self._collect_syncable_data()
        raw = json.dumps(data, default=str).encode()
        encrypted = self._encrypt(raw)

        if endpoint:
            return self._http_push(endpoint, encrypted)
        return self._file_push(raw, encrypted)

    def pull(self, endpoint: str | None = None) -> dict[str, Any]:
        if not self._sync_key:
            return {"status": "error", "reason": "Sync key not set."}

        if endpoint:
            return self._http_pull(endpoint)
        return self._file_pull()

    def _http_push(self, endpoint: str, encrypted: bytes) -> dict[str, Any]:
        try:
            import httpx

            resp = httpx.put(endpoint, content=encrypted, timeout=30)
            if resp.is_success:
                self._save_cache(encrypted)
                return {"status": "ok", "target": endpoint, "size": len(encrypted)}
            return {"status": "error", "reason": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as exc:
            return {"status": "error", "reason": str(exc)[:200]}

    def _http_pull(self, endpoint: str) -> dict[str, Any]:
        try:
            import httpx

            resp = httpx.get(endpoint, timeout=30)
            if not resp.is_success:
                return {"status": "error", "reason": f"HTTP {resp.status_code}"}
            decrypted = self._decrypt(resp.content)
            data = json.loads(decrypted)
            self._merge(data)
            return {"status": "ok", "domains": list(data.keys()), "device_id": data.get("device_id")}
        except Exception as exc:
            return {"status": "error", "reason": str(exc)[:200]}

    def _file_push(self, raw: bytes, encrypted: bytes) -> dict[str, Any]:
        ORION_DIR.mkdir(parents=True, exist_ok=True)
        export_path = ORION_DIR / f"orion_sync_{int(time.time())}.enc"
        export_path.write_bytes(encrypted)
        # Also save a human-readable version for manual review (no secrets)
        plain_path = ORION_DIR / f"orion_sync_{int(time.time())}.json"
        plain_path.write_bytes(raw)
        logger.info("Sync package saved: %s", export_path)
        return {"status": "ok", "path": str(export_path), "plain_path": str(plain_path), "size": len(encrypted)}

    def _file_pull(self, path: str | None = None) -> dict[str, Any]:
        if path is None:
            enc_files = sorted(ORION_DIR.glob("orion_sync_*.enc"), reverse=True)
            if not enc_files:
                return {"status": "error", "reason": "No sync packages found"}
            path = str(enc_files[0])

        try:
            encrypted = Path(path).read_bytes()
            decrypted = self._decrypt(encrypted)
            data = json.loads(decrypted)
            self._merge(data)
            return {"status": "ok", "domains": list(data.keys()), "device_id": data.get("device_id")}
        except Exception as exc:
            return {"status": "error", "reason": str(exc)[:300]}

    def _merge(self, remote: dict[str, Any]) -> None:
        local = self._collect_syncable_data()
        remote_ts = remote.get("synced_at", 0)
        local_ts = local.get("synced_at", 0)

        merged = remote if remote_ts >= local_ts else local
        self._save_cache(merged)
        logger.info("Sync merged (remote_ts=%s, local_ts=%s)", remote_ts, local_ts)

    def _save_cache(self, data: Any) -> None:
        raw = (
            data
            if isinstance(data, bytes)
            else json.dumps(data, default=str).encode()
            if isinstance(data, dict)
            else data
        )
        SYNC_CACHE.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(raw, bytes):
            SYNC_CACHE.write_bytes(raw)
        else:
            SYNC_CACHE.write_text(raw)

    def status(self) -> dict[str, Any]:
        cache_exists = SYNC_CACHE.exists()
        return {
            "has_key": self.has_key(),
            "cache_exists": cache_exists,
            "cache_size": SYNC_CACHE.stat().st_size if cache_exists else 0,
            "syncable_domains": SYNCABLE_DOMAINS,
            "device_id": self._get_device_id(),
            "sync_config_path": str(SYNC_CONFIG) if SYNC_CONFIG.exists() else None,
        }


_SYNC_ENGINE: SyncEngine | None = None


def get_sync_engine() -> SyncEngine:
    global _SYNC_ENGINE
    if _SYNC_ENGINE is None:
        _SYNC_ENGINE = SyncEngine()
    return _SYNC_ENGINE
