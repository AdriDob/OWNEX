"""Gmail OAuth2 integration — credentials stored in identity_vault."""

from __future__ import annotations

import json
import logging
import secrets
import urllib.parse
import urllib.request
from typing import Any

from cores.authhub.base import OAuth2Provider
from cores.identity_vault import get_identity_vault

logger = logging.getLogger("cateye.authhub.gmail")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
PROVIDER_NAME = "gmail"


class GmailOAuth2(OAuth2Provider):
    def __init__(self) -> None:
        self._client_id: str = ""
        self._client_secret: str = ""
        self._redirect_uri: str = ""
        self._oauth_state: str = ""
        self._load_credentials()

    def _load_credentials(self) -> None:
        vault = get_identity_vault()
        creds = vault.get_credentials(PROVIDER_NAME)
        self._client_id = creds.get("client_id", "")
        self._client_secret = creds.get("client_secret", "")
        self._redirect_uri = creds.get("redirect_uri", "")
        self._access_token = creds.get("token", "")
        self._refresh_token_val = creds.get("refresh_token", "")

    def _save_tokens(self, tokens: dict[str, Any]) -> None:
        vault = get_identity_vault()
        metadata = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "refresh_token": tokens.get("refresh_token", self._refresh_token_val),
        }
        vault.store_credentials(
            provider=PROVIDER_NAME,
            email=tokens.get("email", ""),
            token=tokens.get("access_token", ""),
            metadata=metadata,
        )
        self._access_token = tokens.get("access_token", self._access_token)
        self._refresh_token_val = tokens.get("refresh_token", self._refresh_token_val)

    def authorize_url(self) -> str:
        self._oauth_state = secrets.token_urlsafe(32)
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": self._oauth_state,
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str, state: str = "") -> dict[str, Any]:
        if state and state != self._oauth_state:
            logger.warning("OAuth state mismatch — possible CSRF attack")
            return {}
        data = {
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(GOOGLE_TOKEN_URL, data=body)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                tokens = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            logger.warning("Gmail exchange_code failed: %s", exc)
            return {}

        if "access_token" in tokens:
            user = self._get_user_info(tokens.get("access_token", ""))
            tokens["email"] = user.get("email", "")
            self._save_tokens(tokens)

        return tokens

    def refresh_token(self) -> dict[str, Any] | None:
        if not self._refresh_token_val:
            logger.warning("No refresh token available for Gmail")
            return None

        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token_val,
            "grant_type": "refresh_token",
        }
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(GOOGLE_TOKEN_URL, data=body)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                tokens = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            logger.warning("Gmail refresh_token failed: %s", exc)
            return None

        if "access_token" in tokens:
            self._save_tokens(tokens)
            logger.info("Gmail token refreshed")

        return tokens

    def revoke(self) -> bool:
        if not self._access_token:
            return False
        params = urllib.parse.urlencode({"token": self._access_token})
        url = f"https://oauth2.googleapis.com/revoke?{params}"
        try:
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req, timeout=10):
                pass
        except urllib.error.URLError as exc:
            logger.warning("Gmail revoke failed: %s", exc)
            return False
        vault = get_identity_vault()
        vault.remove_credentials(PROVIDER_NAME)
        self._access_token = ""
        self._refresh_token_val = ""
        logger.info("Gmail credentials revoked")
        return True

    def is_authenticated(self) -> bool:
        if not self._access_token:
            return False
        try:
            user = self._get_user_info(self._access_token)
            return "email" in user
        except Exception:
            return False

    def get_user_info(self) -> dict[str, Any]:
        return self._get_user_info(self._access_token)

    def _get_user_info(self, access_token: str) -> dict[str, Any]:
        if not access_token:
            return {}
        req = urllib.request.Request(GOOGLE_USERINFO_URL)
        req.add_header("Authorization", f"Bearer {access_token}")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            logger.warning("Gmail userinfo failed: %s", exc)
            return {}
