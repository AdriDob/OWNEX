"""Target authentication management — identities, credentials, sessions.

Phased replacement for the weak XOR-based identity_vault.
Uses AES-256-GCM for all credential encryption at rest.
"""

from cores.target_auth.identity_manager import TargetIdentityManager
from cores.target_auth.login_service import TargetLoginService
from cores.target_auth.session_manager import TargetSessionManager
from cores.target_auth.session_resolver import SessionResolver
from cores.target_auth.vault import CredentialVault

__all__ = [
    "CredentialVault",
    "TargetIdentityManager",
    "TargetLoginService",
    "TargetSessionManager",
    "SessionResolver",
]
