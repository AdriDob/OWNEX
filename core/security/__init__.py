"""Security primitives for OWNEX.

Canonical location for security responsibilities (see
``docs/architecture/CANONICAL_COMPONENTS.md``):

- ``sanitization`` — prompt-injection filtering for externally sourced data
- ``sandbox`` — isolated execution of untrusted commands
- ``credential_broker`` — project-scoped credential isolation
"""

from core.security.credential_broker import (
    AccessLevel,
    CredentialBroker,
    ProjectScopedCredential,
    get_credential_broker,
)
from core.security.sandbox import Sandbox, SandboxConfig, SandboxResult

__all__ = [
    "AccessLevel",
    "CredentialBroker",
    "ProjectScopedCredential",
    "Sandbox",
    "SandboxConfig",
    "SandboxResult",
    "get_credential_broker",
]
