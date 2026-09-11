"""Category Funnel Registry — Declarative funnels for all economic categories.

This is the SINGLE SOURCE OF TRUTH for category funnels.
Every category MUST declare its funnel here.
"""

from __future__ import annotations

from cores.direct_work_engine.probability_contract import (
    CategoryFunnel,
    ProbabilityType,
    get_all_funnels,
    get_categories_with_funnels,
    get_funnel,
    get_probability_types_for_category,
    get_stages_for_category,
    register_funnel,
)

# Re-export for backward compatibility
__all__ = [
    "CategoryFunnel",
    "ProbabilityType",
    "STREAM_TO_FUNNEL",
    "funnel_for_category",
    "get_funnel",
    "get_all_funnels",
    "get_categories_with_funnels",
    "get_probability_types_for_category",
    "get_stages_for_category",
    "register_funnel",
]

# Funnels are registered in probability_contract.py at module import time.
# This module re-exports the registry API.


def _stream_to_funnel_map() -> dict[str, str]:
    """WorkStream value -> funnel category. Lazy import: models.py must never
    import this module (one-way dependency funnel -> models)."""
    from cores.direct_work_engine.models import WorkStream

    return {
        WorkStream.BUG_BOUNTY.value: "bug_bounty",
        WorkStream.DEV_BOUNTY.value: "dev_bounty",
        WorkStream.AI_WORK.value: "ai_training",
        WorkStream.GAME_DEV.value: "dev_bounty",
        WorkStream.OPEN_SOURCE.value: "dev_bounty",
        # Tech-content deliverables (writing/docs/review) close like client work:
        # lead -> proposal -> delivery -> payment.
        WorkStream.TECH_CONTENT.value: "client_work",
    }


# Canonical map: WorkStream -> funnel (built lazily, see above).
STREAM_TO_FUNNEL: dict[str, str] = {}


def funnel_for_category(category: object) -> str:
    """Map an OpportunityCategory (or its raw value) onto a funnel name.

    Unknown/unmapped categories return "" (never invent a funnel).
    """
    from cores.direct_work_engine.models import CATEGORY_TO_STREAM

    global STREAM_TO_FUNNEL
    if not STREAM_TO_FUNNEL:
        STREAM_TO_FUNNEL = _stream_to_funnel_map()
    key = getattr(category, "value", category)
    # Direct hit: caller already holds a WorkStream value or a funnel name.
    if isinstance(key, str) and key in STREAM_TO_FUNNEL:
        return STREAM_TO_FUNNEL[key]
    # Employment has no WorkStream (it's hired labor, not a work stream):
    # it maps straight onto the employment funnel.
    if key == "employment":
        return "employment"
    for cat, stream in CATEGORY_TO_STREAM.items():
        if getattr(cat, "value", cat) == key:
            stream_val = getattr(stream, "value", stream)
            return STREAM_TO_FUNNEL.get(stream_val, "")
    return ""
