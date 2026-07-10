"""Connector Interface — one per external platform.

Connectors wrap external APIs (exchange, bot REST API, scraper).
They NEVER import the external project's code — only call its API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ConnectorHealth:
    connected: bool
    latency_ms: float | None = None
    error: str | None = None
    rate_limit_remaining: int | None = None


class IConnector(ABC):
    """Interface for a single external platform connector.

    Each connector is a self-contained directory under ``connectors/<platform>/``.
    """

    connector_id: str
    app_id: str
    display_name: str = ""

    @abstractmethod
    async def connect(self) -> bool:
        """Initialize connection (API handshake, auth)."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection gracefully."""

    @abstractmethod
    async def health(self) -> ConnectorHealth:
        """Check if the connector is reachable."""

    @abstractmethod
    def get_config_fields(self) -> list[dict]:
        """Return config fields for the UI (key, secret, endpoint, etc.).

        Each field: {"key": str, "label": str, "type": "password"|"text"|"number"}
        """
