"""Competition Intelligence — Estimate competition level for opportunities.

Uses multiple signals:
- Platform-specific competition metrics
- Bounty/issue activity levels
- Time-to-first-submission patterns
- Duplicate detection
- Skill overlap with other candidates
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cores.direct_work_engine.models import Opportunity, UserProfile

logger = logging.getLogger("ownex.competition_intel")


@dataclass(slots=True)
class CompetitionSignal:
    """A single competition signal."""

    source: str
    level: float  # 0–1
    confidence: float  # 0–1
    details: dict | None = None


@dataclass(slots=True)
class CompetitionAssessment:
    """Complete competition assessment for an opportunity."""

    overall_level: float  # 0–1
    confidence: float
    signals: list[CompetitionSignal]
    estimated_competitors: int
    time_to_first_submission_hours: float | None = None
    duplicate_risk: float = 0.0
    first_mover_advantage: bool = False
    recommendation: str = ""


# Platform-specific competition baselines (0–1)
_PLATFORM_COMPETITION_BASELINE = {
    "hackerone": 0.75,
    "bugcrowd": 0.70,
    "intigriti": 0.65,
    "yeswehack": 0.60,
    "opire": 0.30,
    "issuehunt": 0.35,
    "algora": 0.40,
    "freelancer": 0.80,
    "upwork": 0.85,
    "fiverr": 0.60,
    "outlier": 0.25,
    "mindrift": 0.20,
    "alignerr": 0.30,
    "mercor": 0.50,
}

# Category competition multipliers
_CATEGORY_COMPETITION = {
    "bug_bounty": 1.2,
    "dev_bounty": 1.0,
    "security_research": 1.1,
    "ai_evaluation": 0.7,
    "data_annotation": 0.5,
    "synthetic_data": 0.6,
    "software_engineering": 1.0,
    "frontend": 1.1,
    "backend": 1.0,
    "full_stack": 1.0,
    "mobile_development": 1.0,
    "ai_engineering": 1.3,
    "llm_engineering": 1.4,
    "data_engineering": 1.0,
}

# Reward tiers → competition multiplier
_REWARD_COMPETITION = {
    # (min_reward, max_reward): multiplier
    (0, 50): 0.6,
    (50, 200): 0.9,
    (200, 500): 1.1,
    (500, 1000): 1.3,
    (1000, float("inf")): 1.5,
}


def _reward_competition_multiplier(reward: float) -> float:
    for (min_r, max_r), mult in _REWARD_COMPETITION.items():
        if min_r <= reward < max_r:
            return mult
    return 1.0


@dataclass(slots=True)
class CompetitionIntelEngine:
    """Engine for assessing competition on opportunities."""

    def assess(
        self, opportunity: Opportunity, platform_facts: dict | None = None, user_profile: UserProfile | None = None
    ) -> CompetitionAssessment:
        """Assess competition for a single opportunity."""
        signals = []
        platform = opportunity.platform.value if hasattr(opportunity.platform, "value") else str(opportunity.platform)
        category = opportunity.category.value if hasattr(opportunity.category, "value") else str(opportunity.category)
        reward = float(opportunity.payment or 0)

        # 1. Platform baseline
        base_level = _PLATFORM_COMPETITION_BASELINE.get(platform.lower(), 0.5)
        signals.append(
            CompetitionSignal(
                source="platform_baseline",
                level=base_level,
                confidence=0.8,
                details={"platform": platform, "baseline": base_level},
            )
        )

        # 2. Category multiplier
        cat_mult = _CATEGORY_COMPETITION.get(category.lower(), 1.0)
        signals.append(
            CompetitionSignal(
                source="category",
                level=min(1.0, base_level * cat_mult),
                confidence=0.7,
                details={"category": category, "multiplier": cat_mult},
            )
        )

        # 3. Reward tier
        reward_mult = _reward_competition_multiplier(float(opportunity.payment or 0))
        signals.append(
            CompetitionSignal(
                source="reward_tier",
                level=min(1.0, base_level * reward_mult),
                confidence=0.75,
                details={"reward": float(opportunity.payment or 0), "multiplier": reward_mult},
            )
        )

        # 4. Platform facts (if available)
        if platform_facts:
            # Check for active bounties count
            active_count = platform_facts.get("active_bounties", 0)
            if active_count > 20:
                signals.append(
                    CompetitionSignal(
                        source="high_volume",
                        level=min(1.0, base_level * 1.2),
                        confidence=0.7,
                        details={"active_bounties": active_count},
                    )
                )
            # Check for recent submissions
            recent_subs = platform_facts.get("recent_submissions_24h", 0)
            if recent_subs > 10:
                signals.append(
                    CompetitionSignal(
                        source="high_activity",
                        level=min(1.0, base_level * 1.15),
                        confidence=0.7,
                        details={"recent_submissions_24h": recent_subs},
                    )
                )

        # 4. Skill match (user-specific)
        if user_profile and hasattr(user_profile, "skills"):
            # Would compute overlap between user skills and opportunity requirements
            # For now, use a default
            pass

        # 5. Time-based signals (freshness)
        discovered_at = getattr(opportunity, "discovered_at", None)
        if discovered_at:
            try:
                from datetime import UTC, datetime

                if isinstance(discovered_at, str):
                    discovered = datetime.fromisoformat(discovered_at.replace("Z", "+00:00"))
                else:
                    discovered = discovered_at
                age_hours = (datetime.now(UTC) - discovered).total_seconds() / 3600
                if age_hours < 24:
                    signals.append(
                        CompetitionSignal(
                            source="fresh_opportunity",
                            level=min(1.0, base_level * 1.1),  # fresher = more competition
                            confidence=0.8,
                            details={"age_hours": age_hours},
                        )
                    )
                elif age_hours > 168:  # > 1 week
                    signals.append(
                        CompetitionSignal(
                            source="stale_opportunity",
                            level=max(0.2, base_level * 0.8),  # older = less competition but maybe taken
                            confidence=0.7,
                            details={"age_hours": age_hours},
                        )
                    )
            except Exception:
                pass

        # Aggregate signals
        if not signals:
            overall = base_level
            conf = 0.5
        else:
            weighted_sum = sum(s.level * s.confidence for s in signals)
            total_conf = sum(s.confidence for s in signals)
            overall = weighted_sum / total_conf if total_conf > 0 else base_level
            conf = total_conf / len(signals)

        # Clamp
        overall = max(0.0, min(1.0, overall))

        # Estimate competitors
        estimated_competitors = int(overall * 20)  # rough estimate

        # Time to first submission (heuristic)
        if overall > 0.7:
            time_to_first = 2.0  # hours
        elif overall > 0.5:
            time_to_first = 6.0
        else:
            time_to_first = 24.0

        # Duplicate risk
        duplicate_risk = min(0.3, overall * 0.3)

        # First mover advantage
        first_mover = False
        if overall < 0.5 and reward > 200:
            first_mover = True

        # Recommendation
        if overall < 0.3:
            rec = "LOW COMPETITION — High first-mover advantage, execute fast"
        elif overall < 0.5:
            rec = "MODERATE COMPETITION — Good opportunity, prepare quality submission"
        elif overall < 0.7:
            rec = "HIGH COMPETITION — Need exceptional submission, consider first-mover"
        else:
            rec = "VERY HIGH COMPETITION — Only pursue if strong skill match or unique angle"

        return CompetitionAssessment(
            overall_level=overall,
            confidence=conf,
            signals=signals,
            estimated_competitors=estimated_competitors,
            time_to_first_submission_hours=time_to_first,
            duplicate_risk=duplicate_risk,
            first_mover_advantage=first_mover,
            recommendation=rec,
        )

    def assess_batch(
        self, opportunities: list, platform_facts: dict | None = None, user_profile: UserProfile | None = None
    ) -> list[CompetitionAssessment]:
        """Assess multiple opportunities."""
        return [self.assess(opp, platform_facts, None) for opp in opportunities]


# ──────────────────────────────────────────────────────────────────────
# Convenience
# ──────────────────────────────────────────────────────────────────────

_competition_engine: CompetitionIntelEngine | None = None


def get_competition_engine() -> CompetitionIntelEngine:
    global _competition_engine
    if _competition_engine is None:
        _competition_engine = CompetitionIntelEngine()
    return _competition_engine


def assess_competition(
    opportunity: Opportunity, platform_facts: dict | None = None, user_profile: UserProfile | None = None
) -> CompetitionAssessment:
    """Convenience function for single opportunity."""
    return get_competition_engine().assess(opportunity, platform_facts, user_profile)
