"""AuthHub — central registry for OAuth2 and messaging providers."""

from __future__ import annotations

import logging
from typing import Any

from cores.authhub.base import AuthHubEvent, MessagingProvider, OAuth2Provider
from cores.events.event_bus import EVENT_PRIORITY_MAP, get_event_bus
from cores.identity_vault import get_identity_vault

logger = logging.getLogger("ownex.authhub.hub")

AUTHHUB_EVENT_PRIORITIES: dict[str, str] = {
    AuthHubEvent.GMAIL_AUTHENTICATED.value: "high",
    AuthHubEvent.GMAIL_REVOKED.value: "medium",
    AuthHubEvent.WHATSAPP_CONNECTED.value: "medium",
    AuthHubEvent.TELEGRAM_CONNECTED.value: "medium",
    AuthHubEvent.TOKEN_REFRESHED.value: "low",
    AuthHubEvent.TOKEN_EXPIRED.value: "high",
}

EVENT_PRIORITY_MAP.update(AUTHHUB_EVENT_PRIORITIES)


class AuthHub:
    def __init__(self) -> None:
        self._providers: dict[str, OAuth2Provider | MessagingProvider] = {}

    def register_provider(self, name: str, provider: OAuth2Provider | MessagingProvider) -> None:
        self._providers[name] = provider
        logger.info("Provider registered: %s (%s)", name, type(provider).__name__)

    def get_provider(self, name: str) -> OAuth2Provider | MessagingProvider | None:
        return self._providers.get(name)

    def get_all_providers(self) -> dict[str, OAuth2Provider | MessagingProvider]:
        return dict(self._providers)

    def send_notification(self, channel: str, to: str, content: str) -> bool:
        provider = self._providers.get(channel)
        if provider is None:
            logger.warning("No provider registered for channel: %s", channel)
            return False
        if not isinstance(provider, MessagingProvider):
            logger.warning("Provider %s is not a MessagingProvider", channel)
            return False
        return provider.send_message(to, content)

    def _publish_event(self, event: AuthHubEvent, **payload: Any) -> None:
        bus = get_event_bus()
        bus.publish(event.value, **payload)

    def init_defaults(self) -> None:
        vault = get_identity_vault()

        # Gmail
        gmail_creds = vault.get_credentials("gmail")
        if gmail_creds.get("client_id") and gmail_creds.get("client_secret"):
            from cores.authhub.gmail import GmailOAuth2
            gmail = GmailOAuth2()
            self.register_provider("gmail", gmail)
            logger.info("AuthHub: GmailOAuth2 auto-registered")

        # Twilio / WhatsApp
        twilio_creds = vault.get_credentials("twilio")
        if twilio_creds.get("account_sid", twilio_creds.get("token")) and \
           twilio_creds.get("auth_token", twilio_creds.get("password")):
            from cores.authhub.whatsapp import WhatsAppTwilio
            whatsapp = WhatsAppTwilio()
            self.register_provider("whatsapp", whatsapp)
            logger.info("AuthHub: WhatsAppTwilio auto-registered")

        # Telegram
        telegram_creds = vault.get_credentials("telegram")
        if telegram_creds.get("bot_token", telegram_creds.get("token")):
            from cores.authhub.telegram import TelegramBot
            telegram = TelegramBot()
            self.register_provider("telegram", telegram)
            logger.info("AuthHub: TelegramBot auto-registered")


_HUB: AuthHub | None = None


def get_authhub() -> AuthHub:
    global _HUB
    if _HUB is None:
        _HUB = AuthHub()
        logger.info("AuthHub initialized")
    return _HUB
