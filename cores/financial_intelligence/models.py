from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Opportunity:
    """A ranked financial opportunity with expected value and risk assessment."""

    source: str  # "bug_bounty", "crypto", "stocks", "etfs", "stablecoin_yield", etc.
    label: str
    expected_value: float
    confidence_interval: tuple[float, float]
    historical_win_rate: float
    volatility: float
    liquidity: float
    risk_score: float
    correlation: float
    opportunity_cost: float
    execution_complexity: float  # 0-1
    market_regime: str  # "bull", "bear", "sideways", "volatile"
    data_quality: float
    model_confidence: float
    consensus_score: float
    priority_score: float  # composite: expected_value * win_rate / risk
    estimated_effort_hours: float
    estimated_time_to_payout_days: float
    reasoning: str = ""
    rejected_reasons: list[str] = field(default_factory=list)
    agent_votes: dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "label": self.label,
            "expected_value": self.expected_value,
            "confidence_interval": list(self.confidence_interval),
            "historical_win_rate": self.historical_win_rate,
            "volatility": self.volatility,
            "liquidity": self.liquidity,
            "risk_score": self.risk_score,
            "correlation": self.correlation,
            "opportunity_cost": self.opportunity_cost,
            "execution_complexity": self.execution_complexity,
            "market_regime": self.market_regime,
            "data_quality": self.data_quality,
            "model_confidence": self.model_confidence,
            "consensus_score": self.consensus_score,
            "priority_score": self.priority_score,
            "estimated_effort_hours": self.estimated_effort_hours,
            "estimated_time_to_payout_days": self.estimated_time_to_payout_days,
            "reasoning": self.reasoning,
            "rejected_reasons": self.rejected_reasons,
            "agent_votes": self.agent_votes,
            "created_at": self.created_at,
        }


@dataclass
class RiskPolicy:
    position_size_pct: float = 0.02  # max 2% per position
    max_allocation_pct: float = 0.40  # max 40% per asset class
    max_daily_loss_pct: float = 0.03
    max_monthly_loss_pct: float = 0.10
    drawdown_protection_pct: float = 0.15  # halt if 15% drawdown
    min_diversification: int = 3
    correlation_limit: float = 0.70
    emergency_stop: bool = False
    circuit_breaker_active: bool = False
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_size_pct": self.position_size_pct,
            "max_allocation_pct": self.max_allocation_pct,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_monthly_loss_pct": self.max_monthly_loss_pct,
            "drawdown_protection_pct": self.drawdown_protection_pct,
            "min_diversification": self.min_diversification,
            "correlation_limit": self.correlation_limit,
            "emergency_stop": self.emergency_stop,
            "circuit_breaker_active": self.circuit_breaker_active,
            "last_updated": self.last_updated,
        }


@dataclass
class F1Message:
    """A message from F1 to the user — friendly, retro, informative."""

    category: str  # "info", "risk", "success", "warning", "confirmation"
    title: str
    body: str
    emoji: str = ""
    requires_action: bool = False
    action_label: str = ""
    action_payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "title": self.title,
            "body": self.body,
            "emoji": self.emoji,
            "requires_action": self.requires_action,
            "action_label": self.action_label,
            "action_payload": self.action_payload,
            "created_at": self.created_at,
        }


@dataclass
class AgentVote:
    agent_name: str
    score: float
    confidence: float
    evidence: str
    reasoning: str
