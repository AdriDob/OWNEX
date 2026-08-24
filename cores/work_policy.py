"""Category business-priority policy — SEPARATE from taxonomy identity.

The canonical ``OpportunityCategory`` defines WHAT a piece of work IS.
This module defines how much BUSINESS ATTENTION it deserves right now,
so priorities can evolve without touching the taxonomy (and vice versa).

Evidence rules (nothing invented):
- HIGH: categories on the owner's current business-priority list.
- Inherited: curated ``CATEGORY_PRIORITIES`` from the mercenary filter,
  mapped to canonical families via ``cores.work_taxonomy`` (EXTREME/VERY_
  HIGH/HIGH -> HIGH; MEDIUM_HIGH/MEDIUM -> MEDIUM).
- Everything else: LOW with an explicit no-evidence rationale.

Adding evidence sources later means adding seed blocks here — never
editing the Enum, never scattering ifs across engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cores.direct_work_engine.models import OpportunityCategory
from cores.work_taxonomy import MERCENARY_TO_CANONICAL

__all__ = ["CategoryPriority", "PolicySource", "CategoryProfile", "policy_for", "priority_for"]


class CategoryPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PolicySource(StrEnum):
    OWNER_PRIORITY_LIST = "owner_priority_list"
    MERCENARY_CURATED = "mercenary_curated"
    DEFAULT_NO_EVIDENCE = "default_no_evidence"


#: Owner's stated focus (2026-08 product direction).
_OWNER_PRIORITY: frozenset[OpportunityCategory] = frozenset(
    {
        OpportunityCategory.DATA_ANNOTATION,
        OpportunityCategory.AI_EVALUATION,
        OpportunityCategory.BUG_BOUNTY,
        OpportunityCategory.DEV_BOUNTY,
        OpportunityCategory.PROMPT_ENGINEERING,
        OpportunityCategory.TECHNICAL_WRITING,
        OpportunityCategory.CODE_REVIEW,
        OpportunityCategory.QA_AUTOMATION,
    }
)

#: Curated mercenary priorities, translated to canonical families.
_MERCENARY_RANK: dict[str, int] = {
    "EXTREME": 3,
    "VERY_HIGH": 3,
    "HIGH": 3,
    "MEDIUM_HIGH": 2,
    "MEDIUM": 2,
    "LOW": 1,
}


@dataclass(frozen=True)
class CategoryProfile:
    """Business posture of one canonical category. Identity lives in the Enum."""

    category: OpportunityCategory
    priority: CategoryPriority
    source: PolicySource
    rationale: str


def _build_profiles() -> dict[OpportunityCategory, CategoryProfile]:
    inherited: dict[OpportunityCategory, int] = {}
    from core.opportunity.mercenary_filter import CATEGORY_PRIORITIES

    for legacy_member, legacy_priority in CATEGORY_PRIORITIES.items():
        canonical = MERCENARY_TO_CANONICAL[legacy_member]
        rank = _MERCENARY_RANK.get(legacy_priority.name, 0)
        inherited[canonical] = max(inherited.get(canonical, 0), rank)

    profiles: dict[OpportunityCategory, CategoryProfile] = {}
    for member in OpportunityCategory:
        if member in _OWNER_PRIORITY:
            profiles[member] = CategoryProfile(
                category=member,
                priority=CategoryPriority.HIGH,
                source=PolicySource.OWNER_PRIORITY_LIST,
                rationale="Owner's current business-priority list.",
            )
        elif inherited.get(member, 0) >= 3:
            profiles[member] = CategoryProfile(
                category=member,
                priority=CategoryPriority.HIGH,
                source=PolicySource.MERCENARY_CURATED,
                rationale="Inherited HIGH/EXTREME from curated mercenary priorities.",
            )
        elif inherited.get(member, 0) == 2:
            profiles[member] = CategoryProfile(
                category=member,
                priority=CategoryPriority.MEDIUM,
                source=PolicySource.MERCENARY_CURATED,
                rationale="Inherited MEDIUM/MEDIUM_HIGH from curated mercenary priorities.",
            )
        else:
            profiles[member] = CategoryProfile(
                category=member,
                priority=CategoryPriority.LOW,
                source=PolicySource.DEFAULT_NO_EVIDENCE,
                rationale="No curated evidence yet; revisit as discovery data grows.",
            )
    return profiles


_CATEGORY_PROFILES: dict[OpportunityCategory, CategoryProfile] = _build_profiles()


def policy_for(category: OpportunityCategory) -> CategoryProfile:
    """Deterministic business profile for any canonical category."""
    return _CATEGORY_PROFILES[category]


def priority_for(category: OpportunityCategory) -> CategoryPriority:
    return policy_for(category).priority
