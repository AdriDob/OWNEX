"""Gmail notification adapter — Gmail API con OAuth2."""

from __future__ import annotations

import base64
import logging
from email.mime.text import MIMEText
from typing import Any

import httpx

from cores.env.config import get_config

logger = logging.getLogger("cateye.notifications.gmail")

GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GmailAdapter:
    def __init__(self) -> None:
        cfg = get_config()
        self._client_id = cfg.gmail_client_id
        self._client_secret = cfg.gmail_client_secret
        self._refresh_token = cfg.gmail_refresh_token
        self._from_email = cfg.gmail_from
        self._enabled = bool(
            self._client_id and self._client_secret and self._refresh_token and self._from_email
        )

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def _refresh_access_token(self) -> str | None:
        """Obtiene un access token usando el refresh token."""
        try:
            with httpx.Client() as client:
                resp = client.post(
                    OAUTH_TOKEN_URL,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "refresh_token": self._refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=15,
                )
                if resp.is_success:
                    return resp.json().get("access_token")
                logger.warning("Gmail token refresh failed: %s", resp.text)
                return None
        except Exception as exc:
            logger.warning("Gmail token refresh error: %s", exc)
            return None

    def send(self, title: str, message: str, priority: str = "medium", metadata: dict[str, Any] | None = None) -> bool:
        if not self._enabled:
            logger.debug("Gmail disabled — set CATEYE_GMAIL_* env vars")
            return False

        access_token = self._refresh_access_token()
        if not access_token:
            return False

        html = f"""<html><body style="font-family:sans-serif;padding:20px">
<h2 style="color:#7c3aed;">{title}</h2>
<p>{message}</p>
<hr><p style="color:#999;font-size:11px;">CATEYE Notificacion · Prioridad: {priority}</p>
</body></html>"""

        msg = MIMEText(html, "html")
        msg["Subject"] = f"[CATEYE] {title}"
        msg["From"] = self._from_email
        msg["To"] = self._from_email

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {"raw": raw}

        try:
            with httpx.Client() as client:
                resp = client.post(GMAIL_SEND_URL, json=payload, headers=headers, timeout=15)
                if resp.is_success:
                    logger.info("Gmail sent: %s -> %s", title, self._from_email)
                    return True
                logger.warning("Gmail send failed: %s — %s", resp.status_code, resp.text)
                return False
        except Exception as exc:
            logger.warning("Gmail request error: %s", exc)
            return False


_GMAIL: GmailAdapter | None = None


def get_gmail_adapter() -> GmailAdapter:
    global _GMAIL
    if _GMAIL is None:
        _GMAIL = GmailAdapter()
    return _GMAIL
