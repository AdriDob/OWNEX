"""Gitpay Adapter — GitHub-funded bounties with Whop payouts.

Platform: gitpay.io
Opportunities: Funded GitHub issues, PR acceptance bounties
Payout: Whop (bank, PayPal, crypto depending on country)
Argentina: Needs verification — may use crypto or PayPal
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class GitpayAdapter(OpportunityAdapter):
    """Gitpay adapter — GitHub-funded bounties with Whop payouts."""

    platform: str = "gitpay"
    cycle: str = "forge"
    reward_currency: str = "USD"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("gitpay", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch funded GitHub bounties from Gitpay."""
        try:
            config = self.config or {}
            api_key = config.get("api_key") or config.get("key")

            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.gitpay.io/v1/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:30]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"gitpay_{bounty.get('id')}",
                            name=bounty.get("title") or "Gitpay Bounty",
                            description=bounty.get("description") or "",
                            platform="gitpay",
                            url=bounty.get("url"),
                            reward=float(bounty.get("amount", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 4)),
                            tags=bounty.get("labels", ["github", "bounty"]),
                            specialization=bounty.get("specialization", "backend"),
                            remote=bounty.get("remote", True),
                            reward_currency=bounty.get("currency", "USD"),
                            reward_status=bounty.get("payment_status", "REPORTED"),
                            source_type="dev_bounty",
                            source_name="gitpay",
                            metadata={"original": bounty},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("GitpayAdapter fetch failed: %s", e)
            return []
