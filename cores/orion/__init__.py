"""CATEYE Context Engine — aggregation and decision layer.

Reads existing system data and returns unified context, next actions,
and opportunity analysis. Never modifies pipeline data or DB.
"""

from cores.orion.context_engine import get_context
from cores.orion.next_action import get_next_action
from cores.orion.opportunity_analyzer import analyze_opportunity

__all__ = ["get_context", "get_next_action", "analyze_opportunity"]
