"""DeFi Yield Tracker — monitor yield positions, track APY, compound strategy.

Provides:
- Position tracking across DeFi protocols
- APY monitoring via DefiLlama + on-chain
- Compounding strategy simulation
- Event bus integration for yield events
"""

from __future__ import annotations

from core.defi.positions import DefiPosition, ProtocolInfo, YieldSnapshot
from core.defi.strategy import CompoundStrategy, StrategyProjection
from core.defi.yield_tracker import DefiYieldTracker

__all__ = [
    "CompoundStrategy",
    "DefiPosition",
    "DefiYieldTracker",
    "ProtocolInfo",
    "StrategyProjection",
    "YieldSnapshot",
]
