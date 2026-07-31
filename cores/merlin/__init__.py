"""MERLIN — Office Retro Modernized Assistant for OWNEX OMEGA.

MERLIN is a sophisticated AI assistant with a retro-futuristic Office 97-inspired
personality, modernized with advanced capabilities for bug bounty, cybersecurity,
and intelligence operations.

The Assistant consumes Core Services (EventBus, Decision Journal, Memory, System State)
through their public interfaces. It never accesses apps directly.
"""

from __future__ import annotations

from cores.merlin.config import MerlinConfig
from cores.merlin.memory import MerlinMemory
from cores.merlin.personality import MerlinPersonality
from cores.merlin.system import MerlinSystem

__all__ = [
    "MerlinSystem",
    "MerlinMemory",
    "MerlinPersonality",
    "MerlinConfig",
]
