from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

PlatformCategory = Literal[
    "crypto_bot",
    "trading",
    "dex_aggregator",
    "prediction_market",
    "ai_trading",
    "bug_bounty",
    "messaging",
    "portfolio",
    "notification",
]


@dataclass
class AdapterMetric:
    """Score for a single dimension of the Advisor Mode evaluation."""

    score: float  # 0.0 – 10.0
    justification: str = ""
    weight: float = 1.0  # relative importance in overall score


@dataclass
class AdvisorScore:
    """Full Advisor Mode evaluation for a platform."""

    compatibility: AdapterMetric  # integration with existing Python/API infra
    community: AdapterMetric  # stars, contributors, activity
    automation_ease: AdapterMetric  # headless / API-first / config-driven
    docs_quality: AdapterMetric  # documentation completeness
    cost: AdapterMetric  # higher = cheaper / more free
    security: AdapterMetric  # auth methods, track record
    maturity: AdapterMetric  # years active, stable releases
    maintenance: AdapterMetric  # recent commits, issue responsiveness

    overall: float = 0.0  # weighted average (computed by registry)

    def compute_overall(self) -> float:
        metrics = [
            self.compatibility,
            self.community,
            self.automation_ease,
            self.docs_quality,
            self.cost,
            self.security,
            self.maturity,
            self.maintenance,
        ]
        total_weight = sum(m.weight for m in metrics)
        if total_weight == 0:
            self.overall = 0.0
        else:
            self.overall = round(sum(m.score * m.weight for m in metrics) / total_weight, 1)
        return self.overall

    def to_dict(self) -> dict[str, Any]:
        return {
            "compatibility": {"score": self.compatibility.score, "justification": self.compatibility.justification},
            "community": {"score": self.community.score, "justification": self.community.justification},
            "automation_ease": {
                "score": self.automation_ease.score,
                "justification": self.automation_ease.justification,
            },
            "docs_quality": {"score": self.docs_quality.score, "justification": self.docs_quality.justification},
            "cost": {"score": self.cost.score, "justification": self.cost.justification},
            "security": {"score": self.security.score, "justification": self.security.justification},
            "maturity": {"score": self.maturity.score, "justification": self.maturity.justification},
            "maintenance": {"score": self.maintenance.score, "justification": self.maintenance.justification},
            "overall": self.overall,
        }


@dataclass
class PlatformCapability:
    """What a platform can do (machine-readable capability)."""

    name: str  # e.g. "spot_trading", "backtesting", "market_making"
    description: str = ""
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformDef:
    """Descriptor for an external platform that can be integrated."""

    name: str
    category: PlatformCategory
    description: str = ""
    url: str = ""
    docs_url: str = ""
    api_type: str = "rest"  # rest | websocket | graphql | sdk | cli
    auth_type: str = "api_key"  # api_key | oauth2 | jwt | hmac | none
    env_keys: list[str] = field(default_factory=list)
    vault_provider: str = ""
    repo_url: str = ""
    language: str = "python"  # primary language
    license_type: str = "MIT"
    tags: list[str] = field(default_factory=list)
    score: AdvisorScore | None = None
    capabilities: list[PlatformCapability] = field(default_factory=list)
    adapter_class: str = ""  # dotted path to adapter implementation

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "url": self.url,
            "docs_url": self.docs_url,
            "api_type": self.api_type,
            "auth_type": self.auth_type,
            "env_keys": list(self.env_keys),
            "repo_url": self.repo_url,
            "language": self.language,
            "license": self.license_type,
            "tags": list(self.tags),
            "score": self.score.to_dict() if self.score else None,
            "capabilities": [{"name": c.name, "description": c.description} for c in self.capabilities],
        }


@dataclass
class Recommendation:
    """Single platform recommendation with transparent scoring."""

    platform: PlatformDef
    overall_score: float
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    verdict: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform.to_dict(),
            "overall_score": self.overall_score,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "verdict": self.verdict,
        }


@dataclass
class AdapterHealth:
    """Health status of an adapter connection."""

    connected: bool = False
    latency_ms: float = 0.0
    last_check: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str = ""
    balance: dict[str, float] = field(default_factory=dict)
    portfolio_value: float = 0.0


class AdapterError(Exception):
    """Base exception for adapter operations."""
