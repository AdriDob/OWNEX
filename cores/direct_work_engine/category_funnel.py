"""Category Funnel Registry — Declarative funnels for all economic categories.

This is the SINGLE SOURCE OF TRUTH for category funnels.
Every category MUST declare its funnel here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cores.direct_work_engine.probability_contract import (
    CategoryFunnel,
    ProbabilityType,
    get_funnel,
    get_funnel as _get_funnel,
    get_all_funnels,
    get_categories_with_funnels,
    get_probability_types_for_category,
    get_stages_for_category,
    register_funnel,
)

# Re-export for backward compatibility
__all__ = [
    "CategoryFunnel",
    "ProbabilityType",
    "get_funnel",
    "get_all_funnels",
    "get_categories_with_funnels",
    "get_probability_types_for_category",
    "get_stages_for_category",
    "register_funnel",
]

# Funnels are registered in probability_contract.py at module import time.
# This module re-exports the registry API.
