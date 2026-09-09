"""Security Bounty Platform Adapters — HackerOne, Bugcrowd, Intigriti, YesWeHack.

These adapters connect to real bug bounty platforms to discover programs and
fetch submissions/opportunities for the Security Work Cycle.
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class HackerOneAdapter(OpportunityAdapter):
    """HackerOne platform adapter — largest bug bounty platform (Security cycle)."""

    platform: str = "hackerone"
    cycle: str = "security"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("hackerone", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("hackerone", merged_config)
        self.handle = merged_config.get("handle", "")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open programs from HackerOne API."""
        try:
            headers = get_auth_headers("hackerone", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.hackerone.com/v1/hackers/programs",
                    headers=headers,
                    params={"filter[state]": "open", "page[size]": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                programs = data.get("data", [])

                raw_opps: list[RawOpportunity] = []
                for prog in programs:
                    attrs = prog.get("attributes", {})
                    raw_opps.append(
                        RawOpportunity(
                            id=f"h1_{prog.get('id')}",
                            name=attrs.get("name") or "HackerOne Program",
                            description=attrs.get("brief_description") or attrs.get("description") or "",
                            platform="hackerone",
                            url=attrs.get("url"),
                            reward=float(attrs.get("max_bounty", 0)) if attrs.get("max_bounty") else 0.0,
                            effort_hours=8.0,
                            tags=attrs.get("tags", ["bug_bounty"]),
                            cycle="security",
                            source_type="platform",
                            source_name="hackerone",
                            metadata={"original": prog, "handle": attrs.get("handle")},
                            created_at=attrs.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("HackerOneAdapter fetch failed: %s", e)
            return []

    async def fetch_submissions(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch submitted reports as opportunities."""
        try:
            headers = get_auth_headers("hackerone", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.hackerone.com/v1/hackers/reports",
                    headers=headers,
                    params={"page[size]": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                reports = data.get("data", [])

                raw_opps: list[RawOpportunity] = []
                for report in reports:
                    attrs = report.get("attributes", {})
                    raw_opps.append(
                        RawOpportunity(
                            id=f"h1_report_{report.get('id')}",
                            name=f"[Report] {attrs.get('title', 'HackerOne Report')}",
                            description=attrs.get("vulnerability_information", "")[:500],
                            platform="hackerone",
                            url=f"https://hackerone.com/reports/{attrs.get('number')}",
                            reward=float(attrs.get("bounty_amount", 0)),
                            effort_hours=2.0,
                            tags=[attrs.get("severity_rating", "unknown")],
                            cycle="security",
                            source_type="submission",
                            source_name="hackerone",
                            metadata={"original": report, "state": attrs.get("state")},
                            created_at=attrs.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("HackerOneAdapter submissions fetch failed: %s", e)
            return []


class BugcrowdAdapter(OpportunityAdapter):
    """Bugcrowd platform adapter — second largest bug bounty platform (Security cycle)."""

    platform: str = "bugcrowd"
    cycle: str = "security"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("bugcrowd", config)
        super().__init__(merged_config)
        self.api_token = get_api_key("bugcrowd", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open programs from Bugcrowd API."""
        try:
            headers = get_auth_headers("bugcrowd", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.bugcrowd.com/programs",
                    headers=headers,
                    params={"state": "open", "limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                programs = data.get("programs", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for prog in programs:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"bc_{prog.get('id')}",
                            name=prog.get("name") or "Bugcrowd Program",
                            description=prog.get("description", "")[:500],
                            platform="bugcrowd",
                            url=prog.get("url"),
                            reward=float(prog.get("max_payout", 0)) if prog.get("max_payout") else 0.0,
                            effort_hours=8.0,
                            tags=prog.get("tags", ["bug_bounty"]),
                            cycle="security",
                            source_type="platform",
                            source_name="bugcrowd",
                            metadata={"original": prog, "code": prog.get("code")},
                            created_at=prog.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("BugcrowdAdapter fetch failed: %s", e)
            return []

    async def fetch_submissions(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch submitted reports as opportunities."""
        try:
            headers = get_auth_headers("bugcrowd", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.bugcrowd.com/submissions",
                    headers=headers,
                    params={"limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                submissions = data.get("submissions", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for sub in submissions:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"bc_report_{sub.get('id')}",
                            name=f"[Report] {sub.get('title', 'Bugcrowd Submission')}",
                            description=sub.get("description", "")[:500],
                            platform="bugcrowd",
                            url=sub.get("url"),
                            reward=float(sub.get("payout_amount", 0)),
                            effort_hours=2.0,
                            tags=[sub.get("severity", "unknown")],
                            cycle="security",
                            source_type="submission",
                            source_name="bugcrowd",
                            metadata={"original": sub, "state": sub.get("state")},
                            created_at=sub.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("BugcrowdAdapter submissions fetch failed: %s", e)
            return []


class IntigritiAdapter(OpportunityAdapter):
    """Intigriti platform adapter — European bug bounty platform (Security cycle)."""

    platform: str = "intigriti"
    cycle: str = "security"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("intigriti", config)
        super().__init__(merged_config)
        self.client_id = merged_config.get("client_id", "")
        self.client_secret = merged_config.get("client_secret", "")
        self._access_token: str | None = None

    async def _get_access_token(self) -> str | None:
        """Get OAuth2 access token."""
        if self._access_token:
            return self._access_token
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.intigriti.com/external/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    self._access_token = resp.json().get("access_token")
                    return self._access_token
        except Exception:
            pass
        return None

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open programs from Intigriti API."""
        try:
            token = await self._get_access_token()
            if not token:
                return []

            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.intigriti.com/external/researcher/v1/programs",
                    headers=headers,
                    params={"status": "open", "limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                programs = data.get("records", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for prog in programs:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"inti_{prog.get('id')}",
                            name=prog.get("name") or "Intigriti Program",
                            description=prog.get("description", "")[:500],
                            platform="intigriti",
                            url=prog.get("url"),
                            reward=float(prog.get("max_bounty", 0)) if prog.get("max_bounty") else 0.0,
                            effort_hours=8.0,
                            tags=prog.get("tags", ["bug_bounty"]),
                            cycle="security",
                            source_type="platform",
                            source_name="intigriti",
                            metadata={"original": prog, "handle": prog.get("handle")},
                            created_at=prog.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("IntigritiAdapter fetch failed: %s", e)
            return []

    async def fetch_submissions(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch submitted reports as opportunities."""
        try:
            token = await self._get_access_token()
            if not token:
                return []

            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.intigriti.com/external/researcher/v1/submissions",
                    headers=headers,
                    params={"limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                submissions = data.get("records", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for sub in submissions:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"inti_report_{sub.get('id')}",
                            name=f"[Report] {sub.get('title', 'Intigriti Submission')}",
                            description=sub.get("description", "")[:500],
                            platform="intigriti",
                            url=sub.get("url"),
                            reward=float(sub.get("bounty_amount", 0)),
                            effort_hours=2.0,
                            tags=[sub.get("severity", "unknown")],
                            cycle="security",
                            source_type="submission",
                            source_name="intigriti",
                            metadata={"original": sub, "status": sub.get("status")},
                            created_at=sub.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("IntigritiAdapter submissions fetch failed: %s", e)
            return []


class YesWeHackAdapter(OpportunityAdapter):
    """YesWeHack platform adapter — European bug bounty platform (Security cycle)."""

    platform: str = "yeswehack"
    cycle: str = "security"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("yeswehack", config)
        super().__init__(merged_config)
        self.api_token = get_api_key("yeswehack", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open programs from YesWeHack API."""
        try:
            headers = get_auth_headers("yeswehack", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.yeswehack.com/programs",
                    headers=headers,
                    params={"status": "open", "limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                programs = data.get("programs", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for prog in programs:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"yeswehack_{prog.get('id')}",
                            name=prog.get("name") or "YesWeHack Program",
                            description=prog.get("description", "")[:500],
                            platform="yeswehack",
                            url=prog.get("url"),
                            reward=float(prog.get("max_reward", 0)) if prog.get("max_reward") else 0.0,
                            effort_hours=8.0,
                            tags=prog.get("categories", ["bug_bounty"]),
                            cycle="security",
                            source_type="platform",
                            source_name="yeswehack",
                            metadata={"original": prog, "slug": prog.get("slug")},
                            created_at=prog.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("YesWeHackAdapter fetch failed: %s", e)
            return []

    async def fetch_submissions(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch submitted reports as opportunities."""
        try:
            headers = get_auth_headers("yeswehack", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.yeswehack.com/submissions",
                    headers=headers,
                    params={"limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                submissions = data.get("submissions", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for sub in submissions:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"yeswehack_report_{sub.get('id')}",
                            name=f"[Report] {sub.get('title', 'YesWeHack Submission')}",
                            description=sub.get("description", "")[:500],
                            platform="yeswehack",
                            url=sub.get("url"),
                            reward=float(sub.get("reward", 0)),
                            effort_hours=2.0,
                            tags=[sub.get("severity", "unknown")],
                            cycle="security",
                            source_type="submission",
                            source_name="yeswehack",
                            metadata={"original": sub, "status": sub.get("status")},
                            created_at=sub.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("YesWeHackAdapter submissions fetch failed: %s", e)
            return []


class ImmunefiAdapter(OpportunityAdapter):
    """Immunefi platform adapter — Web3/smart contract bug bounty platform (Security cycle)."""

    platform: str = "immunefi"
    cycle: str = "security"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("immunefi", config)
        super().__init__(merged_config)
        self.api_token = get_api_key("immunefi", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open programs from Immunefi API."""
        try:
            headers = get_auth_headers("immunefi", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.immunefi.com/v1/programs",
                    headers=headers,
                    params={"status": "active", "limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                programs = data.get("programs", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for prog in programs:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"immunefi_{prog.get('id')}",
                            name=prog.get("name") or "Immunefi Program",
                            description=prog.get("description", "")[:500],
                            platform="immunefi",
                            url=prog.get("url"),
                            reward=float(prog.get("max_reward", 0)) if prog.get("max_reward") else 0.0,
                            effort_hours=10.0,  # Web3 bounties typically require more effort
                            tags=prog.get("categories", ["web3", "smart_contract", "blockchain"]),
                            cycle="security",
                            source_type="platform",
                            source_name="immunefi",
                            metadata={"original": prog, "chain": prog.get("chain")},
                            created_at=prog.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("ImmunefiAdapter fetch failed: %s", e)
            return []

    async def fetch_submissions(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch submitted reports as opportunities."""
        try:
            headers = get_auth_headers("immunefi", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.immunefi.com/v1/submissions",
                    headers=headers,
                    params={"limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                submissions = data.get("submissions", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for sub in submissions:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"immunefi_report_{sub.get('id')}",
                            name=f"[Report] {sub.get('title', 'Immunefi Submission')}",
                            description=sub.get("description", "")[:500],
                            platform="immunefi",
                            url=sub.get("url"),
                            reward=float(sub.get("reward", 0)),
                            effort_hours=3.0,
                            tags=[sub.get("severity", "unknown")],
                            cycle="security",
                            source_type="submission",
                            source_name="immunefi",
                            metadata={"original": sub, "status": sub.get("status")},
                            created_at=sub.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("ImmunefiAdapter submissions fetch failed: %s", e)
            return []


class SynackAdapter(OpportunityAdapter):
    """Synack platform adapter — Private/crowdsourced pentest platform (Security cycle)."""

    platform: str = "synack"
    cycle: str = "security"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("synack", config)
        super().__init__(merged_config)
        self.api_token = get_api_key("synack", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch available missions from Synack API."""
        try:
            headers = get_auth_headers("synack", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://platform.synack.com/api/missions",
                    headers=headers,
                    params={"status": "open", "limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                missions = data.get("missions", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for mission in missions:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"synack_{mission.get('id')}",
                            name=mission.get("name") or "Synack Mission",
                            description=mission.get("description", "")[:500],
                            platform="synack",
                            url=mission.get("url"),
                            reward=float(mission.get("reward", 0)) if mission.get("reward") else 0.0,
                            effort_hours=6.0,
                            tags=mission.get("categories", ["pentest", "vulnerability"]),
                            cycle="security",
                            source_type="platform",
                            source_name="synack",
                            metadata={"original": mission, "slug": mission.get("slug")},
                            created_at=mission.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("SynackAdapter fetch failed: %s", e)
            return []

    async def fetch_submissions(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch submitted reports as opportunities."""
        try:
            headers = get_auth_headers("synack", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://platform.synack.com/api/submissions",
                    headers=headers,
                    params={"limit": 50},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                submissions = data.get("submissions", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for sub in submissions:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"synack_report_{sub.get('id')}",
                            name=f"[Report] {sub.get('title', 'Synack Submission')}",
                            description=sub.get("description", "")[:500],
                            platform="synack",
                            url=sub.get("url"),
                            reward=float(sub.get("payout", 0)),
                            effort_hours=3.0,
                            tags=[sub.get("severity", "unknown")],
                            cycle="security",
                            source_type="submission",
                            source_name="synack",
                            metadata={"original": sub, "status": sub.get("status")},
                            created_at=sub.get("created_at") or "",
                        )
                    )
                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("SynackAdapter submissions fetch failed: %s", e)
            return []


# ── Factory ─────────────────────────────────────────────────────────


class SecurityBountyFactory:
    """Factory for creating Security bounty platform adapters."""

    @staticmethod
    def create(platform: str, config: dict[str, Any] | None = None) -> OpportunityAdapter:
        adapter_map = {
            "hackerone": HackerOneAdapter,
            "bugcrowd": BugcrowdAdapter,
            "intigriti": IntigritiAdapter,
            "yeswehack": YesWeHackAdapter,
        }

        cls = adapter_map.get(platform.lower())
        if not cls:
            raise ValueError(f"No security bounty adapter for platform: {platform}")

        return cls(config)

    @staticmethod
    async def list_platforms() -> list[str]:
        return ["hackerone", "bugcrowd", "intigriti", "yeswehack"]

    @staticmethod
    async def fetch_all_programs(config: dict[str, Any] | None = None) -> list[RawOpportunity]:
        """Fetch from all configured security bounty platforms."""
        all_opps: list[RawOpportunity] = []
        for platform in await SecurityBountyFactory.list_platforms():
            adapter = SecurityBountyFactory.create(platform, config)
            opps = await adapter.fetch_opportunities()
            all_opps.extend(opps)
        return all_opps

    @staticmethod
    async def fetch_all_submissions(config: dict[str, Any] | None = None) -> list[RawOpportunity]:
        """Fetch submissions from all configured security bounty platforms."""
        all_opps: list[RawOpportunity] = []
        for platform in await SecurityBountyFactory.list_platforms():
            adapter = SecurityBountyFactory.create(platform, config)
            if hasattr(adapter, "fetch_submissions"):
                opps = await adapter.fetch_submissions()
                all_opps.extend(opps)
        return all_opps
