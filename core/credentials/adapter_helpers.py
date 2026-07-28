"""Credentials integration helpers for opportunity adapters."""

from __future__ import annotations

from core.credentials.vault import get_platform_credentials


def load_credentials(platform: str, config: dict | None = None) -> dict:
    """Load credentials for a platform from vault, merging with config.

    Priority: config (explicit) > vault (env file) > defaults
    """
    vault_creds = get_platform_credentials(platform)
    merged = {**vault_creds}
    if config:
        merged.update(config)
    return merged


def get_api_key(platform: str, config: dict | None = None) -> str | None:
    """Get API key for platform from merged credentials."""
    creds = load_credentials(platform, config)
    for key in ("api_key", "api_token", "token", "key", "access_token"):
        if key in creds:
            return creds[key]
    return None


def get_oauth_credentials(platform: str, config: dict | None = None) -> dict:
    """Get OAuth client_id/client_secret for platform."""
    creds = load_credentials(platform, config)
    return {
        "client_id": creds.get("client_id") or creds.get("clientId"),
        "client_secret": creds.get("client_secret") or creds.get("clientSecret"),
        "redirect_uri": creds.get("redirect_uri") or creds.get("redirectUri"),
    }


def get_auth_headers(platform: str, config: dict | None = None) -> dict:
    """Generate Authorization headers for platform."""
    creds = load_credentials(platform, config)
    headers = {}

    api_key = get_api_key(platform, config)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        return headers

    if "access_token" in creds:
        headers["Authorization"] = f"Bearer {creds['access_token']}"
        return headers

    if "li_at_cookie" in creds:
        headers["Cookie"] = f"li_at={creds['li_at_cookie']}"
        return headers

    if "email" in creds and "password" in creds:
        return {}

    return headers
