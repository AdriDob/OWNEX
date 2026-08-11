from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, field_validator


class TradingMode(StrEnum):
    REAL = "real"
    DRY_RUN = "dry_run"
    PAPER_TRADING = "paper_trading"


class TradingConfig(BaseModel):
    mode: TradingMode = TradingMode.DRY_RUN

    pair: str = "SOL/USDC"
    quote_currency: str = "USDC"

    paper_initial_balance_usdc: float = 1_000.0
    paper_initial_balance_sol: float = 5.0
    paper_fee_pct: float = 0.003
    paper_slippage_pct: float = 0.005
    paper_latency_ms: int = 200
    paper_wallet_path: str = str(Path.home() / ".orion" / "paper_wallet.json")

    dry_run_log_actions: bool = True
    dry_run_show_pnl: bool = True

    default_slippage_pct: float = 0.01
    default_fee_pct: float = 0.003

    max_slippage_pct: float = 0.05
    max_position_size_usd: float = 500.0
    min_position_size_usd: float = 5.0

    rpc_url: str = "https://api.mainnet-beta.solana.com"
    helius_api_key: str = ""
    jupiter_api_url: str = "https://quote-api.jup.ag/v6"

    exchange_api_key: str = ""
    exchange_secret: str = ""

    @field_validator("paper_fee_pct", "paper_slippage_pct", "default_slippage_pct")
    @classmethod
    def validate_percentage(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"Percentage must be between 0 and 1, got {v}")
        return v

    @field_validator("max_position_size_usd", "min_position_size_usd")
    @classmethod
    def validate_position_size(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"Position size must be positive, got {v}")
        return v

    @classmethod
    def from_env(cls) -> TradingConfig:
        return cls(
            mode=TradingMode(os.getenv("TRADING_MODE", "dry_run")),
            rpc_url=os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
            helius_api_key=os.getenv("HELIUS_API_KEY", ""),
            jupiter_api_url=os.getenv("JUPITER_API_URL", "https://quote-api.jup.ag/v6"),
            exchange_api_key=os.getenv("EXCHANGE_API_KEY", ""),
            exchange_secret=os.getenv("EXCHANGE_SECRET", ""),
            paper_initial_balance_usdc=float(os.getenv("PAPER_BALANCE_USDC", "1000")),
            paper_initial_balance_sol=float(os.getenv("PAPER_BALANCE_SOL", "5")),
        )

    @property
    def is_live(self) -> bool:
        return self.mode == TradingMode.REAL

    @property
    def is_simulation(self) -> bool:
        return self.mode in (TradingMode.DRY_RUN, TradingMode.PAPER_TRADING)

    @property
    def mode_label(self) -> str:
        labels: dict[TradingMode, str] = {
            TradingMode.REAL: "LIVE",
            TradingMode.DRY_RUN: "DRY RUN",
            TradingMode.PAPER_TRADING: "PAPER",
        }
        return labels[self.mode]
