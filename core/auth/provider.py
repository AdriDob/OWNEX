from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ownex.auth.provider")


class AuthType(enum.StrEnum):
    BEARER_TOKEN = "bearer_token"
    JWT = "jwt"
    COOKIE = "cookie"
    BASIC_AUTH = "basic_auth"
    API_KEY_HEADER = "api_key_header"
    API_KEY_QUERY = "api_key_query"


@dataclass
class AuthConfig:
    auth_type: AuthType
    params: dict[str, Any] = field(default_factory=dict)
    label: str = ""
    target_id: int | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.auth_type == AuthType.BEARER_TOKEN:
            if "token" not in self.params:
                errors.append("BearerToken requires 'token' param")
        elif self.auth_type == AuthType.JWT:
            if "token" not in self.params and "refresh_token" not in self.params:
                errors.append("JWT requires 'token' or 'refresh_token' param")
        elif self.auth_type == AuthType.COOKIE:
            if "cookie" not in self.params:
                errors.append("Cookie requires 'cookie' param")
        elif self.auth_type == AuthType.BASIC_AUTH:
            if "username" not in self.params or "password" not in self.params:
                errors.append("BasicAuth requires 'username' and 'password' params")
        elif self.auth_type == AuthType.API_KEY_HEADER:
            if "key" not in self.params:
                errors.append("APIKeyHeader requires 'key' param")
            self.params.setdefault("header_name", "X-API-Key")
        elif self.auth_type == AuthType.API_KEY_QUERY and "key" not in self.params:
            errors.append("APIKeyQuery requires 'key' param")
        return errors


class AuthProvider:
    auth_type: AuthType

    def get_headers(self, config: AuthConfig) -> dict[str, str]:
        return {}

    def get_query_params(self, config: AuthConfig) -> dict[str, str]:
        return {}

    def get_cookies(self, config: AuthConfig) -> dict[str, str]:
        return {}

    def modify_request_body(self, config: AuthConfig, body: dict[str, Any] | None) -> dict[str, Any] | None:
        return body

    def supports(self, config: AuthConfig) -> bool:
        return config.auth_type == self.auth_type

    def test_connection(self, config: AuthConfig, url: str | None = None) -> bool:
        import httpx

        test_url = url or "https://httpbin.org/get"
        headers = self.get_headers(config)
        try:
            resp = httpx.get(test_url, headers=headers, timeout=10, verify=False)
            return resp.status_code < 500
        except Exception as e:
            logger.debug("Connection test failed for %s: %s", test_url, e)
            return False


class BearerTokenProvider(AuthProvider):
    auth_type = AuthType.BEARER_TOKEN

    def get_headers(self, config: AuthConfig) -> dict[str, str]:
        token = config.params.get("token", "")
        return {"Authorization": f"Bearer {token}"}


class JWTProvider(AuthProvider):
    auth_type = AuthType.JWT

    def get_headers(self, config: AuthConfig) -> dict[str, str]:
        token = config.params.get("token", "")
        return {"Authorization": f"Bearer {token}"}


class CookieProvider(AuthProvider):
    auth_type = AuthType.COOKIE

    def get_headers(self, config: AuthConfig) -> dict[str, str]:
        cookie = config.params.get("cookie", "")
        return {"Cookie": cookie}

    def get_cookies(self, config: AuthConfig) -> dict[str, str]:
        raw = config.params.get("cookie", "")
        pairs: dict[str, str] = {}
        for part in raw.split(";"):
            if "=" in part:
                k, _, v = part.partition("=")
                pairs[k.strip()] = v.strip()
        return pairs


class BasicAuthProvider(AuthProvider):
    auth_type = AuthType.BASIC_AUTH

    def get_headers(self, config: AuthConfig) -> dict[str, str]:
        import base64

        username = config.params.get("username", "")
        password = config.params.get("password", "")
        raw = f"{username}:{password}"
        encoded = base64.b64encode(raw.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}


class APIKeyHeaderProvider(AuthProvider):
    auth_type = AuthType.API_KEY_HEADER

    def get_headers(self, config: AuthConfig) -> dict[str, str]:
        header_name = config.params.get("header_name", "X-API-Key")
        key = config.params.get("key", "")
        return {header_name: key}


class APIKeyQueryProvider(AuthProvider):
    auth_type = AuthType.API_KEY_QUERY

    def get_query_params(self, config: AuthConfig) -> dict[str, str]:
        param_name = config.params.get("param_name", "api_key")
        key = config.params.get("key", "")
        return {param_name: key}


_PROVIDER_REGISTRY: dict[AuthType, AuthProvider] = {
    AuthType.BEARER_TOKEN: BearerTokenProvider(),
    AuthType.JWT: JWTProvider(),
    AuthType.COOKIE: CookieProvider(),
    AuthType.BASIC_AUTH: BasicAuthProvider(),
    AuthType.API_KEY_HEADER: APIKeyHeaderProvider(),
    AuthType.API_KEY_QUERY: APIKeyQueryProvider(),
}


def get_provider(auth_type: AuthType) -> AuthProvider | None:
    return _PROVIDER_REGISTRY.get(auth_type)


def list_providers() -> list[AuthType]:
    return list(_PROVIDER_REGISTRY.keys())
