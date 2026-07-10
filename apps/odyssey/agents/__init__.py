"""ODYSSEY Agents — AI-powered betting intelligence agent.

No automated betting — analytical suggestions only.
"""

from __future__ import annotations

import logging

from core.ai.runtime import AIRuntime

logger = logging.getLogger("orion.odyssey.agents")


class OdysseyBettingAgent:
    """ODYSSEY betting intelligence agent.

    Analyzes markets, recommends EV+ bets, tracks performance.
    User must confirm all bets manually.
    """

    def __init__(self, runtime: AIRuntime | None = None) -> None:
        self.runtime = runtime
