"""Base connector for ATLAS — extends IConnector for investment platforms."""

from __future__ import annotations

from abc import abstractmethod

from core.interfaces.connector import IConnector
from core.normalizer.base import NormalizedPortfolio, NormalizedPrice, NormalizedTransaction


class AtlasConnector(IConnector):
    """Base class for ATLAS exchange/broker connectors."""

    app_id: str = "atlas"

    @abstractmethod
    async def get_portfolio(self) -> NormalizedPortfolio | None:
        """Full portfolio snapshot."""

    @abstractmethod
    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        """Recent transaction history."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        """Current price for a symbol."""

    @abstractmethod
    async def search_symbols(self, query: str) -> list[dict]:
        """Search for tradeable symbols."""
