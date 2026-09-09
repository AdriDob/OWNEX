from __future__ import annotations

from typing import Any

from core.auth.provider import AuthConfig, AuthType, get_provider


def create_auth_for_provider(config: AuthConfig) -> dict[str, Any]:
    provider = get_provider(config.auth_type)
    if not provider:
        return {}

    result: dict[str, Any] = {
        "headers": provider.get_headers(config),
        "query_params": provider.get_query_params(config),
        "cookies": provider.get_cookies(config),
        "auth": None,
    }

    if config.auth_type == AuthType.BASIC_AUTH:
        import httpx

        result["auth"] = httpx.BasicAuth(
            username=config.params.get("username", ""),
            password=config.params.get("password", ""),
        )

    return result


def inject_into_client(client: Any, config: AuthConfig) -> Any:
    auth_data = create_auth_for_provider(config)
    headers = auth_data.get("headers", {})
    if headers:
        client.headers.update(headers)

    auth = auth_data.get("auth")
    if auth is not None and hasattr(client, "auth"):
        client.auth = auth

    return client


def apply_auth_to_request_kwargs(kwargs: dict[str, Any], config: AuthConfig) -> dict[str, Any]:
    auth_data = create_auth_for_provider(config)

    headers = kwargs.get("headers", {}) or {}
    headers.update(auth_data.get("headers", {}))
    kwargs["headers"] = headers

    params = kwargs.get("params", {}) or {}
    params.update(auth_data.get("query_params", {}))
    kwargs["params"] = params

    if auth_data.get("auth") is not None:
        kwargs["auth"] = auth_data["auth"]

    return kwargs
