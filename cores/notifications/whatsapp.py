"""WhatsApp notification adapter — Twilio API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from cores.env.config import get_config

logger = logging.getLogger("catseye.notifications.whatsapp")

TWILIO_API_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class WhatsAppAdapter:
    def __init__(self) -> None:
        cfg = get_config()
        self._account_sid = cfg.twilio_account_sid
        self._auth_token = cfg.twilio_auth_token
        self._from_number = cfg.twilio_whatsapp_from
        self._to_number = cfg.notification_whatsapp_to
        self._enabled = bool(self._account_sid and self._auth_token and self._from_number and self._to_number)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def send(self, title: str, message: str, priority: str = "medium", metadata: dict[str, Any] | None = None) -> bool:
        if not self._enabled:
            logger.debug("WhatsApp disabled — set CATEYE_TWILIO_* and CATEYE_NOTIFICATION_WHATSAPP_TO")
            return False

        body = f"[CATEYE] {title}\n\n{message}\n\nPrioridad: {priority}"

        url = TWILIO_API_URL.format(sid=self._account_sid)
        auth = (self._account_sid, self._auth_token)
        data = {
            "From": f"whatsapp:{self._from_number}",
            "To": f"whatsapp:{self._to_number}",
            "Body": body[:1600],
        }

        try:
            with httpx.Client() as client:
                resp = client.post(url, auth=auth, data=data, timeout=15)
                if resp.is_success:
                    logger.info("WhatsApp sent: %s -> %s", title, self._to_number)
                    return True
                logger.warning("WhatsApp send failed: %s — %s", resp.status_code, resp.text)
                return False
        except Exception as exc:
            logger.warning("WhatsApp request error: %s", exc)
            return False


_WHATSAPP: WhatsAppAdapter | None = None


def get_whatsapp_adapter() -> WhatsAppAdapter:
    global _WHATSAPP
    if _WHATSAPP is None:
        _WHATSAPP = WhatsAppAdapter()
    return _WHATSAPP
