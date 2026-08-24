"""Single Source of Truth for work-category taxonomies across engines.

The system has several local ``OpportunityCategory`` enums, one per engine
layer. Each layer legitimately models its own granularity, but they must map
onto ONE product taxonomy: ``cores.direct_work_engine.models.OpportunityCategory``
(the 38-category canonical set used by scoring, career planning and reporting).

This module declares the explicit, exhaustive mappings between every engine
taxonomy and the canonical one. Tests enforce exhaustiveness: adding a member
to a local enum without registering its canonical equivalent fails CI.

Mapping policy: exact matches map directly; approximate matches map to the
closest canonical family with the rationale documented inline. Mappings are
total but NOT injective (two local categories may share a canonical target).
"""

from __future__ import annotations

from core.opportunity.mercenary_filter import OpportunityCategory as MercenaryCategory
from cores.direct_work_engine.models import OpportunityCategory
from cores.opportunity.engine import OpportunityCategory as EngineOpportunityCategory
from cores.opportunity.global_sources import OpportunityCategory as GlobalSourceCategory

__all__ = [
    "OpportunityCategory",
    "EngineOpportunityCategory",
    "GlobalSourceCategory",
    "MercenaryCategory",
    "ENGINE_TO_CANONICAL",
    "GLOBAL_SOURCE_TO_CANONICAL",
    "MERCENARY_TO_CANONICAL",
    "to_canonical",
]

# cores.opportunity.engine (11 categories) -> canonical
ENGINE_TO_CANONICAL: dict[EngineOpportunityCategory, OpportunityCategory] = {
    EngineOpportunityCategory.BUG_BOUNTY: OpportunityCategory.BUG_BOUNTY,
    EngineOpportunityCategory.DEV_BOUNTY: OpportunityCategory.DEV_BOUNTY,
    # Freelance technical work without a hiring process ≈ general engineering.
    EngineOpportunityCategory.FREELANCE_TECH: OpportunityCategory.SOFTWARE_ENGINEERING,
    EngineOpportunityCategory.DATA_ANNOTATION: OpportunityCategory.DATA_ANNOTATION,
    # HIT-style microtasks: the dominant microtask supply OWNEX sources is
    # AI-training annotation work (Outlier/Mercor/Mindrift family).
    EngineOpportunityCategory.MICROTASKS: OpportunityCategory.DATA_ANNOTATION,
    EngineOpportunityCategory.TESTING_QA: OpportunityCategory.QA_AUTOMATION,
    EngineOpportunityCategory.OPEN_SOURCE: OpportunityCategory.OPEN_SOURCE,
    EngineOpportunityCategory.AI_EVALUATION: OpportunityCategory.AI_EVALUATION,
    # Building/selling APIs ≈ the API development family.
    EngineOpportunityCategory.API_MARKETPLACE: OpportunityCategory.API_DEVELOPMENT,
    # No dedicated products category canonically; engineering output is the
    # closest family (templates, tools, digital assets built as software).
    EngineOpportunityCategory.DIGITAL_PRODUCTS: OpportunityCategory.SOFTWARE_ENGINEERING,
    EngineOpportunityCategory.TECH_CHALLENGES: OpportunityCategory.COMPETITIONS,
}

# cores.opportunity.global_sources (3 curated source families) -> canonical
GLOBAL_SOURCE_TO_CANONICAL: dict[GlobalSourceCategory, OpportunityCategory] = {
    GlobalSourceCategory.bug_bounty: OpportunityCategory.BUG_BOUNTY,
    GlobalSourceCategory.dev_bounty: OpportunityCategory.DEV_BOUNTY,
    # Entry-level data work ≈ annotation family.
    GlobalSourceCategory.data_entry: OpportunityCategory.DATA_ANNOTATION,
}

# core.opportunity.mercenary_filter (11 prioritized categories) -> canonical
MERCENARY_TO_CANONICAL: dict[MercenaryCategory, OpportunityCategory] = {
    MercenaryCategory.BUG_BOUNTY: OpportunityCategory.BUG_BOUNTY,
    MercenaryCategory.DEVELOPMENT_TASKS: OpportunityCategory.SOFTWARE_ENGINEERING,
    MercenaryCategory.TESTING_QA: OpportunityCategory.QA_AUTOMATION,
    MercenaryCategory.AI_EVALUATION: OpportunityCategory.AI_EVALUATION,
    MercenaryCategory.GAME_PROGRAMMING: OpportunityCategory.GAME_DEVELOPMENT,
    # Enterprise automation work lives in the browser-automation family.
    MercenaryCategory.ENTERPRISE_AUTOMATION: OpportunityCategory.BROWSER_AUTOMATION,
    MercenaryCategory.DATA_ENGINEERING: OpportunityCategory.DATA_ENGINEERING,
    # devops_cloud spans both canonical families; DevOps is the primary.
    MercenaryCategory.DEVOPS_CLOUD: OpportunityCategory.DEVOPS,
    MercenaryCategory.TECHNICAL_DOCUMENTATION: OpportunityCategory.TECHNICAL_WRITING,
    MercenaryCategory.HACKATHONS: OpportunityCategory.COMPETITIONS,
    # Funded open-source work ≈ bounties paid on OSS repositories.
    MercenaryCategory.FUNDED_OPEN_SOURCE: OpportunityCategory.OSS_BOUNTIES,
}


def to_canonical(
    category: (EngineOpportunityCategory | GlobalSourceCategory | MercenaryCategory | OpportunityCategory),
) -> OpportunityCategory:
    """Convert any engine-layer category to its canonical equivalent."""
    if isinstance(category, OpportunityCategory):
        return category
    if isinstance(category, EngineOpportunityCategory):
        return ENGINE_TO_CANONICAL[category]
    if isinstance(category, GlobalSourceCategory):
        return GLOBAL_SOURCE_TO_CANONICAL[category]
    if isinstance(category, MercenaryCategory):
        return MERCENARY_TO_CANONICAL[category]
    raise ValueError(f"Unknown opportunity category type: {type(category).__name__}")
