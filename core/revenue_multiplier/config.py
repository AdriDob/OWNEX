from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class ExecutionMode(StrEnum):
    DRY_RUN = "dry_run"
    PAPER = "paper"
    LIVE = "live"


class CapitalAllocation(BaseModel):
    bug_bounty_pct: float = 0.30
    crypto_trading_pct: float = 0.40
    defi_yield_pct: float = 0.20
    arbitrage_pct: float = 0.10
    emergency_reserve_pct: float = 0.05
    max_drawdown_pct: float = 0.15
    risk_per_trade_pct: float = 0.02

    @property
    def allocated(self) -> float:
        return self.bug_bounty_pct + self.crypto_trading_pct + self.defi_yield_pct + self.arbitrage_pct


class RevenueMultiplierConfig(BaseModel):
    mode: ExecutionMode = ExecutionMode.DRY_RUN
    max_concurrent_tools: int = 4
    max_concurrent_trades: int = 2
    min_confidence_for_report: float = 0.65
    auto_report_enabled: bool = True
    auto_trade_enabled: bool = False
    capital_allocation: CapitalAllocation = Field(default_factory=CapitalAllocation)
    data_dir: str = str(Path.home() / ".orion" / "revenue_multiplier")
    event_bus_enabled: bool = True
    knowledge_graph_enabled: bool = True
    max_daily_bounty_targets: int = 20
    cooldown_hours_between_scans: int = 6
    trading_pair_whitelist: list[str] = Field(default_factory=lambda: ["SOL/USDC", "BONK/USDC", "WIF/USDC"])
    slippage_bps: int = 100
    min_position_usd: float = 10.0
    max_position_usd: float = 500.0
    jupiter_api_url: str = "https://quote-api.jup.ag/v6"
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    katana_binary: str = "katana"
    nuclei_binary: str = "nuclei"
    ffuf_binary: str = "ffuf"
    subfinder_binary: str = "subfinder"
    naabu_binary: str = "naabu"
    httpx_binary: str = "httpx"
