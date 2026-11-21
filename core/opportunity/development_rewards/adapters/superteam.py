"""Superteam Earn Adapter — Development bounties and grants.

Platform: superteam.sh
Categories: development, backend, web3, AI
Payout: USDC, crypto
Argentina: Has regional page, supports Argentina users
"""

from __future__ import annotations

from typing import Any

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity
import httpx


class SuperteamEarnAdapter(OpportunityAdapter):
    """Superteam Earn adapter — development bounties and grants."""

    platform: str = "superteam"
    cycle: str = "forge"
    reward_currency: str = "USDC"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("superteam", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Superteam opportunities."""
        try:
            config = self.config or {}

            # Try direct work engine first
            from core.opportunity.source_discovery import _is_argentina_compatible

            # Fetch from Superteam API or use curated fallback
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.superteam.sh/v1/opportunities",
                    timeout=15,
                )

            if resp.status_code != 200:
                # Fallback to curated data
                from core.opportunity.development_rewards.adapters.superteam import (
                    classify_opportunity,
                    DevelopmentRewardType,
                )

                fallback_data = [
                    {
                        "id": "superteam_task_1",
                        "name": "Superteam Task Example",
                        "description": "Example superteam opportunity",
                        "url": "https://superteam.com",
                        "reward": 100.0,
                        "effort_hours": 5.0,
                        "tags": ["superteam", "task-based"],
                        "category": "dev_bounty",
                        "specialization": "backend",
                        "remote": True,
                    }
                ]
                raw_opps: list[RawOpportunity] = []
                for item in fallback_data:
                    raw_opps.append(
                        RawOpportunity(
                            id=item["id"],
                            name=item["name"],
                            description=item["description"],
                            platform=item["platform"],
                            url=item["url"],
                            reward=item["reward"],
                            effort_hours=item["effort_hours"],
                            tags=item["tags"],
                            specialization=item.get("specialization", "backend"),
                            remote=item.get("remote", True),
                            reward_currency="USD",
                            reward_status="REPORTED",
                            source_type="direct_bounty",
                            source_name="superteam",
                            metadata={"original": item},
                        )
                    )
                return raw_opps

            data = resp.json()
            opportunities = data.get("opportunities", data.get("data", []))

            raw_opps: list[RawOpportunity] = []
            for opp in opportunities[:20]:
                raw_opps.append(
                    RawOpportunity(
                        id=f"superteam_{opp.get('id')}",
                        name=opp.get("title") or "Superteam Opportunity",
                        description=opp.get("description") or "",
                        platform="superteam",
                        url=opp.get("url"),
                        reward=float(opp.get("reward", 0)),
                        effort_hours=float(opp.get("estimated_hours", 5)),
                        tags=opp.get("tags", ["superteam"]),
                        specialization=opp.get("specialization", "backend"),
                        remote=opp.get("remote", True),
                        reward_currency=opp.get("currency", "USDC"),
                        reward_status=opp.get("payment_status", "REPORTED"),
                        source_type="dev_bounty",
                        source_name="superteam",
                        metadata={"original": opp},
                    )
                )

            return raw_opps

        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning(
                "SuperteamEarnAdapter fetch failed: %s", e
            )

            # Return curated fallback
            from core.opportunity.development_rewards.adapters.superteam import (
                classify_opportunity,
                DevelopmentRewardType,
            )

            fallback_data = [
                {
                    "id": "superteam_task_1",
                    "name": "Superteam Task Example",
                    "description": "Example superteam opportunity",
                    "url": "https://superteam.com",
                    "reward": 100.0,
                    "effort_hours": 5.0,
                    "tags": ["superteam", "task-based"],
                    "category": "dev_bounty",
                    "specialization": "backend",
                    "remote": True,
                }
            ]
            raw_opps: list[RawOpportunity] = []
            for item in fallback_data:
                raw_opps.append(
                    RawOpportunity(
                        id=item["id"],
                        name=item["name"],
                        description=item["description"],
                        platform=item["platform"],
                        url=item["url"],
                        reward=item["reward"],
                        effort_hours=item["effort_hours"],
                        tags=item["tags"],
                        specialization=item.get("specialization", "backend"),
                        remote=item.get("remote", True),
                        reward_currency="USD",
                        reward_status="REPORTED",
                        source_type="direct_bounty",
                        source_name="superteam",
                        metadata={"original": item},
                    )
                )
            return raw_opps