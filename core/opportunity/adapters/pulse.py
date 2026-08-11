"""Pulse Cycle Adapter — AI Work platforms (Outlier, DataAnnotation, Mindrift, Remotasks, Freelancer Microtasks, LinkedIn Easy Apply, Opyre Microtasks).

Integrated with credentials vault for API key management.
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class OutlierAdapter(OpportunityAdapter):
    """Outlier.ai adapter — AI training and evaluation tasks (Pulse cycle)."""

    platform: str = "outlier"
    cycle: str = "pulse"

    def __init__(self, config: dict[str, Any] | None = None):
        # Load credentials from vault first, then merge with config
        merged_config = load_credentials("outlier", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("outlier", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch projects from Outlier.ai."""
        try:
            headers = get_auth_headers("outlier", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.outlier.ai/v1/projects/available", headers=headers, timeout=15)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                projects = data.get("projects", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for project in projects[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"outlier_{project.get('id')}",
                            name=project.get("name") or "Outlier Project",
                            description=project.get("description") or "",
                            platform="outlier",
                            url=project.get("url"),
                            reward=float(project.get("pay_rate", 0)),
                            effort_hours=float(project.get("estimated_hours", 2)),
                            tags=project.get("skills", ["ai_training", "evaluation"]),
                            cycle="pulse",
                            source_type="ai_work",
                            source_name="outlier",
                            metadata={"original": project},
                            created_at=project.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("OutlierAdapter fetch failed: %s", e)
            return []


class DataAnnotationAdapter(OpportunityAdapter):
    """DataAnnotation.tech adapter — AI data labeling tasks (Pulse cycle)."""

    platform: str = "dataannotation"
    cycle: str = "pulse"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("dataannotation", config)
        super().__init__(merged_config)
        self.email = self.config.get("email")
        self.password = self.config.get("password")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch projects from DataAnnotation."""
        try:
            async with httpx.AsyncClient() as client:
                # Login
                auth_resp = await client.post(
                    "https://api.dataannotation.tech/auth/login",
                    json={"email": self.email, "password": self.password},
                    timeout=15,
                )
                if auth_resp.status_code != 200:
                    return []

                token = auth_resp.json().get("token")
                headers = {"Authorization": f"Bearer {token}"} if token else {}

                # Get available projects
                resp = await client.get(
                    "https://api.dataannotation.tech/v1/projects/available", headers=headers, timeout=15
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                projects = data.get("projects", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for project in projects[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"dataannotation_{project.get('id')}",
                            name=project.get("name") or "DataAnnotation Project",
                            description=project.get("description") or "",
                            platform="dataannotation",
                            url=project.get("url"),
                            reward=float(project.get("pay_rate", 0)),
                            effort_hours=float(project.get("estimated_hours", 3)),
                            tags=project.get("categories", ["data_labeling", "annotation"]),
                            cycle="pulse",
                            source_type="ai_work",
                            source_name="dataannotation",
                            metadata={"original": project},
                            created_at=project.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("DataAnnotationAdapter fetch failed: %s", e)
            return []


class MindriftAdapter(OpportunityAdapter):
    """Mindrift.com adapter — AI training tasks (Pulse cycle)."""

    platform: str = "mindrift"
    cycle: str = "pulse"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("mindrift", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("mindrift", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch tasks from Mindrift."""
        try:
            headers = get_auth_headers("mindrift", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.mindrift.com/v1/tasks/available", headers=headers, timeout=15)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"mindrift_{task.get('id')}",
                            name=task.get("title") or "Mindrift Task",
                            description=task.get("description") or "",
                            platform="mindrift",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("estimated_time", 1.5)),
                            tags=task.get("categories", ["ai_training", "evaluation"]),
                            cycle="pulse",
                            source_type="ai_work",
                            source_name="mindrift",
                            metadata={"original": task},
                            created_at=task.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("MindriftAdapter fetch failed: %s", e)
            return []


class RemotasksAdapter(OpportunityAdapter):
    """Remotasks adapter — various AI data tasks (Pulse cycle)."""

    platform: str = "remotasks"
    cycle: str = "pulse"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("remotasks", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("remotasks", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch tasks from Remotasks."""
        try:
            headers = get_auth_headers("remotasks", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.remotasks.com/v1/tasks", headers=headers, timeout=15)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"remotasks_{task.get('id')}",
                            name=task.get("name") or "Remotasks Task",
                            description=task.get("description") or "",
                            platform="remotasks",
                            url=task.get("url"),
                            reward=float(task.get("pay", 0)),
                            effort_hours=float(task.get("time_estimate", 2)),
                            tags=task.get("categories", ["data_entry", "annotation"]),
                            cycle="pulse",
                            source_type="ai_work",
                            source_name="remotasks",
                            metadata={"original": task},
                            created_at=task.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("RemotasksAdapter fetch failed: %s", e)
            return []


class FreelancerMicrotaskAdapter(OpportunityAdapter):
    """Freelancer.com micro-tasks / contests adapter (Pulse cycle - low effort)."""

    platform: str = "freelancer_microtask"
    cycle: str = "pulse"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("freelancer_micro", config)
        super().__init__(merged_config)
        self.api_token = get_api_key("freelancer_micro", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch micro-tasks and contests from Freelancer (low effort, quick payout)."""
        try:
            headers = get_auth_headers("freelancer_micro", self.config)
            async with httpx.AsyncClient() as client:
                # Fetch contests (micro-tasks)
                resp = await client.get(
                    "https://www.freelancer.com/api/projects/0.1/contests/active",
                    headers=headers,
                    params={"limit": 20, "compact": "true"},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                contests = data.get("result", {}).get("contests", [])

                raw_opps: list[RawOpportunity] = []
                for contest in contests[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"freelancer_micro_{contest.get('id')}",
                            name=f"[Contest] {contest.get('title') or 'Freelancer Contest'}",
                            description=contest.get("description") or "",
                            platform="freelancer_microtask",
                            url=contest.get("url"),
                            reward=float(contest.get("prize", 0)),
                            effort_hours=float(contest.get("time_left_days", 3)) * 2,
                            tags=["contest", "microtask"] + (contest.get("tags", [])[:3]),
                            cycle="pulse",
                            source_type="microtask",
                            source_name="freelancer_microtask",
                            metadata={"original": contest},
                            created_at=contest.get("time_submitted") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("FreelancerMicrotaskAdapter fetch failed: %s", e)
            return []


class LinkedInEasyApplyAdapter(OpportunityAdapter):
    """LinkedIn Easy Apply adapter — low-effort job applications (Pulse cycle)."""

    platform: str = "linkedin_easyapply"
    cycle: str = "pulse"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("linkedin", config)
        super().__init__(merged_config)
        self.li_at_cookie = self.config.get("li_at_cookie") or self.config.get("li_at")
        self.client_id = self.config.get("client_id")
        self.client_secret = self.config.get("client_secret")

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
                    return []

                soup = BeautifulSoup(resp.text, "html.parser")
                job_cards = soup.find_all("li", class_="job-search-card")

                raw_opps: list[RawOpportunity] = []
                for card in job_cards[:15]:
                    job_id = card.get("data-entity-urn", "")
                    if job_id:
                        job_id = job_id.split(":")[-1]
                    title_elem = card.find("h3", class_="base-search-card__title")
                    company_elem = card.find("h4", class_="base-search-card__subtitle")
                    location_elem = card.find("span", class_="job-search-card__location")
                    link_elem = card.find("a", class_="base-card__full-link")

                    easy_apply = card.find("span", string=re.compile(r"Easy Apply", re.I))

                    if not easy_apply:
                        continue

                    raw_opps.append(
                        RawOpportunity(
                            id=f"linkedin_easy_{job_id}",
                            name=f"[Easy Apply] {title_elem.get_text(strip=True) if title_elem else 'LinkedIn Job'}",
                            description=f"Company: {company_elem.get_text(strip=True) if company_elem else 'Unknown'}. Location: {location_elem.get_text(strip=True) if location_elem else 'Remote'}",
                            platform="linkedin_easyapply",
                            url=link_elem.get("href") if link_elem else None,
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
            return []


class OpyreMicrotaskAdapter(OpportunityAdapter):
    """Opyre micro-tasks / quick fixes adapter (Pulse cycle)."""

    platform: str = "opyre_microtask"
    cycle: str = "pulse"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("opyre_micro", config)
        super().__init__(merged_config)
        self.token = get_api_key("opyre_micro", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch quick-fix micro-tasks from Opyre (low effort, fast payout)."""
        try:
            headers = get_auth_headers("opyre_micro", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.opyre.com/v1/tasks/quick",
                    headers=headers,
                    params={"max_effort_hours": 4, "min_reward": 25},
                    timeout=10,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps = []
                for task in tasks[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"opyre_micro_{task.get('id')}",
                            name=f"[Quick] {task.get('title') or 'Opyre Quick Task'}",
                            description=task.get("description") or "",
                            platform="opyre_microtask",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("time_estimate", 1)),
                            tags=["quick-fix", "microtask"] + task.get("labels", []),
                            cycle="pulse",
                            source_type="microtask",
                            source_name="opyre_microtask",
                            metadata={"original": task},
                            created_at=task.get("created_at"),
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("OpyreMicrotaskAdapter fetch failed: %s", e)
            return []
