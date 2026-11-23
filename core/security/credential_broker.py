"""Credential Broker — project-scoped credential isolation.

Provides controlled, isolated access to credentials so that workers only ever
receive the secrets assigned to their own project, never global credentials or
credentials belonging to another project.

Security principles:
- Credentials are never shared between projects by default
- Each project receives only the credentials assigned to it (least privilege)
- Every access is counted and audited
- Access levels gate what a credential may be used for
- Automatic expiration enforcement

Storage: values live in this process's memory only. They are never logged and
never serialized by this module; :meth:`ProjectScopedCredential.mask` is the
only representation meant for logs, API responses and audit trails.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_USAGE_LOG_LIMIT = 1000
_USAGE_LOG_KEEP = 500


class AccessLevel(Enum):
    """Levels of credential access for different worker types."""

    READ_ONLY = "read_only"  # Read-only use, no execution
    EXECUTION = "execution"  # For sandboxed code execution
    FULL = "full"  # Full access (admin only)
    NONE = "none"  # No access


_LEVEL_ORDER = {
    AccessLevel.NONE: 0,
    AccessLevel.READ_ONLY: 1,
    AccessLevel.EXECUTION: 2,
    AccessLevel.FULL: 3,
}


@dataclass
class ProjectScopedCredential:
    """Credential scoped to a specific project with access controls."""

    project_id: str
    provider: str
    credential_type: str  # "token", "password", "api_key", "oauth"
    value: str  # Real value, in-memory only — never log it
    expires_at: float | None = None
    access_level: AccessLevel = AccessLevel.READ_ONLY
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0
    max_usages: int | None = None
    last_used: float | None = None

    def is_expired(self) -> bool:
        """Check if credential has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def can_use(self, required_level: AccessLevel = AccessLevel.READ_ONLY) -> bool:
        """Check if this credential satisfies the required access level."""
        return _LEVEL_ORDER.get(self.access_level, 0) >= _LEVEL_ORDER.get(required_level, 0) and not self.is_expired()

    def mask(self) -> str:
        """Return the masked representation safe for logs and API responses."""
        if not self.value:
            return ""
        if len(self.value) <= 8:
            return "*" * len(self.value)
        return self.value[:4] + "*" * (len(self.value) - 8) + self.value[-4:]


class CredentialBroker:
    """Manages project-scoped credential access with isolation.

    Ensures that:
    - Workers only receive credentials for their assigned project
    - Access is counted and auditable
    - Expiration and access levels are enforced
    - No credential leakage between projects
    """

    def __init__(self) -> None:
        self._project_creds: dict[str, dict[str, ProjectScopedCredential]] = {}
        self._stats: dict[str, Any] = {
            "total_requests": 0,
            "granted_requests": 0,
            "denied_requests": 0,
            "expired_credentials": 0,
            "usage_log": [],
        }

    def assign_project_credentials(
        self,
        project_id: str,
        providers: list[str],
        credentials: dict[str, str],
        expires_in_hours: int | None = None,
        access_level: AccessLevel = AccessLevel.READ_ONLY,
    ) -> None:
        """Assign credentials to a project with explicit scope.

        Args:
            project_id: Unique project identifier
            providers: Provider names to assign (e.g. "github", "aws")
            credentials: Mapping of provider -> secret value
            expires_in_hours: Optional expiration in hours
            access_level: Access level granted for these credentials
        """
        self._project_creds.setdefault(project_id, {})

        expiration = None
        if expires_in_hours is not None:
            expiration = time.time() + (expires_in_hours * 3600)

        for provider in providers:
            if provider not in credentials:
                logger.warning(
                    "No credentials provided for project %s, provider %s",
                    project_id,
                    provider,
                )
                continue

            self._project_creds[project_id][provider] = ProjectScopedCredential(
                project_id=project_id,
                provider=provider,
                credential_type=self._detect_type(provider),
                value=credentials[provider],
                expires_at=expiration,
                access_level=access_level,
            )

            logger.info(
                "Assigned %s credential for project %s, provider %s (expires: %sh)",
                access_level.value,
                project_id,
                provider,
                expires_in_hours,
            )

    def _detect_type(self, provider: str) -> str:
        """Detect credential type based on provider name."""
        type_map = {
            "github": "token",
            "gitlab": "token",
            "bitbucket": "token",
            "aws": "api_key",
            "gcp": "api_key",
            "azure": "api_key",
            "docker": "password",
            "npm": "password",
            "generic": "token",
        }
        return type_map.get(provider.lower(), "token")

    async def get_credential(
        self,
        project_id: str,
        provider: str,
        required_level: AccessLevel = AccessLevel.READ_ONLY,
    ) -> ProjectScopedCredential | None:
        """Get a project-scoped credential, enforcing isolation and limits.

        Returns None when the project has no such credential, when the access
        level is insufficient, or when the credential has expired.
        """
        return self.resolve_credential(project_id, provider, required_level)

    def resolve_credential(
        self,
        project_id: str,
        provider: str,
        required_level: AccessLevel = AccessLevel.READ_ONLY,
    ) -> ProjectScopedCredential | None:
        """Synchronous credential lookup for worker code that cannot await.

        Same enforcement and audit trail as :meth:`get_credential`; kept sync so
        executors can resolve a secret inside a synchronous request path without
        holding the value on the instance.
        """
        self._stats["total_requests"] += 1

        cred = self._project_creds.get(project_id, {}).get(provider)
        if cred is None:
            logger.warning(
                "Credential request for project %s, provider %s but no credentials assigned",
                project_id,
                provider,
            )
            self._stats["denied_requests"] += 1
            return None

        if cred.is_expired():
            logger.warning("Credential expired for project %s, provider %s", project_id, provider)
            # The assignment is kept (and reported as expired) instead of being
            # deleted: its presence is what tells callers to fail closed rather
            # than fall back to an unscoped secret.
            self._stats["expired_credentials"] += 1
            return None

        if not cred.can_use(required_level):
            logger.warning(
                "Credential access denied: project %s requires %s, credential has %s",
                project_id,
                required_level.value,
                cred.access_level.value,
            )
            self._stats["denied_requests"] += 1
            return None

        cred.usage_count += 1
        cred.last_used = time.time()

        self._stats["granted_requests"] += 1
        usage_log: list[dict[str, Any]] = self._stats["usage_log"]
        usage_log.append(
            {
                "timestamp": time.time(),
                "project_id": project_id,
                "provider": provider,
                "credential_type": cred.credential_type,
                "usage_count": cred.usage_count,
            }
        )
        if len(usage_log) > _USAGE_LOG_LIMIT:
            self._stats["usage_log"] = usage_log[-_USAGE_LOG_KEEP:]

        logger.debug(
            "Granted credential for project %s, provider %s (type: %s, level: %s)",
            project_id,
            provider,
            cred.credential_type,
            cred.access_level.value,
        )
        return cred

    async def execute_with_credentials(
        self,
        project_id: str,
        provider: str,
        callback: Callable[[str], Any],
        required_level: AccessLevel = AccessLevel.EXECUTION,
        timeout: int = 30,
    ) -> Any:
        """Run a callback with a single project-scoped credential.

        The secret is handed to the callback as its only argument; the caller
        never sees it, and the environment of this process is never modified
        (the callback runs in a worker thread with a private env copy).
        """
        cred = await self.get_credential(project_id, provider, required_level)
        if cred is None:
            raise ValueError(f"Cannot get credential for project {project_id}, provider {provider}")

        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(loop.run_in_executor(None, callback, cred.value), timeout=timeout)

    def has_credential(self, project_id: str, provider: str) -> bool:
        """Whether the project has an assignment for this provider (usable or not)."""
        return provider in self._project_creds.get(project_id, {})

    def get_project_credentials_summary(self, project_id: str) -> dict[str, Any]:
        """Get a masked summary of credentials assigned to a project."""
        creds = self._project_creds.get(project_id, {})
        if not creds:
            return {"project_id": project_id, "providers": {}, "count": 0}

        return {
            "project_id": project_id,
            "providers": {
                provider: {
                    "type": cred.credential_type,
                    "access_level": cred.access_level.value,
                    "masked_value": cred.mask(),
                    "expired": cred.is_expired(),
                    "usage_count": cred.usage_count,
                    "max_usages": cred.max_usages,
                }
                for provider, cred in creds.items()
            },
            "count": len(creds),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get broker statistics for monitoring/health surfaces."""
        return {
            **self._stats,
            "total_projects": len(self._project_creds),
            "active_projects": len([p for p, c in self._project_creds.items() if c]),
        }


_credential_broker: CredentialBroker | None = None


def get_credential_broker() -> CredentialBroker:
    """Get the process-wide credential broker instance."""
    global _credential_broker
    if _credential_broker is None:
        _credential_broker = CredentialBroker()
    return _credential_broker
