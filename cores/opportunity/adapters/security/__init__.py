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

from cores.opportunity.adapters.security.bugcrowd import BugcrowdAdapter
from cores.opportunity.adapters.security.code4rena import Code4renaAdapter
from cores.opportunity.adapters.security.hackerone import HackerOneAdapter
from cores.opportunity.adapters.security.immunefi import ImmunefiAdapter
from cores.opportunity.adapters.security.intigriti import IntigritiAdapter
from cores.opportunity.adapters.security.sherlock import SherlockAdapter
from cores.opportunity.adapters.security.synack import SynackAdapter
from cores.opportunity.adapters.security.yeswehack import YesWeHackAdapter

__all__ = [
    "HackerOneAdapter",
    "BugcrowdAdapter",
    "IntigritiAdapter",
    "YesWeHackAdapter",
    "ImmunefiAdapter",
    "SynackAdapter",
    "SherlockAdapter",
    "Code4renaAdapter",
]
