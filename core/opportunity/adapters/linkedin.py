"""LinkedIn Adapter — Job search (Forge) and Easy Apply micro-applications (Pulse)."""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class LinkedInJobsAdapter(OpportunityAdapter):
    """LinkedIn Jobs adapter - contract/freelance roles, entry-level friendly (Forge cycle)."""

    platform: str = "linkedin"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("linkedin", config)
        super().__init__(merged_config)
        self.api_key = self.config.get("api_key")
        self.urn = self.config.get("urn")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch jobs/contracts from LinkedIn (uses curated fallback since API is restricted)."""
        try:
            return self._get_curated_direct_work()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("LinkedInJobsAdapter fetch failed: %s", e)
            return self._get_curated_direct_work()

    def _get_curated_direct_work(self) -> list[RawOpportunity]:
        """Curated search URLs for direct-work-friendly LinkedIn opportunities."""
        fallback_data = [
            {
                "id": "linkedin_freelance_no_portfolio",
                "name": "Freelance/Contract Software Developer (No Portfolio Required)",
                "description": "Multiple contract roles on LinkedIn tagged 'no portfolio required' or 'entry level welcome'",
                "url": "https://www.linkedin.com/jobs/search/?keywords=freelance%20software%20developer%20no%20portfolio&f_WT=2",
                "reward": 3000.0,
                "effort_hours": 40.0,
                "tags": ["freelance", "contract", "remote", "entry_level"],
                "source_type": "direct_employment",
                "source_name": "linkedin",
            },
            {
                "id": "linkedin_junior_remote_contract",
                "name": "Junior/Entry Level Remote Contracts",
                "description": "Contract roles explicitly welcoming beginners and self-taught developers",
                "url": "https://www.linkedin.com/jobs/search/?keywords=junior%20remote%20contract&f_WT=2&f_E=1,2",
                "reward": 2500.0,
                "effort_hours": 40.0,
                "tags": ["junior", "remote", "contract", "entry_level"],
                "source_type": "direct_employment",
                "source_name": "linkedin",
            },
            {
                "id": "linkedin_apprentice_trainee",
                "name": "Apprentice/Trainee Software Roles",
                "description": "Paid apprenticeship and trainee programs on LinkedIn",
                "url": "https://www.linkedin.com/jobs/search/?keywords=apprentice%20trainee%20software&f_E=1",
                "reward": 2000.0,
                "effort_hours": 40.0,
                "tags": ["apprentice", "trainee", "mentorship", "entry_level"],
                "source_type": "direct_employment",
                "source_name": "linkedin",
            },
        ]

        raw_opps: list[RawOpportunity] = []
        for item in fallback_data:
            raw_opps.append(
                RawOpportunity(
                    id=item["id"],
                    name=item["name"],
                    description=item["description"],
                    platform="linkedin",
                    url=item["url"],
                    reward=item["reward"],
                    effort_hours=item["effort_hours"],
                    tags=item["tags"],
                    cycle="forge",
                    source_type=item["source_type"],
                    source_name=item["source_name"],
                    metadata={},
                    created_at="",
                )
            )

        return raw_opps


class LinkedInEasyApplyAdapter(OpportunityAdapter):
    """LinkedIn Easy Apply adapter — ultra-low-effort job applications (Pulse cycle)."""

    platform: str = "linkedin_easyapply"
    cycle: str = "pulse"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("linkedin", config)
        super().__init__(merged_config)
        self.li_at_cookie = self.config.get("li_at_cookie") or self.config.get("li_at")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Easy Apply jobs from LinkedIn (entry-level, remote, no portfolio required)."""
        try:
            import re

            from bs4 import BeautifulSoup

            params = {
                "keywords": "entry level junior remote",
                "f_AL": "true",
                "f_E": "1,2",
                "f_WT": "2",
                "f_TPR": "r604800",
                "position": 1,
                "pageNum": 0,
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Cookie": f"li_at={self.li_at_cookie}" if self.li_at_cookie else "",
            }

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                    params=params,
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return self._get_easy_apply_fallback()

                soup = BeautifulSoup(resp.text, "html.parser")
                job_cards = soup.find_all("li", class_="job-search-card")

                raw_opps: list[RawOpportunity] = []
                for card in job_cards[:15]:
                    job_id = card.get("data-entity-urn", "")
                    if job_id:
                        job_id = str(job_id).split(":")[-1]

                    title_elem = card.find("h3", class_="base-search-card__title")
                    company_elem = card.find("h4", class_="base-search-card__subtitle")
                    location_elem = card.find("span", class_="job-search-card__location")
                    link_elem = card.find("a", class_="base-card__full-link")

                    # Check for Easy Apply badge
                    easy_apply = card.find("span", string=re.compile(r"Easy Apply", re.I))

                    if not easy_apply:
                        continue

                    raw_opps.append(
                        RawOpportunity(
                            id=f"linkedin_easy_{job_id}",
                            name=f"[Easy Apply] {title_elem.get_text(strip=True) if title_elem else 'LinkedIn Job'}",
                            description=f"Company: {company_elem.get_text(strip=True) if company_elem else 'Unknown'}. Location: {location_elem.get_text(strip=True) if location_elem else 'Remote'}",
                            platform="linkedin_easyapply",
                            url=str(link_elem.get("href")) if link_elem and link_elem.get("href") else None,
                            reward=0.0,
                            effort_hours=0.5,
                            tags=["easy_apply", "entry_level", "remote", "quick_apply"],
                            cycle="pulse",
                            source_type="job_application",
                            source_name="linkedin_easyapply",
                            metadata={"original": {"job_id": job_id}},
                            created_at="",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("LinkedInEasyApplyAdapter fetch failed: %s", e)
            return self._get_easy_apply_fallback()

    def _get_easy_apply_fallback(self) -> list[RawOpportunity]:
        """Fallback curated Easy Apply search URLs."""
        fallback_data = [
            {
                "id": "linkedin_easy_fallback_1",
                "name": "[Easy Apply] Junior Remote Software Roles",
                "description": "Entry-level remote positions with Easy Apply - no portfolio required",
                "url": "https://www.linkedin.com/jobs/search/?keywords=junior%20remote&f_AL=true&f_E=1,2&f_WT=2",
                "reward": 0.0,
                "effort_hours": 0.5,
                "tags": ["easy_apply", "junior", "remote", "entry_level"],
                "source_type": "job_application",
                "source_name": "linkedin_easyapply",
            },
            {
                "id": "linkedin_easy_fallback_2",
                "name": "[Easy Apply] Contract/Freelance Quick Apply",
                "description": "Contract roles with Easy Apply - minimal effort to apply",
                "url": "https://www.linkedin.com/jobs/search/?keywords=contract%20freelance&f_AL=true&f_WT=2",
                "reward": 0.0,
                "effort_hours": 0.5,
                "tags": ["easy_apply", "contract", "freelance", "quick_apply"],
                "source_type": "job_application",
                "source_name": "linkedin_easyapply",
            },
        ]

        raw_opps: list[RawOpportunity] = []
        for item in fallback_data:
            raw_opps.append(
                RawOpportunity(
                    id=item["id"],
                    name=item["name"],
                    description=item["description"],
                    platform="linkedin_easyapply",
                    url=item["url"],
                    reward=item["reward"],
                    effort_hours=item["effort_hours"],
                    tags=item["tags"],
                    cycle="pulse",
                    source_type=item["source_type"],
                    source_name=item["source_name"],
                    metadata={},
                    created_at="",
                )
            )

        return raw_opps
