"""Base connector for ODYSSEY — extends IConnector for betting platforms."""

from __future__ import annotations

from abc import abstractmethod

from core.interfaces.connector import IConnector
from core.normalizer.base import NormalizedBet, NormalizedMarket


class OdysseyConnector(IConnector):
    """Base class for ODYSSEY betting/prediction market connectors."""

    app_id: str = "odyssey"

    @abstractmethod
    async def get_bets(self, since_days: int = 30) -> list[NormalizedBet]:
        """Recent bets from this platform."""

    @abstractmethod
    async def get_markets(self, sport: str = "") -> list[NormalizedMarket]:
        """Available markets for analysis."""

    @abstractmethod
    async def get_balance(self) -> float:
        """Current account balance."""
