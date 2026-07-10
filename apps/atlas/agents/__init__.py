"""ATLAS Agents — AI-powered investment agent.

Uses ORION AI Runtime for decision making.
"""

from __future__ import annotations

import logging

from core.ai.runtime import AIRuntime

logger = logging.getLogger("orion.atlas.agents")


class AtlasInvestorAgent:
    """ATLAS investment agent — rebalance suggestions, risk alerts.

    TODO: connect to ORION's AIRuntime for autonomous portfolio management.
    """

    def __init__(self, runtime: AIRuntime | None = None) -> None:
        self.runtime = runtime
