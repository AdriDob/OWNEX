"""OWNEX Opportunity Score Engine - Core models and logic.

This module implements the scoring system for bug bounty opportunities,
integrating personal history, platform analytics, and EV calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class PersonalHistory:
    """Operator's historical performance across platforms and vuln types."""

    personal_acceptance_rate: float = 0.0
    personal_avg_payout: float = 0.0
    personal_avg_days: float = 0.0
    personal_competition_level: float = 0.5
    total_submissions: int = 0
    total_accepted: int = 0
    by_platform: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_vuln_type: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class PersonalHistoryTracker:
    """Tracks and updates personal history from submission outcomes."""

    history: PersonalHistory = field(default_factory=PersonalHistory)
    metrics: Any = None  # Compatibility with tests

    def __init__(self, history: PersonalHistory | None = None, metrics: Any = None):
        self.history = history or PersonalHistory()
        self.metrics = metrics

    def record_submission(
        self,
        platform: str,
        vuln_type: str,
        accepted: bool,
        payout: float = 0.0,
        days_to_resolution: float = 0.0,
    ) -> None:
        """Record a submission outcome and update history."""
        self.history.total_submissions += 1
        if accepted:
            self.history.total_accepted += 1

        # Update acceptance rate
        self.history.personal_acceptance_rate = self.history.total_accepted / self.history.total_submissions

        # Update average payout (only for accepted)
        if accepted and payout > 0:
            total_payout = self.history.personal_avg_payout * (self.history.total_accepted - 1)
            self.history.personal_avg_payout = (total_payout + payout) / self.history.total_accepted

        # Update average days
        if accepted and days_to_resolution > 0:
            total_days = self.history.personal_avg_days * (self.history.total_accepted - 1)
            self.history.personal_avg_days = (total_days + days_to_resolution) / self.history.total_accepted

        # Update platform stats
        if platform not in self.history.by_platform:
            self.history.by_platform[platform] = {
                "total": 0,
                "accepted": 0,
                "acceptance_rate": 0.0,
            }
        plat = self.history.by_platform[platform]
        plat["total"] += 1
        if accepted:
            plat["accepted"] += 1
        plat["acceptance_rate"] = plat["accepted"] / plat["total"]

        # Update vuln type stats
        if vuln_type not in self.history.by_vuln_type:
            self.history.by_vuln_type[vuln_type] = {
                "total_payout": 0.0,
                "count": 0,
                "avg_payout": 0.0,
            }
        vt = self.history.by_vuln_type[vuln_type]
        if accepted:
            vt["count"] += 1
            vt["total_payout"] += payout
            vt["avg_payout"] = vt["total_payout"] / vt["count"]

        self.history.last_updated = datetime.now(UTC).isoformat()

    def get_history(self) -> PersonalHistory:
        """Get the current personal history."""
        return self.history


@dataclass
class UnifiedScore:
    """Unified scoring model combining all factors into a single decision metric."""

    expected_value: float = 0.0
    acceptance_probability: float = 0.0
    speed_days: float = 0.0
    difficulty: float = 0.0
    competition: float = 0.0
    personal_fit: float = 0.0
    confidence: float = 0.0
    overall: float = 0.0

    def reasoning(self) -> list[str]:
        """Generate human-readable reasoning for each factor."""
        return [
            f"EV= ${self.expected_value:.2f}",
            f"acceptance={self.acceptance_probability:.2f}",
            f"speed={self.speed_days:.1f}d",
            f"difficulty={self.difficulty:.2f}",
            f"competition={self.competition:.2f}",
            f"fit={self.personal_fit:.2f}",
            f"confidence={self.confidence:.2f}",
            f"overall={self.overall:.2f}",
        ]


@dataclass
class ScoredOpportunity:
    """An opportunity with its computed unified score."""

    id: str
    name: str
    cycle: str
    source_type: str
    source_name: str
    reward: float
    effort_hours: float
    platform: str
    technology_tags: list[str]
    url: str
    created_at: str
    score: UnifiedScore
    metadata: dict[str, Any] = field(default_factory=dict)
    original: object | None = None  # Compatibility with cores/opportunity/scorer.py

    @property
    def opportunity_id(self) -> str:
        return self.id

    @property
    def estimated_payout(self) -> float:
        return self.reward

    @property
    def estimated_effort_hours(self) -> float:
        return self.effort_hours

    @property
    def vuln_type(self) -> str:
        return self.cycle

    @property
    def scope_quality(self) -> float:
        return 1.0 - self.score.difficulty

    @property
    def competition_level(self) -> float:
        return self.score.competition

    @property
    def freshness_days(self) -> float:
        return self.score.speed_days


@dataclass
class Top5Recommendation:
    """Top 5 recommendations with diversification."""

    ranked: list[ScoredOpportunity]
    generated_at: str
    total_scored: int
    diversification_note: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "top5": [
                {
                    "id": o.id,
                    "name": o.name,
                    "cycle": o.cycle,
                    "source_type": o.source_type,
                    "source_name": o.source_name,
                    "reward": o.reward,
                    "effort_hours": o.effort_hours,
                    "platform": o.platform,
                    "technology_tags": o.technology_tags,
                    "url": o.url,
                    "created_at": o.created_at,
                    "score": {
                        "overall": o.score.overall,
                        "expected_value": o.score.expected_value,
                        "acceptance_probability": o.score.acceptance_probability,
                        "difficulty": o.score.difficulty,
                        "competition": o.score.competition,
                        "personal_fit": o.score.personal_fit,
                        "confidence": o.score.confidence,
                        "reasoning": o.score.reasoning(),
                    },
                }
                for o in self.ranked
            ],
            "generated_at": self.generated_at,
            "total_scored": self.total_scored,
            "diversification_note": self.diversification_note,
            "summary": self.summary,
        }


@dataclass
class Top5Engine:
    """Generates top 5 recommendations from scored opportunities."""

    personal_history: PersonalHistory = field(default_factory=PersonalHistory)

    def score_opportunity(
        self,
        opp_id: str,
        name: str,
        cycle: str,
        source_type: str,
        source_name: str,
        reward: float,
        effort_hours: float,
        platform: str,
        technology_tags: list[str],
        url: str,
        created_at: str,
        personal: PersonalHistory | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ScoredOpportunity:
        """Score a single opportunity using unified scoring."""
        ph = personal or self.personal_history

        # Calculate acceptance probability based on personal history
        acceptance_prob = ph.personal_acceptance_rate
        if acceptance_prob == 0:
            acceptance_prob = 0.15  # baseline

        # Platform-specific adjustment
        if platform in ph.by_platform:
            plat_data = ph.by_platform[platform]
            acceptance_prob = (acceptance_prob + plat_data["acceptance_rate"]) / 2

        # Vuln type adjustment
        vuln_type = cycle
        if vuln_type in ph.by_vuln_type:
            vt_data = ph.by_vuln_type[vuln_type]
            if vt_data["avg_payout"] > 0:
                # Boost confidence if we have good history with this vuln type
                acceptance_prob = min(0.9, acceptance_prob * 1.2)

        # Expected value calculation
        expected_value = reward * acceptance_prob

        # Speed factor (inverse of days) - estimate from created_at
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            freshness_days = (datetime.now(UTC) - created).days
        except Exception:
            freshness_days = 7.0
        speed_score = max(0.0, 1.0 - (freshness_days / 30.0))  # newer = better

        # Difficulty based on technology tags
        difficulty = 0.5
        if "api" in technology_tags:
            difficulty = 0.4
        if "graphql" in technology_tags:
            difficulty = 0.5
        if "jwt" in technology_tags:
            difficulty = 0.6
        if "xss" in technology_tags:
            difficulty = 0.3
        if "sqli" in technology_tags:
            difficulty = 0.7

        # Competition factor - estimate from platform
        competition = 0.5
        if platform == "hackerone":
            competition = 0.7
        elif platform == "bugcrowd":
            competition = 0.6
        elif platform == "intigriti":
            competition = 0.5

        # Personal fit based on historical payout for this vuln type
        personal_fit = 0.5
        if vuln_type in ph.by_vuln_type:
            vt_data = ph.by_vuln_type[vuln_type]
            if vt_data["avg_payout"] > ph.personal_avg_payout * 1.5:
                personal_fit = 0.8
            elif vt_data["avg_payout"] > 0:
                personal_fit = 0.6

        # Confidence based on data availability
        confidence = 0.5
        if ph.total_submissions > 10:
            confidence += 0.2
        if platform in ph.by_platform:
            confidence += 0.15
        if vuln_type in ph.by_vuln_type:
            confidence += 0.15
        confidence = min(1.0, confidence)

        # Overall weighted score
        overall = (
            0.30 * min(1.0, expected_value / 1000.0)  # EV component
            + 0.20 * acceptance_prob
            + 0.15 * speed_score
            + 0.10 * (1.0 - difficulty)
            + 0.10 * (1.0 - competition)
            + 0.10 * personal_fit
            + 0.05 * confidence
        )

        unified = UnifiedScore(
            expected_value=expected_value,
            acceptance_probability=acceptance_prob,
            speed_days=freshness_days,
            difficulty=difficulty,
            competition=competition,
            personal_fit=personal_fit,
            confidence=confidence,
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
            technology_tags=technology_tags,
            url=url,
            created_at=created_at,
            score=unified,
            metadata=metadata or {},
        )

    def compute(
        self,
        opportunities: list[dict[str, Any]],
        max_results: int = 5,
    ) -> Top5Recommendation:
        """Generate top 5 recommendations from a list of opportunity dicts."""
        scored = []

        for opp in opportunities:
            scored.append(
                self.score_opportunity(
                    opp_id=opp.get("id", ""),
                    name=opp.get("name", "Unknown"),
                    cycle=opp.get("cycle", "security"),
                    source_type=opp.get("source_type", "platform"),
                    source_name=opp.get("source_name", "unknown"),
                    reward=opp.get("reward", 0.0),
                    effort_hours=opp.get("effort_hours", 1.0),
                    platform=opp.get("platform", "unknown"),
                    technology_tags=opp.get("technology_tags", []),
                    url=opp.get("url", ""),
                    created_at=opp.get("created_at", datetime.now(UTC).isoformat()),
                    personal=opp.get("personal"),
                    metadata=opp.get("metadata", {}),
                )
            )

        # Sort by overall score descending
        scored.sort(key=lambda x: x.score.overall, reverse=True)

        # Take top N
        top = scored[:max_results]

        # Diversification note
        platforms = set(o.platform for o in top)
        cycles = set(o.cycle for o in top)
        diversification_note = f"Diversified across {len(platforms)} platforms and {len(cycles)} cycles."

        summary = f"Top {len(top)} opportunities selected from {len(scored)} scored."

        return Top5Recommendation(
            ranked=top,
            generated_at=datetime.now(UTC).isoformat(),
            total_scored=len(scored),
            diversification_note=diversification_note,
            summary=summary,
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
    technology_tags: list[str],
    url: str,
    created_at: str,
    personal: PersonalHistory | None = None,
    metadata: dict[str, Any] | None = None,
) -> ScoredOpportunity:
    """Convenience function to score a single opportunity."""
    engine = Top5Engine(personal_history=personal or PersonalHistory())
    return engine.score_opportunity(
        opp_id=opp_id,
        name=name,
        cycle=cycle,
        source_type=source_type,
        source_name=source_name,
        reward=reward,
        effort_hours=effort_hours,
        platform=platform,
        technology_tags=technology_tags,
        url=url,
        created_at=created_at,
        personal=personal,
        metadata=metadata,
    )


# Work cycle constants - match test expectations
OWNEX_WORK_CYCLES = {
    "security": {"name": "Security", "description": "Security research & bug bounty"},
    "forge": {"name": "Forge", "description": "Research & discovery phase"},
    "pulse": {"name": "Pulse", "description": "Active exploitation & validation"},
    "vault": {"name": "Vault", "description": "Report generation & evidence packaging"},
    "atlas": {"name": "Atlas", "description": "Mapping & reconnaissance"},
}

OWNEX_WORK_CYCLE_ORDER = ["security", "forge", "pulse", "vault", "atlas"]


__all__ = [
    # Core models
    "PersonalHistory",
    "PersonalHistoryTracker",
    "ScoredOpportunity",
    "Top5Engine",
    "Top5Recommendation",
    "UnifiedScore",
    "score_opportunity",
    # Work cycle constants
    "OWNEX_WORK_CYCLES",
    "OWNEX_WORK_CYCLE_ORDER",
]
