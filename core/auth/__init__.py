from __future__ import annotations

from core.auth.credentials import CredentialStore
from core.auth.injector import apply_auth_to_request_kwargs, create_auth_for_provider, inject_into_client
from core.auth.manager import AuthManager, AuthTarget, get_auth_manager
from core.auth.provider import (
    APIKeyHeaderProvider,
    APIKeyQueryProvider,
    AuthConfig,
    AuthProvider,
    AuthType,
    BasicAuthProvider,
    BearerTokenProvider,
    CookieProvider,
    JWTProvider,
    get_provider,
    list_providers,
)

__all__ = [
    "APIKeyHeaderProvider",
    "APIKeyQueryProvider",
    "AuthConfig",
    "AuthManager",
    "AuthProvider",
    "AuthTarget",
    "AuthType",
    "BearerTokenProvider",
    "BasicAuthProvider",
    "CookieProvider",
    "CredentialStore",
    "JWTProvider",
    "apply_auth_to_request_kwargs",
    "create_auth_for_provider",
    "get_auth_manager",
    "get_provider",
    "inject_into_client",
    "list_providers",
]
