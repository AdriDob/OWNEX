"""Telegram Bot API integration — credentials stored in identity_vault."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from cores.authhub.base import MessagingProvider
from cores.identity_vault import get_identity_vault

logger = logging.getLogger("catseye.authhub.telegram")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"
PROVIDER_NAME = "telegram"


class TelegramBot(MessagingProvider):
    def __init__(self) -> None:
        self._bot_token: str = ""
        self._chat_id: str = ""
        self._load_credentials()

    def _load_credentials(self) -> None:
        vault = get_identity_vault()
        creds = vault.get_credentials(PROVIDER_NAME)
        self._bot_token = creds.get("bot_token", creds.get("token", ""))
        self._chat_id = creds.get("chat_id", "")

    @property
    def is_configured(self) -> bool:
        return bool(self._bot_token)

    def send_message(self, to: str = "", content: str = "") -> bool:
        if not self.is_configured:
            logger.warning("Telegram not configured — missing bot_token")
            return False

        target_chat = to or self._chat_id
        if not target_chat:
            logger.warning("Telegram send_message requires a chat_id (to= argument or stored chat_id)")
            return False

        url = TELEGRAM_API_URL.format(token=self._bot_token, method="sendMessage")
        data = {"chat_id": target_chat, "text": content, "parse_mode": "HTML"}
        body = urllib.parse.urlencode(data).encode()

        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if result.get("ok"):
                    logger.info("Telegram message sent to %s", target_chat)
                    return True
                logger.warning("Telegram send failed: %s", result.get("description", "unknown"))
                return False
        except urllib.error.URLError as exc:
            logger.warning("Telegram request error: %s", exc)
            return False

    def set_webhook(self, url: str) -> bool:
        if not self.is_configured:
            return False

        webhook_url = TELEGRAM_API_URL.format(token=self._bot_token, method="setWebhook")
        data = {"url": url}
        body = urllib.parse.urlencode(data).encode()

        req = urllib.request.Request(webhook_url, data=body)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if result.get("ok"):
                    logger.info("Telegram webhook set to %s", url)
                    return True
                logger.warning("Telegram set_webhook failed: %s", result.get("description", ""))
                return False
        except urllib.error.URLError as exc:
            logger.warning("Telegram webhook request error: %s", exc)
            return False
