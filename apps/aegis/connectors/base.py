"""Base connector for AEGIS — extends IConnector for security tools."""

from __future__ import annotations

from abc import abstractmethod

from core.interfaces.connector import IConnector


class AegisConnector(IConnector):
    """Base class for AEGIS tool connectors."""

    app_id: str = "aegis"

    @abstractmethod
    async def scan(self, target: str) -> list[dict]:
        """Run the tool against a target and return findings."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the tool binary is installed."""
