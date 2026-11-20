"""Upwork Adapter — Freelance platform integration.

Integrates with Upwork API for remote opportunity discovery.
Supports OAuth 2.0 authentication and freelance/bounty posting.
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class UpworkAdapter(OpportunityAdapter):
    """Adapter for Upwork freelance platform."""

    platform: str = "upwork"
    cycle: str = "upwork"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch opportunities from Upwork API."""
        try:
            credentials = load_credentials("upwork")
            get_api_key("upwork", credentials)

            headers = get_auth_headers("upwork", credentials)

            # Upwork API v2 endpoint for opportunities
            base_url = "https://www.upwork.com/api/v2/jobs"
            params = {
                "apiversion": "2.0",
                "client": "default",
                "category": " it & software",  # Could be parameterized
                "budget_min": "0",
                "budget_max": "10000",
                "sort": "posts",
                "keywords": "remote",
            }

            async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                response = await client.get(base_url, params=params)
                if response.status_code != 200:
                    return []

                data = response.json()
                jobs = data.get("jobs", data.get("results", []))

                raw_opps: list[RawOpportunity] = []
                for job in jobs[:20]:  # Limit to recent 20 jobs
                    raw_opps.append(
                        RawOpportunity(
                            id=f"upwork_{job.get('job_id', job.get('id', ''))}",
                            name=job.get("title", "Upwork Project"),
                            description=job.get("description", "") or job.get("title", ""),
                            platform="upwork",
                            url=job.get("alternate_link", job.get("url", "")),
                            reward=float(job.get("budget", job.get("price", 0)) or 0),
                            effort_hours=float(job.get("estimated_hours", 10) or 4.0),
                            tags=job.get("tags", []) or [],
                            cycle="upwork",
                            source_type="freelance",
                            source_name="upwork",
                            metadata={"original": job, "personal": None},
                            created_at=job.get("created_at", ""),
                        )
                    )

                return raw_opps

        except Exception:
            # Log error but don't fail - adapter resilience
            return []
