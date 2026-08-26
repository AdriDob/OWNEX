"""Configuration schema for Polymarket BTC Latency Arb."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeedConfig(BaseModel):
    """WebSocket feed configuration."""

    binance_ws_url: str = "wss://stream.binance.com:9443/ws"
    polymarket_ws_url: str = "wss://clob.polymarket.com/ws"
    symbol: str = "BTCUSDT"
    market_id: str = ""  # Auto-detect if empty


class StrategyConfig(BaseModel):
    """Strategy detection parameters."""

    btc_move_threshold_usd: float = Field(default=70.0, ge=0)
    min_seconds_left: int = Field(default=120, ge=0)
    max_position_usd: float = Field(default=10.0, gt=0)
    check_interval_ms: int = Field(default=100, ge=50)


class PaperTradingConfig(BaseModel):
    """Paper trading simulation parameters."""

    initial_usd: float = Field(default=100.0, gt=0)
    slippage_bps: int = Field(default=50, ge=0, le=500)  # 0.5% default
    fee_bps: int = Field(default=200, ge=0, le=500)  # 2% Polymarket fee
    min_order_usd: float = Field(default=1.0, gt=0)
    max_slippage_pct: float = Field(default=0.02, gt=0, le=0.1)
    fill_latency_ms_min: int = Field(default=50, ge=0)
    fill_latency_ms_max: int = Field(default=200, ge=0)
    partial_fill_probability: float = Field(default=0.1, ge=0, le=1)
    price_impact_bps_per_1k: int = Field(default=10, ge=0)  # Price impact per $1k


class RiskConfig(BaseModel):
    """Risk management limits."""

    max_daily_loss_usd: float = Field(default=20.0, gt=0)
    max_position_pct: float = Field(default=0.10, gt=0, le=1.0)  # 10% of capital
    max_concurrent_positions: int = Field(default=1, ge=1, le=5)
    cooldown_seconds: int = Field(default=30, ge=0)
    max_consecutive_losses: int = Field(default=5, ge=1)
    drawdown_pause_pct: float = Field(default=0.15, gt=0, le=0.5)  # 15% drawdown pauses
    kill_switch_enabled: bool = True


class SizingConfig(BaseModel):
    """Position sizing configuration."""

    method: str = Field(default="kelly")  # "kelly", "fixed_fractional", "fixed_usd"
    kelly_fraction: float = Field(default=0.25, gt=0, le=1.0)  # 25% Kelly
    fixed_fraction_pct: float = Field(default=0.02, gt=0, le=0.1)  # 2% per trade
    fixed_usd: float = Field(default=5.0, gt=0)
    min_win_rate_for_kelly: float = Field(default=0.51, gt=0.5, lt=1.0)


class LiveTradingConfig(BaseModel):
    """Live trading configuration (disabled by default)."""

    enable_live: bool = False
    polymarket_api_key: str = ""
    polymarket_secret: str = ""
    polymarket_passphrase: str = ""
    wallet_address: str = ""
    private_key_path: str = ""  # Path to encrypted key in IdentityVault


class PersistenceConfig(BaseModel):
    """Persistence configuration."""

    data_dir: str = "~/.orion/polymarket/btc_latency_arb"
    trades_file: str = "trades.jsonl"
    state_file: str = "state.json"
    max_trades_in_memory: int = 10000


class BTCArbConfig(BaseSettings):
    """Main configuration for BTC Latency Arbitrage bot."""

    model_config = SettingsConfigDict(
        env_prefix="BTC_ARB_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Sub-configs
    feeds: FeedConfig = Field(default_factory=FeedConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    paper: PaperTradingConfig = Field(default_factory=PaperTradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    sizing: SizingConfig = Field(default_factory=SizingConfig)
    live: LiveTradingConfig = Field(default_factory=LiveTradingConfig)
    persistence: PersistenceConfig = Field(default_factory=PersistenceConfig)

    # Runtime
    log_level: str = "INFO"
    dry_run: bool = True  # Paper trading by default

    @field_validator("live", mode="before")
    @classmethod
    def _validate_live(cls, v: Any) -> LiveTradingConfig:
        if isinstance(v, dict):
            return LiveTradingConfig(**v)
        return v

    @property
    def data_path(self) -> Path:
        """Get resolved data directory path."""
        return Path(self.persistence.data_dir).expanduser()

    @property
    def trades_path(self) -> Path:
        return self.data_path / self.persistence.trades_file

    @property
    def state_path(self) -> Path:
        return self.data_path / self.persistence.state_file


def load_config(config_path: str | None = None) -> BTCArbConfig:
    """Load configuration from file or environment."""
    if config_path:
        import yaml

        with open(config_path) as f:
            data = yaml.safe_load(f)
        return BTCArbConfig(**data)
    return BTCArbConfig()


def get_default_config() -> BTCArbConfig:
    """Get default configuration."""
    return BTCArbConfig()
