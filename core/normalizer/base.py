from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ── Standard Normalized Types ────────────────────────────────────


@dataclass
class NormalizedPosition:
    """A single asset position in a portfolio."""

    symbol: str
    name: str = ""
    asset_type: str = ""           # stock, crypto, etf, bond, cash
    quantity: float = 0.0
    avg_price: float = 0.0
    current_price: float = 0.0
    value: float = 0.0
    currency: str = "USD"
    pnl_percent: float = 0.0
    exchange: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedPortfolio:
    """Snapshot of an entire portfolio."""

    total_value: float = 0.0
    cash: float = 0.0
    positions: list[NormalizedPosition] = field(default_factory=list)
    currency: str = "USD"
    provider: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedTransaction:
    """A single trade or transfer."""

    tx_id: str = ""
    symbol: str = ""
    tx_type: str = ""              # buy, sell, deposit, withdrawal
    quantity: float = 0.0
    price: float = 0.0
    fees: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    executed_at: str = ""
    platform: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedMarket:
    """A betting/prediction market."""

    market_id: str = ""
    title: str = ""
    platform: str = ""             # polymarket, betfair, pinnacle
    outcomes: list[dict] = field(default_factory=list)  # [{name, price, volume}]
    volume_24h: float = 0.0
    close_time: str = ""
    url: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedBet:
    """A single bet record."""

    bet_id: str = ""
    event: str = ""
    market: str = ""
    platform: str = ""
    odds: float = 0.0
    stake: float = 0.0
    outcome: str = "pending"       # win, loss, push, pending
    payout: float = 0.0
    ev: float = 0.0
    roi: float = 0.0
    placed_at: str = ""
    settled_at: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedPrice:
    """A single price quote."""

    symbol: str = ""
    price: float = 0.0
    currency: str = "USD"
    change_24h: float | None = None
    volume_24h: float | None = None
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    extra: dict[str, Any] = field(default_factory=dict)


# ── Abstract Normalizer ──────────────────────────────────────────


class BaseNormalizer(ABC):
    """Transforms raw connector data into standard normalized types."""

    @abstractmethod
    def normalize_portfolio(self, raw: Any) -> NormalizedPortfolio:
        ...

    @abstractmethod
    def normalize_transactions(self, raw: list[Any]) -> list[NormalizedTransaction]:
        ...

    @abstractmethod
    def normalize_prices(self, raw: dict[str, Any]) -> list[NormalizedPrice]:
        ...

    @abstractmethod
    def normalize_markets(self, raw: list[Any]) -> list[NormalizedMarket]:
        ...

    @abstractmethod
    def normalize_bets(self, raw: list[Any]) -> list[NormalizedBet]:
        ...
