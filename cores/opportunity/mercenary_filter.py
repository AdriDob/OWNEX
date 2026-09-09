"""Mercenary Filter — Aggressive scoring system for opportunity filtering.

Ownex operates in "mercenary technical mode":
- Not seeking employment ("hire me")
- Seeking exchangeable value ("solve public problem → monetize")

Filter Criteria (SCORE > 80/100):
- Verifiable payment: +20
- Defined task: +20
- No interview required: +15
- No portfolio required: +15
- Argentina compatible: +10
- Real IT work: +10
- Reasonable time: +10

11 Categories with priority levels:
1. Bug Bounty (EXTREME)
2. Development by tasks (EXTREME)
3. Testing/QA (HIGH)
4. AI Evaluation (MEDIUM-HIGH)
5. Game Programming (MEDIUM)
6. Enterprise Automation (HIGH)
7. Data Engineering (MEDIUM)
8. DevOps/Cloud (MEDIUM)
9. Technical Documentation (MEDIUM)
10. Hackathons (MEDIUM)
11. Funded Open Source (MEDIUM)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger("ownex.opportunity.mercenary_filter")


class CategoryPriority(IntEnum):
    """Priority levels for opportunity categories."""

    EXTREME = 100
    HIGH = 75
    MEDIUM_HIGH = 60
    MEDIUM = 50
    LOW = 25


class OpportunityCategory(IntEnum):
    """11 categories of opportunities with priorities.

    Local layer taxonomy — canonical mapping in ``cores.work_taxonomy``.
    """

    BUG_BOUNTY = 1
    DEVELOPMENT_TASKS = 2
    TESTING_QA = 3
    AI_EVALUATION = 4
    GAME_PROGRAMMING = 5
    ENTERPRISE_AUTOMATION = 6
    DATA_ENGINEERING = 7
    DEVOPS_CLOUD = 8
    TECHNICAL_DOCUMENTATION = 9
    HACKATHONS = 10
    FUNDED_OPEN_SOURCE = 11


# Category priorities mapping
CATEGORY_PRIORITIES: dict[OpportunityCategory, CategoryPriority] = {
    OpportunityCategory.BUG_BOUNTY: CategoryPriority.EXTREME,
    OpportunityCategory.DEVELOPMENT_TASKS: CategoryPriority.EXTREME,
    OpportunityCategory.TESTING_QA: CategoryPriority.HIGH,
    OpportunityCategory.AI_EVALUATION: CategoryPriority.MEDIUM_HIGH,
    OpportunityCategory.GAME_PROGRAMMING: CategoryPriority.MEDIUM,
    OpportunityCategory.ENTERPRISE_AUTOMATION: CategoryPriority.HIGH,
    OpportunityCategory.DATA_ENGINEERING: CategoryPriority.MEDIUM,
    OpportunityCategory.DEVOPS_CLOUD: CategoryPriority.MEDIUM,
    OpportunityCategory.TECHNICAL_DOCUMENTATION: CategoryPriority.MEDIUM,
    OpportunityCategory.HACKATHONS: CategoryPriority.MEDIUM,
    OpportunityCategory.FUNDED_OPEN_SOURCE: CategoryPriority.MEDIUM,
}


@dataclass
class MercenaryAttributes:
    """Attributes for mercenary scoring."""

    # Payment
    verifiable_payment: bool = False
    payment_amount_verified: bool = False
    payment_history_good: bool = False

    # Task definition
    defined_objective: bool = False
    clear_deliverable: bool = False
    scope_well_defined: bool = False

    # Requirements
    no_interview_required: bool = False
    no_portfolio_required: bool = False
    no_experience_required: bool = False

    # Location/compatibility
    argentina_compatible: bool = False
    remote_work: bool = False
    flexible_hours: bool = False

    # Technical quality
    real_it_work: bool = False
    technical_skill_required: bool = False
    no_mechanical_task: bool = False

    # Time
    reasonable_timeframe: bool = False
    estimated_hours: float = 0.0
    hourly_rate_competitive: bool = False

    # Metadata
    category: OpportunityCategory = OpportunityCategory.DEVELOPMENT_TASKS
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MercenaryScore:
    """Result of mercenary scoring."""

    total_score: float
    passed_filter: bool
    category: OpportunityCategory
    category_priority: CategoryPriority

    # Component scores
    payment_score: float = 0.0
    task_definition_score: float = 0.0
    requirements_score: float = 0.0
    location_score: float = 0.0
    technical_score: float = 0.0
    time_score: float = 0.0

    # Details
    reasons: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=dict)


class MercenaryFilter:
    """Aggressive filter for opportunities based on mercenary principles."""

    MIN_SCORE_THRESHOLD = 80.0

    # Score weights
    WEIGHT_VERIFIABLE_PAYMENT = 20.0
    WEIGHT_DEFINED_TASK = 20.0
    WEIGHT_NO_INTERVIEW = 15.0
    WEIGHT_NO_PORTFOLIO = 15.0
    WEIGHT_ARGENTINA_COMPATIBLE = 10.0
    WEIGHT_REAL_IT = 10.0
    WEIGHT_REASONABLE_TIME = 10.0

    def __init__(self) -> None:
        self._cache: dict[str, MercenaryScore] = {}

    def score_opportunity(
        self,
        opp_id: str,
        attributes: MercenaryAttributes,
    ) -> MercenaryScore:
        """Score an opportunity using mercenary criteria."""
        if opp_id in self._cache:
            return self._cache[opp_id]

        score = MercenaryScore(
            total_score=0.0,
            passed_filter=False,
            category=attributes.category,
            category_priority=CATEGORY_PRIORITIES.get(attributes.category, CategoryPriority.MEDIUM),
        )

        # 1. Payment score (max 20)
        if attributes.verifiable_payment:
            score.payment_score += 10.0
            score.reasons.append("Verifiable payment platform")
        if attributes.payment_amount_verified:
            score.payment_score += 5.0
            score.reasons.append("Payment amount verified")
        if attributes.payment_history_good:
            score.payment_score += 5.0
            score.reasons.append("Good payment history")

        # 2. Task definition score (max 20)
        if attributes.defined_objective:
            score.task_definition_score += 8.0
            score.reasons.append("Defined objective")
        if attributes.clear_deliverable:
            score.task_definition_score += 7.0
            score.reasons.append("Clear deliverable")
        if attributes.scope_well_defined:
            score.task_definition_score += 5.0
            score.reasons.append("Well-defined scope")

        # 3. Requirements score (max 30)
        if attributes.no_interview_required:
            score.requirements_score += 15.0
            score.reasons.append("No interview required")
        else:
            score.blockers["interview_required"] = "Interview required"
        if attributes.no_portfolio_required:
            score.requirements_score += 10.0
            score.reasons.append("No portfolio required")
        else:
            score.blockers["portfolio_required"] = "Portfolio required"
        if attributes.no_experience_required:
            score.requirements_score += 5.0
            score.reasons.append("No experience required")

        # 4. Location/compatibility score (max 10)
        if attributes.argentina_compatible:
            score.location_score += 5.0
            score.reasons.append("Argentina compatible")
        if attributes.remote_work:
            score.location_score += 3.0
            score.reasons.append("Remote work")
        if attributes.flexible_hours:
            score.location_score += 2.0
            score.reasons.append("Flexible hours")

        # 5. Technical score (max 10)
        if attributes.real_it_work:
            score.technical_score += 5.0
            score.reasons.append("Real IT work")
        if attributes.technical_skill_required:
            score.technical_score += 3.0
            score.reasons.append("Technical skill required")
        if attributes.no_mechanical_task:
            score.technical_score += 2.0
            score.reasons.append("Not mechanical task")
        else:
            score.blockers["mechanical_task"] = "Mechanical task detected"

        # 6. Time score (max 10)
        if attributes.reasonable_timeframe:
            score.time_score += 5.0
            score.reasons.append("Reasonable timeframe")
        if attributes.hourly_rate_competitive:
            score.time_score += 3.0
            score.reasons.append("Competitive hourly rate")
        if 0 < attributes.estimated_hours <= 40:
            score.time_score += 2.0
            score.reasons.append("Reasonable hours")

        # Calculate total with weights
        score.total_score = (
            score.payment_score * (self.WEIGHT_VERIFIABLE_PAYMENT / 20.0)
            + score.task_definition_score * (self.WEIGHT_DEFINED_TASK / 20.0)
            + score.requirements_score * (self.WEIGHT_NO_INTERVIEW / 15.0)
            + score.location_score * (self.WEIGHT_ARGENTINA_COMPATIBLE / 10.0)
            + score.technical_score * (self.WEIGHT_REAL_IT / 10.0)
            + score.time_score * (self.WEIGHT_REASONABLE_TIME / 10.0)
        )

        # Add category priority bonus
        priority_bonus = score.category_priority / 100.0 * 10.0
        score.total_score += priority_bonus

        # Determine if passed filter
        score.passed_filter = score.total_score >= self.MIN_SCORE_THRESHOLD

        if not score.passed_filter:
            score.reasons.append(f"Score {score.total_score:.1f} below threshold {self.MIN_SCORE_THRESHOLD}")

        # Cache
        self._cache[opp_id] = score

        logger.debug(
            "[MercenaryFilter] %s: Score=%.1f, Category=%s, Passed=%s",
            opp_id,
            score.total_score,
            attributes.category.name,
            score.passed_filter,
        )

        return score

    def get_category(self, platform: str, source_type: str, tags: list[str]) -> OpportunityCategory:
        """Determine category based on platform and metadata."""
        platform_lower = platform.lower()

        # Bug bounty platforms
        if platform_lower in {"hackerone", "bugcrowd", "intigriti", "yeswehack", "immunefi"}:
            return OpportunityCategory.BUG_BOUNTY

        # Dev bounty / OSS
        if platform_lower in {"algora", "opire", "superteam", "gitcoin", "bountysource"}:
            return OpportunityCategory.DEVELOPMENT_TASKS

        # AI evaluation
        if platform_lower in {"outlier", "dataannotation", "mindrift", "remotasks", "toloka", "scale"}:
            return OpportunityCategory.AI_EVALUATION

        # Testing/QA
        if platform_lower in {"utest", "testlio"}:
            return OpportunityCategory.TESTING_QA

        # Hackathons
        if "hackathon" in tags or "competition" in tags:
            return OpportunityCategory.HACKATHONS

        # DevOps/Cloud
        if any(tag in tags for tag in ["devops", "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd"]):
            return OpportunityCategory.DEVOPS_CLOUD

        # Data engineering
        if any(tag in tags for tag in ["data", "etl", "pipeline", "scraping", "analytics"]):
            return OpportunityCategory.DATA_ENGINEERING

        # Automation
        if any(tag in tags for tag in ["automation", "bot", "script", "api"]):
            return OpportunityCategory.ENTERPRISE_AUTOMATION

        # Game programming
        if any(tag in tags for tag in ["unity", "unreal", "gamedev", "c#", "c++"]):
            return OpportunityCategory.GAME_PROGRAMMING

        # Documentation
        if any(tag in tags for tag in ["documentation", "docs", "tutorial", "api"]):
            return OpportunityCategory.TECHNICAL_DOCUMENTATION

        # Default
        return OpportunityCategory.DEVELOPMENT_TASKS

    def clear_cache(self) -> None:
        """Clear the scoring cache."""
        self._cache.clear()
        logger.debug("[MercenaryFilter] Cache cleared")


_global_filter: MercenaryFilter | None = None


def get_mercenary_filter() -> MercenaryFilter:
    global _global_filter
    if _global_filter is None:
        _global_filter = MercenaryFilter()
        logger.info("MercenaryFilter initialized")
    return _global_filter
