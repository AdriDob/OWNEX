from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum, StrEnum, auto
from typing import Any


class ToolStatus(Enum):
    AVAILABLE = auto()
    NOT_FOUND = auto()
    ERROR = auto()


class ToolCategory(Enum):
    RECON = "recon"
    SCANNER = "scanner"
    FUZZING = "fuzzing"
    EXPLOIT = "exploit"
    OSINT = "osint"
    BROWSER = "browser"
    CRYPTO_EXCHANGE = "crypto_exchange"
    CRYPTO_DEX = "crypto_dex"
    CRYPTO_SNIPER = "crypto_sniper"
    CRYPTO_ANALYSIS = "crypto_analysis"
    AUTOMATION = "automation"
    REPORT = "report"
    VISUALIZATION = "visualization"
    DATA = "data"
    AI = "ai"
    INFRASTRUCTURE = "infrastructure"


class RevenueCategory(StrEnum):
    BUG_BOUNTY = "bug_bounty"
    CRYPTO_TRADING = "crypto_trading"
    DEFI_YIELD = "defi_yield"
    ARBITRAGE = "arbitrage"


@dataclass
class Finding:
    id: str = ""
    title: str = ""
    description: str = ""
    severity: str = ""
    cvss_score: float = 0.0
    cwe: str = ""
    tool: str = ""
    target: str = ""
    endpoint: str = ""
    evidence: str = ""
    confidence: float = 0.0
    raw_output: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradeSignal:
    pair: str
    side: str
    confidence: float
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    quantity: Decimal
    reason: str = ""
    strategy: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RevenueEvent:
    source: str
    category: RevenueCategory
    amount: Decimal
    currency: str = "USD"
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CapitalState:
    total: Decimal = Decimal("0")
    allocated: Decimal = Decimal("0")
    available: Decimal = Decimal("0")
    in_positions: Decimal = Decimal("0")
    pending_withdrawal: Decimal = Decimal("0")
    daily_pnl: Decimal = Decimal("0")
    weekly_pnl: Decimal = Decimal("0")
    total_pnl: Decimal = Decimal("0")
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RevenueReport:
    daily_revenue: Decimal = Decimal("0")
    weekly_revenue: Decimal = Decimal("0")
    monthly_revenue: Decimal = Decimal("0")
    total_revenue: Decimal = Decimal("0")
    bounty_revenue: Decimal = Decimal("0")
    trading_revenue: Decimal = Decimal("0")
    defi_revenue: Decimal = Decimal("0")
    total_findings: int = 0
    accepted_findings: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    win_rate: float = 0.0
    estimated_yearly: Decimal = Decimal("0")
    generated_at: datetime = field(default_factory=datetime.utcnow)
