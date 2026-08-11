"""DeFi positions — data models for protocol positions, yields, and snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ProtocolInfo:
    """Metadata for a DeFi protocol."""

    name: str
    slug: str
    chain: str
    category: str  # lending, dex, staking, yield, bridge, etc.
    url: str = ""
    tvl: float = 0.0


@dataclass
class DefiPosition:
    """A single position in a DeFi protocol."""

    protocol: str
    chain: str
    asset: str
    amount: float
    usd_value: float
    apy: float
    category: str = "yield"
    pool_name: str = ""
    tokens: list[str] = field(default_factory=list)
    link: str = ""
    notes: str = ""

    @property
    def monthly_yield(self) -> float:
        return self.usd_value * (self.apy / 100 / 12)

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "chain": self.chain,
            "asset": self.asset,
            "amount": self.amount,
            "usd_value": self.usd_value,
            "apy": self.apy,
            "category": self.category,
            "pool_name": self.pool_name,
            "tokens": self.tokens,
            "monthly_yield": round(self.monthly_yield, 2),
            "link": self.link,
            "notes": self.notes,
        }


@dataclass
class YieldSnapshot:
    """Snapshot of all DeFi positions at a point in time."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    positions: list[DefiPosition] = field(default_factory=list)

    @property
    def total_value(self) -> float:
        return sum(p.usd_value for p in self.positions)

    @property
    def total_monthly_yield(self) -> float:
        return sum(p.monthly_yield for p in self.positions)

    @property
    def weighted_apy(self) -> float:
        if not self.positions or self.total_value == 0:
            return 0.0
        return sum(p.apy * p.usd_value for p in self.positions) / self.total_value

    @property
    def position_count(self) -> int:
        return len(self.positions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_value": round(self.total_value, 2),
            "total_monthly_yield": round(self.total_monthly_yield, 2),
            "total_annual_yield": round(self.total_monthly_yield * 12, 2),
            "weighted_apy": round(self.weighted_apy, 2),
            "position_count": len(self.positions),
            "positions": [p.to_dict() for p in self.positions],
        }


# ── Known high-yield protocols (reference data) ──────────────

REFERENCE_PROTOCOLS: dict[str, ProtocolInfo] = {
    "aave_v3_usdc": ProtocolInfo(
        name="AAVE V3",
        slug="aave-v3",
        chain="ethereum",
        category="lending",
        url="https://app.aave.com",
        tvl=0.0,
    ),
    "compound_usdc": ProtocolInfo(
        name="Compound",
        slug="compound",
        chain="ethereum",
        category="lending",
        url="https://app.compound.finance",
        tvl=0.0,
    ),
    "morpho_usdc": ProtocolInfo(
        name="Morpho Blue",
        slug="morpho-blue",
        chain="ethereum",
        category="lending",
        url="https://app.morpho.org",
        tvl=0.0,
    ),
    "lido_steth": ProtocolInfo(
        name="Lido",
        slug="lido",
        chain="ethereum",
        category="staking",
        url="https://stake.lido.fi",
        tvl=0.0,
    ),
    "rocket_pool_reth": ProtocolInfo(
        name="Rocket Pool",
        slug="rocket-pool",
        chain="ethereum",
        category="staking",
        url="https://rocketpool.net",
        tvl=0.0,
    ),
    "uniswap_v3_usdc_eth": ProtocolInfo(
        name="Uniswap V3",
        slug="uniswap-v3",
        chain="ethereum",
        category="dex",
        url="https://app.uniswap.org",
        tvl=0.0,
    ),
    "marinade_msol": ProtocolInfo(
        name="Marinade",
        slug="marinade",
        chain="solana",
        category="staking",
        url="https://marinade.finance",
        tvl=0.0,
    ),
    "jito_jitosol": ProtocolInfo(
        name="Jito",
        slug="jito",
        chain="solana",
        category="staking",
        url="https://jito.network",
        tvl=0.0,
    ),
    "binance_earn": ProtocolInfo(
        name="Binance Earn",
        slug="binance-earn",
        chain="binance",
        category="yield",
        url="https://www.binance.com/en/earn",
        tvl=0.0,
    ),
    "coinbase_staking": ProtocolInfo(
        name="Coinbase Staking",
        slug="coinbase-staking",
        chain="ethereum",
        category="staking",
        url="https://www.coinbase.com/staking",
        tvl=0.0,
    ),
}


# ── 5 high-yield protocols from the tweet strategy ──────────

HIGH_YIELD_PROTOCOLS = [
    "aave_v3_usdc",
    "morpho_usdc",
    "lido_steth",
    "compound_usdc",
    "binance_earn",
]
