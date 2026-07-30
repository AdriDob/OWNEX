"""Identity Vault — secure provider credential management.

Stores encrypted credentials for bug bounty platforms.
Encryption at rest using AES-256-GCM with a randomly generated key
stored in ~/.orion/identity_vault.key (chmod 600).

Previously derived the AES key from /etc/machine-id (CVE-2) —
this version auto-migrates existing vaults to a random file key.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from cores.vault_crypto import decrypt as _decrypt
from cores.vault_crypto import encrypt as _encrypt
from cores.vault_crypto import get_vault_key

logger = logging.getLogger("cateye.identity_vault")

_VAULT_PATH: str | None = None
_VAULT_DATA: dict[str, dict[str, Any]] = {}


def _get_vault_dir() -> str:
    home = os.environ.get("HOME", os.environ.get("USERPROFILE", "."))
    return os.path.join(home, ".orion")


def _get_vault_path() -> str:
    global _VAULT_PATH
    if _VAULT_PATH is None:
        _VAULT_PATH = os.path.join(_get_vault_dir(), "identity_vault.json")
    return _VAULT_PATH


def _get_machine_id() -> str:
    raw: list[str] = []
    etc_machine = "/etc/machine-id"
    if os.path.exists(etc_machine):
        try:
            with open(etc_machine) as f:
                raw.append(f.read().strip())
        except Exception as exc:
            logger.warning("Failed to read machine-id: %s", exc)
    if not raw:
        raw.append(os.environ.get("HOSTNAME", "CATEYE-default"))
    seen: set[str] = set()
    deduped: list[str] = []
    for v in raw:
        if v and v not in seen:
            deduped.append(v)
            seen.add(v)
    return "|".join(deduped)


def _get_old_machine_id_key() -> bytes:
    return hashlib.sha256(_get_machine_id().encode()).digest()


def _maybe_migrate_vault() -> None:
    vault_path = _get_vault_path()
    if not os.path.exists(vault_path):
        return
    try:
        with open(vault_path) as f:
            data = json.load(f)
    except Exception:
        return
    if data.get("_key_version") == "file":
        return

    old_key = _get_old_machine_id_key()
    get_vault_key()
    migrated = 0

    for provider, entry in data.items():
        if provider == "_key_version":
            continue
        for field in ("encrypted_token", "encrypted_password"):
            encrypted = entry.get(field, "")
            if not encrypted:
                continue
            try:
                raw = base64.b64decode(encrypted)
                nonce = raw[:12]
                ciphertext = raw[12:]
                plain = AESGCM(old_key).decrypt(nonce, ciphertext, None).decode("utf-8")
                entry[field] = _encrypt(plain)
                migrated += 1
            except Exception as exc:
                logger.warning("Failed to migrate credential for %s: %s", provider, exc)

    if migrated:
        data["_key_version"] = "file"
        with open(vault_path, "w") as f:
            json.dump(data, f, indent=2)
        os.chmod(vault_path, 0o600)
        logger.info("Migrated %d credentials from machine-id key to file key", migrated)


class IdentityVault:
    """Secure credential vault for bug bounty provider accounts."""

    SUPPORTED_PROVIDERS = [
        "hackerone",
        "bugcrowd",
        "huntr",
        "immunefi",
        "intigriti",
        "yeswehack",
        "github",
        "synack",
    ]

    def __init__(self) -> None:
        self._load()

    def list_accounts(self) -> list[dict[str, Any]]:
        result = []
        for provider, data in _VAULT_DATA.items():
            result.append(
                {
                    "provider_name": provider,
                    "email": data.get("email", ""),
                    "session_state": data.get("session_state", "disconnected"),
                    "last_checked": data.get("last_checked"),
                    "health_status": data.get("health_status", "unknown"),
                    "has_credentials": bool(data.get("encrypted_token") or data.get("encrypted_password")),
                }
            )
        return result

    def get_account(self, provider: str) -> dict[str, Any] | None:
        data = _VAULT_DATA.get(provider)
        if not data:
            return None
        return {
            "provider_name": provider,
            "email": data.get("email", ""),
            "session_state": data.get("session_state", "disconnected"),
            "last_checked": data.get("last_checked"),
            "health_status": data.get("health_status", "unknown"),
            "has_credentials": bool(data.get("encrypted_token") or data.get("encrypted_password")),
        }

    def store_credentials(
        self,
        provider: str,
        email: str,
        token: str = "",
        password: str = "",
        metadata: dict[str, str] | None = None,
    ) -> None:
        if provider not in self.SUPPORTED_PROVIDERS and provider not in _VAULT_DATA:
            logger.warning("Storing credentials for unsupported provider: %s", provider)

        entry = {
            "email": email,
            "session_state": "disconnected",
            "last_checked": datetime.now(UTC).isoformat(),
            "health_status": "unknown",
            "encrypted_token": _encrypt(token) if token else "",
            "encrypted_password": _encrypt(password) if password else "",
            "metadata": json.dumps(metadata or {}),
        }

        if provider in _VAULT_DATA:
            existing = _VAULT_DATA[provider]
            entry["session_state"] = existing.get("session_state", "disconnected")
            entry["health_status"] = existing.get("health_status", "unknown")
            if not token:
                entry["encrypted_token"] = existing.get("encrypted_token", "")
            if not password:
                entry["encrypted_password"] = existing.get("encrypted_password", "")

        _VAULT_DATA[provider] = entry
        self._save()
        logger.info("Credentials stored for provider: %s (email: %s)", provider, email)

    def get_credentials(self, provider: str) -> dict[str, str]:
        data = _VAULT_DATA.get(provider)
        if not data:
            return {}

        token = _decrypt(data.get("encrypted_token", ""))
        password = _decrypt(data.get("encrypted_password", ""))
        metadata_raw = data.get("metadata", "{}")
        try:
            metadata = json.loads(metadata_raw)
        except (json.JSONDecodeError, TypeError):
            metadata = {}

        return {
            "email": data.get("email", ""),
            "token": token,
            "password": password,
            **metadata,
        }

    def remove_credentials(self, provider: str) -> None:
        if provider in _VAULT_DATA:
            del _VAULT_DATA[provider]
            self._save()
            logger.info("Credentials removed for provider: %s", provider)

    def update_session_state(self, provider: str, state: str) -> None:
        if provider in _VAULT_DATA:
            _VAULT_DATA[provider]["session_state"] = state
            _VAULT_DATA[provider]["last_checked"] = datetime.now(UTC).isoformat()
            self._save()

    def update_health(self, provider: str, status: str) -> None:
        if provider in _VAULT_DATA:
            _VAULT_DATA[provider]["health_status"] = status
            _VAULT_DATA[provider]["last_checked"] = datetime.now(UTC).isoformat()
            self._save()

    def check_session_health(self, provider: str) -> dict[str, Any]:
        data = _VAULT_DATA.get(provider)
        if not data:
            return {"connected": False, "reason": "No credentials stored"}

        last_checked_str = data.get("last_checked", "")
        last_checked = None
        if last_checked_str:
            with contextlib.suppress(ValueError, TypeError):
                last_checked = datetime.fromisoformat(last_checked_str)

        hours_since_check = 999
        if last_checked:
            hours_since_check = int((datetime.now(UTC) - last_checked).total_seconds() / 3600)

        state = data.get("session_state", "disconnected")
        has_creds = bool(data.get("encrypted_token") or data.get("encrypted_password"))

        if state == "connected" and hours_since_check < 24 and has_creds:
            return {"connected": True, "reason": "Session appears valid"}
        elif state == "connected" and hours_since_check >= 24:
            return {"connected": False, "reason": "Session may have expired — re-check"}
        else:
            return {"connected": False, "reason": f"State: {state}"}

    def connected_count(self) -> int:
        return sum(1 for d in _VAULT_DATA.values() if d.get("session_state") == "connected")

    def clear_all(self) -> None:
        _VAULT_DATA.clear()
        self._save()
        logger.info("Identity vault cleared")

    def _load(self) -> None:
        path = _get_vault_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    loaded = json.load(f)
                _VAULT_DATA.clear()
                _VAULT_DATA.update({k: v for k, v in loaded.items() if not k.startswith("_")})
                logger.info("Loaded identity vault from %s (%d entries)", path, len(_VAULT_DATA))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load identity vault: %s", exc)
        _maybe_migrate_vault()

    def _save(self) -> None:
        path = _get_vault_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            data = dict(_VAULT_DATA)
            data["_key_version"] = "file"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            os.chmod(path, 0o600)
        except OSError as exc:
            logger.warning("Failed to save identity vault: %s", exc)


_VAULT_INSTANCE: IdentityVault | None = None


def get_identity_vault() -> IdentityVault:
    global _VAULT_INSTANCE
    if _VAULT_INSTANCE is None:
        _VAULT_INSTANCE = IdentityVault()
    return _VAULT_INSTANCE
