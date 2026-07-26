from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.auth.credentials import CredentialEntry, CredentialStore
from core.auth.injector import apply_auth_to_request_kwargs
from core.auth.provider import AuthConfig, get_provider

logger = logging.getLogger("cateye.auth.manager")


@dataclass
class AuthTarget:
    target_id: int
    target_name: str
    auth_config: AuthConfig
    enabled: bool = True


class AuthManager:
    def __init__(self, store: CredentialStore | None = None):
        self._store = store or CredentialStore()
        self._targets: dict[int, AuthTarget] = {}

    def register_target(self, target: AuthTarget) -> None:
        errors = target.auth_config.validate()
        if errors:
            logger.warning("Auth config for target %d has validation errors: %s", target.target_id, errors)
        self._targets[target.target_id] = target
        self._store.store(
            CredentialEntry(
                provider=str(target.target_id),
                auth_type=target.auth_config.auth_type,
                params=target.auth_config.params,
                label=f"target_{target.target_id}",
            )
        )
        logger.info("Auth registered for target %s (ID %d)", target.target_name, target.target_id)

    def unregister_target(self, target_id: int) -> bool:
        removed = self._targets.pop(target_id, None)
        self._store.delete(f"target_{target_id}")
        if removed:
            logger.info("Auth unregistered for target ID %d", target_id)
        return removed is not None

    def get_auth(self, target_id: int) -> AuthConfig | None:
        target = self._targets.get(target_id)
        if not target or not target.enabled:
            return None
        return target.auth_config

    def apply_auth(self, target_id: int, kwargs: dict[str, Any]) -> dict[str, Any]:
        config = self.get_auth(target_id)
        if config is None:
            return kwargs
        return apply_auth_to_request_kwargs(kwargs, config)

    def list_targets(self) -> list[AuthTarget]:
        return list(self._targets.values())

    def enable_target(self, target_id: int) -> bool:
        target = self._targets.get(target_id)
        if not target:
            return False
        target.enabled = True
        return True

    def disable_target(self, target_id: int) -> bool:
        target = self._targets.get(target_id)
        if not target:
            return False
        target.enabled = False
        return True

    def test_auth(self, target_id: int, test_url: str | None = None) -> bool:
        config = self.get_auth(target_id)
        if config is None:
            return False
        provider = get_provider(config.auth_type)
        if not provider:
            return False
        result = provider.test_connection(config, test_url)
        logger.info("Auth test for target %d: %s", target_id, "passed" if result else "failed")
        return result


_AUTH_MANAGER: AuthManager | None = None


def get_auth_manager() -> AuthManager:
    global _AUTH_MANAGER
    if _AUTH_MANAGER is None:
        _AUTH_MANAGER = AuthManager()
    return _AUTH_MANAGER
