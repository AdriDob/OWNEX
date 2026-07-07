"""Base classes and event definitions for the AuthHub module."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class OAuth2Provider(ABC):
    """Abstract base for OAuth2-based integrations."""

    @abstractmethod
    def authorize_url(self) -> str:
        """Return the URL the user must visit to authorize."""

    @abstractmethod
    def exchange_code(self, code: str, state: str = "") -> dict[str, Any]:
        """Exchange an authorization code for tokens."""

    @abstractmethod
    def refresh_token(self) -> dict[str, Any] | None:
        """Refresh the access token using the stored refresh token."""

    @abstractmethod
    def revoke(self) -> bool:
        """Revoke the current token pair."""

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Return True if a valid access token is available."""


class MessagingProvider(ABC):
    """Abstract base for messaging platform integrations."""

    @abstractmethod
    def send_message(self, to: str, content: str) -> bool:
        """Send a message to the given recipient."""


class AuthHubEvent(Enum):
    GMAIL_AUTHENTICATED = "authhub:gmail_authenticated"
    GMAIL_REVOKED = "authhub:gmail_revoked"
    WHATSAPP_CONNECTED = "authhub:whatsapp_connected"
    TELEGRAM_CONNECTED = "authhub:telegram_connected"
    TOKEN_REFRESHED = "authhub:token_refreshed"
    TOKEN_EXPIRED = "authhub:token_expired"
