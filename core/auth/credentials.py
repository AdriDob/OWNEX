from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from core.auth.provider import AuthType

logger = logging.getLogger("ownex.auth.credentials")


@dataclass
class CredentialEntry:
    provider: str
    auth_type: AuthType
    params: dict[str, Any] = field(default_factory=dict)
    label: str = ""
    created_at: str = ""
    updated_at: str = ""


class CredentialStore:
    def __init__(self, vault: Any | None = None):
        self._vault = vault

    def _get_vault(self) -> Any:
        if self._vault is None:
            from cores.identity_vault import get_identity_vault

            self._vault = get_identity_vault()
        return self._vault

    def store(self, entry: CredentialEntry) -> None:
        vault = self._get_vault()
        provider_key = f"auth_{entry.label or entry.provider}"
        serialized = {
            "provider": entry.provider,
            "auth_type": entry.auth_type.value,
            "params": entry.params,
            "label": entry.label,
        }
        token = json.dumps(serialized)
        vault.store_credentials(
            provider=provider_key,
            email=f"auth@{entry.provider}",
            token=token,
        )
        logger.info("Credential stored: %s", provider_key)

    def load(self, label: str) -> CredentialEntry | None:
        vault = self._get_vault()
        provider_key = f"auth_{label}"
        raw = vault.get_credentials(provider_key)
        token_raw = raw.get("token", "")
        if not token_raw:
            return None
        try:
            data = json.loads(token_raw)
        except (json.JSONDecodeError, TypeError):
            return None
        return CredentialEntry(
            provider=data.get("provider", ""),
            auth_type=AuthType(data.get("auth_type", "bearer_token")),
            params=data.get("params", {}),
            label=data.get("label", label),
        )

    def delete(self, label: str) -> bool:
        vault = self._get_vault()
        provider_key = f"auth_{label}"
        try:
            vault.store_credentials(
                provider=provider_key,
                email="",
                token="",
            )
            logger.info("Credential deleted: %s", provider_key)
            return True
        except Exception as e:
            logger.warning("Failed to delete credential %s: %s", provider_key, e)
            return False

    def list_labels(self) -> list[str]:
        vault = self._get_vault()
        raw = vault.get_credentials("auth_")
        if not raw:
            return []
        return [k.removeprefix("auth_") for k in raw if k.startswith("auth_")]
