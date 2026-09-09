"""Freelancer.com Adapter — Direct software work, no portfolio/interview required for many tasks."""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class FreelancerAdapter(OpportunityAdapter):
    """Freelancer.com adapter - REST API for projects/jobs (Forge cycle)."""

    platform: str = "freelancer"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("freelancer", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("freelancer", merged_config)
        self.user_id = self.config.get("user_id")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch projects from Freelancer API.

        Filters for: software development, no portfolio required, entry-level,
        direct hire, fixed-price micro-tasks.
        """
        try:
            headers = (
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                if self.api_key
                else {}
            )

            params = {
                "category": "software-development,web-development,mobile-development,"
                "desktop-application,api-development,scripting,"
                "database-development,devops,qa-testing",
                "job_type": "fixed",
                "budget_min": "10",
                "budget_max": "5000",
                "limit": 50,
                "compact": "true",
                "query": "entry level OR junior OR no experience OR "
                "no portfolio OR microtask OR small task OR "
                "quick fix OR bug fix OR simple OR beginner",
            }

            if personal:
                if personal.get("skills"):
                    params["query"] += " " + " ".join(personal["skills"][:5])
                if personal.get("hourly_rate_max"):
                    params["budget_max"] = str(personal["hourly_rate_max"] * 40)

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://www.freelancer.com/api/projects/0.1/projects/",
                    headers=headers,
                    params=params,
                )

                if resp.status_code != 200:
                    return []

                data = resp.json()
                projects = data.get("result", {}).get("projects", [])

                raw_opps: list[RawOpportunity] = []
                for project in projects[:30]:
                    desc = (project.get("description") or "").lower()
                    title = (project.get("title") or "").lower()

                    skip_keywords = [
                        "senior",
                        "lead",
                        "architect",
                        "5+ years",
                        "10+ years",
                        "portfolio required",
                        "must have portfolio",
                        "proven track record",
                        "extensive experience",
                        "expert only",
                    ]
                    if any(kw in desc or kw in title for kw in skip_keywords):
                        continue

                    prefer_keywords = [
                        "microtask",
                        "quick",
                        "simple",
                        "small",
                        "entry",
                        "junior",
                        "beginner",
                        "no experience",
                        "no portfolio",
                        "learning",
                        "student",
                        "first job",
                        "starter",
                        "easy",
                        "basic",
                        "fix bug",
                        "small fix",
                        "minor",
                        "tweak",
                        "adjust",
                    ]
                    match_score = sum(1 for kw in prefer_keywords if kw in desc or kw in title)

                    budget = project.get("budget", {})
                    min_budget = budget.get("minimum", 0)
                    max_budget = budget.get("maximum", 0)
                    avg_budget = (min_budget + max_budget) / 2 if max_budget else min_budget

                    effort_hours = max(1, avg_budget / 25)

                    raw_opps.append(
                        RawOpportunity(
                            id=f"freelancer_{project.get('id')}",
                            name=project.get("title") or "Freelancer Project",
                            description=project.get("description") or "",
                            platform="freelancer",
                            url=f"https://www.freelancer.com/projects/{project.get('seo_url')}",
                            reward=float(avg_budget),
                            effort_hours=float(effort_hours),
                            tags=project.get("jobs", []) + project.get("tags", []),
                            cycle="forge",
                            source_type="freelance_direct",
                            source_name="freelancer",
                            metadata={
                                "original": project,
                                "budget_min": min_budget,
                                "budget_max": max_budget,
                                "currency": budget.get("currency", "USD"),
                                "status": project.get("status"),
                                "posted_date": project.get("time_submitted"),
                                "bid_count": project.get("bid_stats", {}).get("bid_count", 0),
                                "avg_bid": project.get("bid_stats", {}).get("avg_bid", 0),
                                "match_score": match_score,
                            },
                            created_at=project.get("time_submitted", ""),
                        )
                    )

                raw_opps.sort(key=lambda x: (-x.metadata.get("match_score", 0), -x.reward / max(x.effort_hours, 1)))

                return raw_opps

        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("FreelancerAdapter fetch failed: %s", e)
            return []


class FreelancerMicrotaskAdapter(OpportunityAdapter):
    """Freelancer.com micro-tasks / contests adapter - even lower barrier (Pulse cycle)."""

    platform: str = "freelancer_microtask"
    cycle: str = "pulse"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("freelancer_micro", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("freelancer_micro", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch micro-tasks and small contests from Freelancer."""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

            params = {
                "category": "software-development,web-development,mobile-development",
                "job_type": "contest,fixed",
                "budget_max": "200",
                "limit": 30,
                "compact": "true",
            }

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://www.freelancer.com/api/projects/0.1/projects/",
                    headers=headers,
                    params=params,
                )

                if resp.status_code != 200:
                    return []

                data = resp.json()
                projects = data.get("result", {}).get("projects", [])

                raw_opps: list[RawOpportunity] = []
                for project in projects[:20]:
                    budget = project.get("budget", {})
                    reward = budget.get("maximum") or budget.get("minimum") or 50

                    raw_opps.append(
                        RawOpportunity(
                            id=f"freelancer_micro_{project.get('id')}",
                            name=f"[Micro] {project.get('title') or 'Micro-task'}",
                            description=project.get("description") or "",
                            platform="freelancer_microtask",
                            url=f"https://www.freelancer.com/projects/{project.get('seo_url')}",
                            reward=float(reward),
                            effort_hours=float(max(0.5, reward / 50)),
                            tags=["microtask", "quick"] + project.get("tags", []),
                            cycle="pulse",
                            source_type="microtask",
                            source_name="freelancer_microtask",
                            metadata={"original": project},
                            created_at=project.get("time_submitted", ""),
                        )
                    )

                return raw_opps

        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("FreelancerMicrotaskAdapter fetch failed: %s", e)
            return []
