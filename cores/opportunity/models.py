"""Data models for the Opportunity Intelligence Layer — read-only metadata.

This module provides backward compatibility for tests that import from core.opportunity.models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EVHRating(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


@dataclass(frozen=True)
class OpportunitySource:
    """Origin metadata for an opportunity."""

    type: str  # "platform", "independent", "web3", "emerging", "research"
    name: str
    url: str
    confidence: float  # 0.0-1.0


@dataclass(frozen=True)
class OpportunityCategory:
    """Categorisation of the opportunity's technical domain."""

    primary: str  # web, api, mobile, web3, cloud, hardware, other
    secondary: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoreBreakdown:
    """Detailed layered score with per-factor explanation."""

    reward_score: float
    competition_score: float
    discovery_score: float
    execution_score: float
    intelligence_score: float
    strategic_score: float
    confidence_score: float
    reward_explanation: str = ""
    competition_explanation: str = ""
    discovery_explanation: str = ""
    execution_explanation: str = ""
    intelligence_explanation: str = ""
    strategic_explanation: str = ""
    confidence_explanation: str = ""


@dataclass(frozen=True)
class EVHCalculation:
    """Expected Value Per Hour estimate."""

    value: float
    rating: EVHRating
    estimated_payout: float
    success_probability: float
    estimated_effort_hours: float
    explanation: str = ""


@dataclass(frozen=True)
class OpportunityScore:
    """Computed multi-factor score with human-readable reasoning."""

    overall: float  # 0.0-1.0
    reward_potential: float
    scope_quality: float
    technology_overlap: float
    competition_estimate: float
    freshness: float
    reasoning: list[str]
    breakdown: ScoreBreakdown | None = None
    evh: EVHCalculation | None = None


@dataclass(frozen=True)
class Opportunity:
    """A single public bug bounty or responsible disclosure opportunity."""

    id: str
    name: str
    source: OpportunitySource
    category: str  # "platform", "independent", "web3", "emerging", "research", "ai", "infrastructure", "cloud", "mobile", "browser_extension", "api_ecosystem", "open_source", "paid_research"
    subcategory: str = ""  # more granular classification
    public_url: str | None = None
    scope_summary: str | None = None
    reward_info: str | None = None
    technology_tags: list[str] = field(default_factory=list)
    last_update: str | None = None
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    score: OpportunityScore | None = None
    priority: str | None = None  # critical, high, medium, low
    created_at: str = ""
    estimated_payout: float = 0.0
    estimated_effort_hours: float = 1.0
    has_rewards: bool = True


@dataclass(frozen=True)
class OpportunitySnapshot:
    """Point-in-time snapshot of all tracked opportunities."""

    id: str
    timestamp: str
    period: str  # daily, weekly, monthly
    opportunities: list[Opportunity] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OpportunityProviderInfo:
    """Describes a registered provider."""

    name: str
    category: str
    active: bool
    opportunity_count: int
    last_refresh: str | None = None
    health_status: str = "unknown"  # healthy, degraded, down


@dataclass(frozen=True)
class OpportunityRecommendations:
    """Generated operator recommendations."""

    top_opportunities: list[Opportunity] = field(default_factory=list)
    top_independent: list[Opportunity] = field(default_factory=list)
    top_web3: list[Opportunity] = field(default_factory=list)
    fast_roi: list[Opportunity] = field(default_factory=list)
    long_term: list[Opportunity] = field(default_factory=list)
    low_competition: list[Opportunity] = field(default_factory=list)
    evh_ranked: list[Opportunity] = field(default_factory=list)
    generated_at: str = ""
    summary: str = ""


@dataclass(frozen=True)
class IdentityVaultEntry:
    """Stored provider identity."""

    provider_name: str
    email: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    session_state: str = "disconnected"  # connected, disconnected, expired
    last_checked: str | None = None
    health_status: str = "unknown"


# ============================================================================
# Backward compatibility layer for tests (core.opportunity.models)
# ============================================================================

OWNEX_WORK_CYCLES = {
    "security": "Bug bounty & vulnerability research",
    "forge": "Freelance development & contracting",
    "pulse": "Data annotation & AI training",
    "vault": "Crypto & DeFi opportunities",
    "atlas": "Career & networking",
}

OWNEX_WORK_CYCLE_ORDER = ["security", "forge", "pulse", "vault", "atlas"]


@dataclass
class PersonalHistory:
    """Historical performance metrics for personalization."""

    personal_acceptance_rate: float = 0.0
    personal_avg_payout: float = 0.0
    personal_avg_days: float = 0.0
    personal_competition_level: float = 0.5
    total_submissions: int = 0
    total_accepted: int = 0
    by_platform: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_vuln_type: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class UnifiedScore:
    """Unified scoring model with human-readable reasoning."""

    expected_value: float = 0.0
    acceptance_probability: float = 0.0
    speed_days: float = 0.0
    difficulty: float = 0.0
    competition: float = 0.0
    personal_fit: float = 0.3
    confidence: float = 0.5
    overall: float = 0.0

    def reasoning(self) -> list[str]:
        """Generate human-readable reasoning lines."""
        return [
            f"EV= ${self.expected_value:.2f}",
            f"acceptance= {self.acceptance_probability:.0%}",
            f"speed= {self.speed_days:.1f} days",
            f"difficulty= {self.difficulty:.2f}",
            f"competition= {self.competition:.2f}",
            f"fit= {self.personal_fit:.2f}",
            f"confidence= {self.confidence:.2f}",
            f"overall= {self.overall:.2f}",
        ]


@dataclass
class ScoredOpportunity:
    """A scored opportunity with all metadata."""

    id: str
    name: str
    cycle: str
    source_type: str
    source_name: str
    reward: float
    effort_hours: float
    platform: str
    technology_tags: list[str] = field(default_factory=list)
    url: str | None = None
    created_at: str = ""
    score: UnifiedScore | None = None


@dataclass
class Top5Recommendation:
    """Recommendation output from Top5Engine."""

    ranked: list[ScoredOpportunity] = field(default_factory=list)
    generated_at: str = ""
    total_scored: int = 0
    diversification_note: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "top5": [
                {
                    "id": o.id,
                    "name": o.name,
                    "cycle": o.cycle,
                    "source_name": o.source_name,
                    "reward": o.reward,
                    "effort_hours": o.effort_hours,
                    "platform": o.platform,
                    "technology_tags": o.technology_tags,
                    "url": o.url,
                    "created_at": o.created_at,
                    "score": {
                        "overall": o.score.overall if o.score else 0,
                        "expected_value": o.score.expected_value if o.score else 0,
                        "acceptance_probability": o.score.acceptance_probability if o.score else 0,
                        "speed_days": o.score.speed_days if o.score else 0,
                        "difficulty": o.score.difficulty if o.score else 0,
                        "competition": o.score.competition if o.score else 0,
                        "personal_fit": o.score.personal_fit if o.score else 0,
                        "confidence": o.score.confidence if o.score else 0,
                        "reasoning": o.score.reasoning() if o.score else [],
                    },
                }
                for o in self.ranked[:5]
            ],
            "total_scored": self.total_scored,
            "diversification_note": self.diversification_note,
            "summary": self.summary,
        }


class Top5Engine:
    """Selects top 5 opportunities with diversification."""

    def __init__(self, max_per_cycle: int = 5, max_per_source: int = 2):
        self.max_per_cycle = max_per_cycle
        self.max_per_source = max_per_source

    def compute(self, opportunities: list[ScoredOpportunity]) -> Top5Recommendation:
        if not opportunities:
            return Top5Recommendation(
                ranked=[],
                generated_at="",
                total_scored=0,
                diversification_note="No opportunities.",
                summary="No opportunities.",
            )

        # Sort by overall score descending
        sorted_opps = sorted(opportunities, key=lambda o: o.score.overall if o.score else 0, reverse=True)

        # Apply diversification
        selected = []
        cycle_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}

        for opp in sorted_opps:
            cycle_count = cycle_counts.get(opp.cycle, 0)
            source_count = source_counts.get(opp.source_name, 0)

            if cycle_count < self.max_per_cycle and source_count < self.max_per_source:
                selected.append(opp)
                cycle_counts[opp.cycle] = cycle_count + 1
                source_counts[opp.source_name] = source_count + 1

            if len(selected) >= 5:
                break

        # Build diversification note
        cycles = set(o.cycle for o in selected)
        sources = set(o.source_name for o in selected)
        div_note = f"{len(selected)} selected from {len(sorted_opps)} scored. Cycles: {', '.join(sorted(cycles))}. Sources: {', '.join(sorted(sources))}."

        # Build summary
        if selected:
            best = selected[0]
            summary = (
                f"Top 1: {best.name} (${best.score.expected_value:.0f} EV)" if best.score else f"Top 1: {best.name}"
            )
        else:
            summary = "No opportunities."

        return Top5Recommendation(
            ranked=selected,
            generated_at="",
            total_scored=len(sorted_opps),
            diversification_note=div_note,
            summary=summary,
        )


class PersonalHistoryTracker:
    """Tracks personal history from metrics."""

    def __init__(self, metrics: Any = None):
        self.metrics = metrics

    def get_history(self) -> PersonalHistory:
        if not self.metrics:
            return PersonalHistory()

        # Mock metrics interface for backward compatibility
        acceptance_rate = getattr(self.metrics, "acceptance_rate", lambda: {})()
        payout_summary = getattr(self.metrics, "payout_summary", lambda: {})()
        time_metrics = getattr(self.metrics, "time_metrics", lambda: {})()
        roi_by_vuln = getattr(self.metrics, "roi_by_vuln_type", lambda: [])()

        total = sum(v.get("total", 0) for v in acceptance_rate.values())
        accepted = sum(v.get("accepted", 0) for v in acceptance_rate.values())
        pending = sum(v.get("pending", 0) for v in acceptance_rate.values())

        return PersonalHistory(
            personal_acceptance_rate=accepted / max(total - pending, 1) if total > pending else 0.0,
            personal_avg_payout=payout_summary.get("avg_payout", 0.0),
            personal_avg_days=time_metrics.get("avg_days_to_acceptance", 0.0),
            total_submissions=total,
            total_accepted=accepted,
            by_platform=acceptance_rate,
            by_vuln_type={
                item["vuln_type"]: {
                    "total_payout": item["total_payout"],
                    "count": item["count"],
                    "avg_payout": item["avg_payout"],
                }
                for item in roi_by_vuln
            },
        )


def score_opportunity(
    opp_id: str,
    name: str,
    cycle: str,
    source_type: str,
    source_name: str,
    reward: float,
    effort_hours: float,
    platform: str,
    technology_tags: list[str] | None = None,
    url: str | None = None,
    created_at: str = "",
    personal: PersonalHistory | None = None,
) -> ScoredOpportunity:
    """Score an opportunity (backward compatibility)."""

    tags = technology_tags or []
    base_ev = reward / max(effort_hours, 0.1)

    # Simple scoring logic
    difficulty = 0.4
    for tag in tags:
        if tag in ["web3", "solidity", "defi", "rust", "move", "smart_contract"]:
            difficulty += 0.1
        elif tag in ["xss", "csrf"]:
            difficulty -= 0.05

    difficulty = max(0.1, min(0.9, difficulty))

    competition = 0.4
    if platform in ["hackerone", "bugcrowd"]:
        competition = 0.6
    elif platform in ["immunefi"]:
        competition = 0.8

    acceptance = 0.3
    if personal:
        platform_data = personal.by_platform.get(platform, {})
        if platform_data:
            acceptance = platform_data.get("acceptance_rate", 0.3)

    personal_fit = 0.3
    if personal and personal.total_submissions > 0:
        personal_fit = min(0.9, personal.personal_acceptance_rate + 0.3)

    overall = (base_ev / 1000) * (1 - difficulty) * (1 - competition) * acceptance * personal_fit
    overall = max(0.0, min(1.0, overall))

    score = UnifiedScore(
        expected_value=base_ev,
        acceptance_probability=acceptance,
        speed_days=14.0,
        difficulty=difficulty,
        competition=competition,
        personal_fit=personal_fit,
        confidence=0.7,
        overall=overall,
    )

    return ScoredOpportunity(
        id=opp_id,
        name=name,
        cycle=cycle,
        source_type=source_type,
        source_name=source_name,
        reward=reward,
        effort_hours=effort_hours,
        platform=platform,
        technology_tags=tags,
        url=url,
        created_at=created_at,
        score=score,
    )
