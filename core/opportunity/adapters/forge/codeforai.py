"""CodeForAI adapter — paid AI-training coding work.

CodeForAI (codeforai.tech) is a hiring funnel, not a task board: developers
apply once, then receive paid tasks ($45/h advertised, payouts twice a
month, remote worldwide, no interview). There is no public jobs API — the
adapter emits the single verified opportunity (the trainer role itself)
so it appears in discovery/ranking with real terms instead of being
invisible. Eligibility stays UNKNOWN until the user applies.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ownex.adapters.forge.codeforai")

ROLE_URL = "https://codeforai.tech/register"


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Return the verified CodeForAI trainer opportunity."""
    return [
        {
            "id": "codeforai_ai_code_trainer",
            "name": "CodeForAI — AI Code Trainer ($45/h)",
            "description": (
                "Paid remote work training AI models to write better code: "
                "review model responses, fix errors, explain corrections. "
                "Advertised rate $45/hour, payouts twice a month, remote "
                "worldwide, no CV or interview — apply and get a decision "
                "within 3 business days."
            ),
            "platform": "codeforai",
            "url": ROLE_URL,
            "reward": 45.0,
            "effort_hours": 10.0,
            "tags": ["ai-training", "code-review", "remote", "contractor"],
            "cycle": "forge",
            "source_type": "ai_work",
            "source_name": "codeforai",
            "metadata": {
                "original": {
                    "hourly_rate_usd": 45.0,
                    "payout_frequency": "twice_monthly",
                    "eligibility": "UNKNOWN",
                    "notes": "Application funnel — no public task API. Verify Argentina payout eligibility after applying.",
                }
            },
            "created_at": "",
        }
    ]
