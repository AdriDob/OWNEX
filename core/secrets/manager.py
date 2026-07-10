"""Secrets Manager — single point of access for all API keys and credentials.

Backed by CATEYE's IdentityVault for AES-256-GCM encrypted storage.
Supports env var fallback for backward compatibility.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("orion.core.secrets")


class SecretsManager:
    """Centralized secrets storage via IdentityVault + env fallback.

    Priority:
      1. IdentityVault (persistent, encrypted)
      2. Environment variable
      3. Default value
    """

    def __init__(self) -> None:
        self._vault = None
        self._cache: dict[str, str] = {}

    # ── Read ─────────────────────────────────────────

    def get(self, key: str, default: str = "", use_cache: bool = True) -> str:
        """Get a secret by key.

        Checks: IdentityVault → env var → default.
        """
        if use_cache and key in self._cache:
            return self._cache[key]

        # 1. Try IdentityVault
        value = self._from_vault(key)
        if value:
            self._cache[key] = value
            return value

        # 2. Try env var
        value = os.environ.get(key, "")
        if value:
            self._cache[key] = value
            return value

        return default

    def get_or_raise(self, key: str) -> str:
        """Like get() but raises KeyError if not found."""
        value = self.get(key, use_cache=True)
        if not value:
            raise KeyError(f"Secret '{key}' not configured. Set it via IdentityVault or env var.")
        return value

    def _vault_provider(self, key: str) -> str:
        return f"_secret:{key}"

    def set(self, key: str, value: str) -> bool:
        """Store a secret in IdentityVault."""
        self._cache[key] = value
        vault = self._get_vault()
        if vault is None:
            logger.warning("IdentityVault not available — secret %s stored in memory only", key)
            return False
        try:
            vault.store_credentials(provider=self._vault_provider(key), email=key, token=value)
            logger.info("Secret %s stored in IdentityVault", key)
            return True
        except Exception as exc:
            logger.warning("Failed to store secret %s in vault (cached in memory): %s", key, exc)
            return False

    def delete(self, key: str) -> bool:
        """Delete a secret."""
        self._cache.pop(key, None)
        vault = self._get_vault()
        if vault is None:
            return True
        try:
            vault.remove_credentials(provider=self._vault_provider(key))
            return True
        except Exception as exc:
            logger.warning("Failed to delete secret %s from vault: %s", key, exc)
            return False

    def list_keys(self) -> list[str]:
        """List all known secret keys."""
        vault = self._get_vault()
        keys: set[str] = set()
        vault_prefix = "_secret:"
        if vault:
            try:
                for acct in vault.list_accounts() or []:
                    provider = acct.get("provider", "")
                    if provider.startswith(vault_prefix):
                        keys.add(provider[len(vault_prefix):])
            except Exception:
                logger.exception("Failed to list vault accounts")
        # Add env vars that look like secrets
        for env_key in os.environ:
            if any(suffix in env_key.upper() for suffix in ("API_KEY", "SECRET", "TOKEN", "PASSWORD")):
                keys.add(env_key)
        # Add cached keys
        keys.update(self._cache.keys())
        return sorted(keys)

    def health(self) -> dict:
        """Check if secrets backend is reachable."""
        vault = self._get_vault()
        return {
            "vault_available": vault is not None,
            "cached_keys": len(self._cache),
            "total_keys": len(self.list_keys()),
        }

    # ── Internal ─────────────────────────────────────

    def _from_vault(self, key: str) -> str:
        vault = self._get_vault()
        if vault is None:
            return ""
        try:
            creds = vault.get_credentials(provider=self._vault_provider(key), email=key)
            return creds.get("token", "") if creds else ""
        except Exception:
            return ""

    def _get_vault(self) -> Any:
        if self._vault is not None:
            return self._vault
        try:
            from cores.identity_vault import get_identity_vault
            self._vault = get_identity_vault()
            return self._vault
        except Exception as exc:
            logger.debug("IdentityVault not available: %s", exc)
            return None


_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    global _manager
    if _manager is None:
        _manager = SecretsManager()
    return _manager
