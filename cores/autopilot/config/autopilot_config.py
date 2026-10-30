"""Autopilot configuration system - Set once, run forever."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class IncomeMode(StrEnum):
    MAX_INCOME = "max_income"
    BEST_INCOME = "best_income"
    FAST_INCOME = "fast_income"


@dataclass
class PlatformConfig:
    enabled: bool = True
    tier: str = "general"
    categories: list[str] = field(default_factory=list)
    api_key_env: str = ""
    max_payout: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutomationConfig:
    mode: str = "best_income"
    max_concurrent_deliveries: int = 20
    max_concurrent_prs: int = 3
    auto_submit_threshold: float = 0.85
    wear_os_auto_approve_usd: int = 5000
    coder_agent_auto_merge_confidence: float = 0.92
    daily_check_enabled: bool = True
    achievement_notifications: bool = True


@dataclass
class CapitalAllocationConfig:
    emergency_reserve_pct: float = 0.10
    cash_reserve_pct: float = 0.15
    low_risk_pct: float = 0.35
    growth_pct: float = 0.25
    quant_pct: float = 0.10
    speculative_pct: float = 0.05
    hard_loss_budget_pct: float = 0.02


@dataclass
class RiskConfig:
    max_drawdown_pct: float = 0.15
    stop_loss_pct: float = 0.10
    max_leverage: float = 1.5
    correlation_threshold: float = 0.7


@dataclass
class IncomeTargetsConfig:
    work_income_monthly_usd: float = 50000.0
    savings_monthly_usd: float = 25000.0
    capital_target_usd: float = 500000.0
    target_monthly_usd: float = 100000.0


@dataclass
class ProfileConfig:
    name: str = "User"
    country: str = "AR"
    timezone: str = "America/Argentina/Buenos_Aires"
    languages: list[str] = field(default_factory=lambda: ["es", "en"])
    skills: list[str] = field(default_factory=list)
    experience_level: str = "expert"
    availability_hours: int = 40
    preferred_currencies: list[str] = field(default_factory=lambda: ["USD", "USDC", "ARS"])
    preferred_payment_methods: list[str] = field(default_factory=lambda: ["USDC", "Wire", "PayPal", "Payoneer"])
    remote_only: bool = True
    accepts_ai_tools: bool = True


@dataclass
class AutopilotConfig:
    profile: ProfileConfig = field(default_factory=ProfileConfig)
    income_targets: IncomeTargetsConfig = field(default_factory=IncomeTargetsConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    platforms: dict[str, PlatformConfig] = field(default_factory=dict)
    capital_allocation: CapitalAllocationConfig = field(default_factory=CapitalAllocationConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    income_targets_config: IncomeTargetsConfig = field(default_factory=IncomeTargetsConfig)

    @classmethod
    def load(cls, path: str | Path | None = None) -> AutopilotConfig:
        if path is None:
            path = Path.home() / ".ownex" / "autopilot.yaml"
        path = Path(path)
        if not path.exists():
            return cls._create_default(path)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls._from_dict(data)

    @classmethod
    def _create_default(cls, path: Path) -> AutopilotConfig:
        config = cls._default_config()
        path.parent.mkdir(parents=True, exist_ok=True)
        config.save(path)
        return config

    @classmethod
    def _default_config(cls) -> AutopilotConfig:
        platforms = {
            "outlier": PlatformConfig(enabled=True, tier="coding"),
            "dataannotation": PlatformConfig(enabled=True),
            "mindrift": PlatformConfig(enabled=True),
            "mercor": PlatformConfig(enabled=True, tier="coding"),
            "crowdgen": PlatformConfig(enabled=True),
            "opire": PlatformConfig(enabled=True),
            "superteam": PlatformConfig(enabled=True, categories=["dev", "content", "design"]),
            "algora": PlatformConfig(enabled=True),
            "hackerone": PlatformConfig(enabled=True, api_key_env="H1_API_KEY"),
            "bugcrowd": PlatformConfig(enabled=True, api_key_env="BC_API_KEY"),
            "intigriti": PlatformConfig(enabled=True, api_key_env="INTIGRITI_API_KEY"),
            "yeswehack": PlatformConfig(enabled=True, api_key_env="YWH_API_KEY"),
            "immunefi": PlatformConfig(enabled=True, api_key_env="IMMUNEFI_API_KEY"),
            "stargate": PlatformConfig(enabled=True, max_payout=10000000),
            "avail": PlatformConfig(enabled=True, max_payout=250000),
            "freqtrade": PlatformConfig(enabled=True, extra={"paper_trading_days": 30}),
            "atlas": PlatformConfig(enabled=True),
        }
        return cls(
            profile=ProfileConfig(),
            income_targets=IncomeTargetsConfig(),
            automation=AutomationConfig(),
            platforms=platforms,
            capital_allocation=CapitalAllocationConfig(),
            risk=RiskConfig(),
            income_targets_config=IncomeTargetsConfig(),
        )

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> AutopilotConfig:
        profile_data = data.get("profile", {})
        income_targets_data = data.get("income_targets", {})
        automation_data = data.get("automation", {})
        platforms_data = data.get("platforms", {})
        capital_allocation_data = data.get("capital_allocation", {})
        risk_data = data.get("risk", {})
        income_targets_config_data = data.get("income_targets_config", {})

        platforms = {}
        for k, v in platforms_data.items():
            if isinstance(v, dict):
                platforms[k] = PlatformConfig(**v)
            else:
                platforms[k] = PlatformConfig()

        return cls(
            profile=ProfileConfig(**profile_data),
            income_targets=IncomeTargetsConfig(**income_targets_data),
            automation=AutomationConfig(**automation_data),
            platforms=platforms,
            capital_allocation=CapitalAllocationConfig(**capital_allocation_data),
            risk=RiskConfig(**risk_data),
            income_targets_config=IncomeTargetsConfig(**income_targets_config_data),
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.__dict__,
            "income_targets": self.income_targets.__dict__,
            "automation": self.automation.__dict__,
            "platforms": {k: v.__dict__ for k, v in self.platforms.items()},
            "capital_allocation": self.capital_allocation.__dict__,
            "risk": self.risk.__dict__,
            "income_targets_config": self.income_targets_config.__dict__,
        }

    def get_platform_config(self, platform: str) -> PlatformConfig | None:
        return self.platforms.get(platform)

    def is_platform_enabled(self, platform: str) -> bool:
        cfg = self.platforms.get(platform)
        return cfg is not None and cfg.enabled

    def get_enabled_platforms(self) -> list[str]:
        return [k for k, v in self.platforms.items() if v.enabled]


def load_autopilot_config(path: str | Path | None = None) -> AutopilotConfig:
    return AutopilotConfig.load(path)
