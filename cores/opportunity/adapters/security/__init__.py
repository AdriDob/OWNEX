"""Security cycle adapters for major bug bounty platforms.

This module provides adapters for:
- HackerOne (largest platform, API + GraphQL)
- Bugcrowd (second largest, REST API)
- Intigriti (European platform, REST API)
- YesWeHack (European platform, REST API)
- Immunefi (Web3/crypto focus, REST API)
- Synack (invite-only, special handling)
"""

from __future__ import annotations

from core.opportunity.adapters.security.bugcrowd import BugcrowdAdapter
from core.opportunity.adapters.security.hackerone import HackerOneAdapter
from core.opportunity.adapters.security.immunefi import ImmunefiAdapter
from core.opportunity.adapters.security.intigriti import IntigritiAdapter
from core.opportunity.adapters.security.synack import SynackAdapter
from core.opportunity.adapters.security.yeswehack import YesWeHackAdapter

__all__ = [
    "HackerOneAdapter",
    "BugcrowdAdapter",
    "IntigritiAdapter",
    "YesWeHackAdapter",
    "ImmunefiAdapter",
    "SynackAdapter",
]
