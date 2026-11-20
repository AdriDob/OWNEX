"""Kaggle Adapter — Data science & annotation platform integration.

Integrates with Kaggle API for data science and annotation opportunities.
Supports competition participation, dataset publishing, and annotation tasks.
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class KaggleAdapter(OpportunityAdapter):
    """Adapter for Kaggle platform."""

    platform: str = "kaggle"
    cycle: str = "kaggle"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch opportunities from Kaggle API."""
        try:
            credentials = load_credentials("kaggle")
            get_api_key("kaggle", credentials)

            # Kaggle API via HTTPS for dataset/listings and competition opportunities
            base_url = "https://kaggle.com/api/v1/"

            headers = get_auth_headers("kaggle", credentials)

            async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                # List competitions ( Kaggle competitions)
                comp_response = await client.get(
                    base_url + "competitions",
                    params={"status": "active"},
                    timeout=30.0,
                )

                if comp_response.status_code != 200:
                    competitions = []
                else:
                    competitions = comp_response.json().get("competitions", [])

                raw_opps: list[RawOpportunity] = []

                for comp in competitions[:15]:  # Limit to recent 15 competitions
                    raw_opps.append(
                        RawOpportunity(
                            id=f"kaggle_{comp.get('id', '')}",
                            name=comp.get("title", "Kaggle Competition"),
                            description=comp.get("description", "") or comp.get("title", ""),
                            platform="kaggle",
                            url=comp.get("competitionUrl", ""),
                            reward=float(comp.get("prizeMoney", 0) or 0),
                            effort_hours=float(comp.get("timeCommitment", 20) or 10.0),
                            tags=[comp.get("keywords", "")] or [],
                            cycle="kaggle",
                            source_type="data_science",
                            source_name="kaggle",
                            metadata={"original": comp, "personal": None},
                            created_at=comp.get("lastUpdated", ""),
                        )
                    )

                # Also check datasets for annotation opportunities
                try:
                    ded_response = await client.get(
                        base_url + "datasets/list",
                        params={"sortBy": "lastUpdated", "search": "annotation"},
                        timeout=30.0,
                    )
                    if ded_response.status_code == 200:
                        datasets = ded_response.json().get("datasetSummaries", [])
                        for ds in datasets[:10]:
                            raw_opps.append(
                                RawOpportunity(
                                    id=f"kaggle_ds_{ds.get('id', '')}",
                                    name=ds.get("title", "Kaggle Dataset"),
                                    description=ds.get("description", "") or ds.get("title", ""),
                                    platform="kaggle",
                                    url=ds.get("url", ""),
                                    reward=0.0,  # Datasets typically don't have monetary rewards
                                    effort_hours=float(ds.get("hoursToCompletion", 5) or 3.0),
                                    tags=[ds.get("tags", "")] or [],
                                    cycle="kaggle",
                                    source_type="data_annotation",
                                    source_name="kaggle",
                                    metadata={"original": ds, "personal": None},
                                    created_at=ds.get("lastUpdated", ""),
                                )
                            )
                except Exception:
                    pass  # Datasets list optional

                return raw_opps

        except Exception:
            # Log error but don't fail - adapter resilience
            return []
