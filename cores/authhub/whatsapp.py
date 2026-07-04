"""WhatsApp Twilio integration — credentials stored in identity_vault."""

from __future__ import annotations

import base64
import json
import logging
import urllib.parse
import urllib.request
from typing import Any

from cores.authhub.base import MessagingProvider
from cores.identity_vault import get_identity_vault

logger = logging.getLogger("catseye.authhub.whatsapp")

TWILIO_API_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
PROVIDER_NAME = "twilio"


class WhatsAppTwilio(MessagingProvider):
    def __init__(self) -> None:
        self._account_sid: str = ""
        self._auth_token: str = ""
        self._from_number: str = ""
        self._load_credentials()

    def _load_credentials(self) -> None:
        vault = get_identity_vault()
        creds = vault.get_credentials(PROVIDER_NAME)
        self._account_sid = creds.get("account_sid", creds.get("token", ""))
        self._auth_token = creds.get("auth_token", creds.get("password", ""))
        self._from_number = creds.get("from_number", "")

    @property
    def is_configured(self) -> bool:
        return bool(self._account_sid and self._auth_token and self._from_number)

    def send_message(self, to: str, content: str) -> bool:
        if not self.is_configured:
            logger.warning("Twilio not configured — missing account_sid, auth_token, or from_number")
            return False

        url = TWILIO_API_URL.format(sid=self._account_sid)
        auth_bytes = f"{self._account_sid}:{self._auth_token}".encode()
        auth_header = base64.b64encode(auth_bytes).decode()

        data = {
            "From": f"whatsapp:{self._from_number}",
            "To": f"whatsapp:{to}",
            "Body": content[:1600],
        }
        body = urllib.parse.urlencode(data).encode()

        req = urllib.request.Request(url, data=body)
        req.add_header("Authorization", f"Basic {auth_header}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if result.get("sid"):
                    logger.info("WhatsApp message sent to %s (sid=%s)", to, result["sid"])
                    return True
                logger.warning("WhatsApp send failed: %s", result)
                return False
        except urllib.error.URLError as exc:
            logger.warning("WhatsApp request error: %s", exc)
            return False

    def on_message(self, callback: Any) -> None:
        """Placeholder for receiving incoming WhatsApp messages via webhook.
        Register a callable to handle incoming messages.
        """
        logger.debug("WhatsApp on_message callback registered (webhook setup required)")
