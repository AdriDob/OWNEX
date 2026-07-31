"""ODYSSEY — provider package.

Provides the ``KellyProvider`` calculator and the registered connector IDs.
"""

from __future__ import annotations

from apps.odyssey.providers.kelly import KellyProvider

PROVIDERS: list[str] = [
    "odyssey/polymarket",
    "odyssey/the_odds_api",
    "odyssey/betfair",
    "odyssey/csv",
]

__all__ = ["PROVIDERS", "KellyProvider"]
