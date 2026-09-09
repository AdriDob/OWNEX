"""Atlas Adapter — Research/Intelligence platforms (CVE, ExploitDB, GitHub Advisory, Google Trends, Shodan)."""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class AtlasBaseAdapter(OpportunityAdapter):
    """Base adapter for Research/Intelligence platforms."""

    platform: str = "atlas"
    cycle: str = "atlas"


class CVEAdapter(AtlasBaseAdapter):
    """CVE/NVD adapter — vulnerability tracking and exploit opportunities."""

    platform: str = "cve"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("cve", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch recent CVEs from NVD API."""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "resultsPerPage": 20,
                    "startIndex": 0,
                    "pubStartDate": "2024-01-01T00:00:00.000",
                }
                resp = await client.get(
                    "https://services.nvd.nist.gov/rest/json/cves/2.0",
                    params=params,
                    timeout=20,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                vulns = data.get("vulnerabilities", [])

                raw_opps: list[RawOpportunity] = []
                for vuln in vulns[:15]:
                    cve = vuln.get("cve", {})
                    cve_id = cve.get("id", "")
                    descriptions = cve.get("descriptions", [])
                    desc = next((d["value"] for d in descriptions if d["lang"] == "en"), "")

                    metrics = cve.get("metrics", {})
                    cvss_v3 = metrics.get("cvssMetricV31", metrics.get("cvssMetricV30", []))
                    severity = "medium"
                    score = 5.0
                    if cvss_v3:
                        cvss = cvss_v3[0].get("cvssData", {})
                        severity = cvss.get("baseSeverity", "MEDIUM").lower()
                        score = cvss.get("baseScore", 5.0)

                    raw_opps.append(
                        RawOpportunity(
                            id=f"cve_{cve_id}",
                            name=cve_id,
                            description=desc[:300],
                            platform="cve",
                            url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                            reward=0.0,
                            effort_hours=2.0,
                            tags=["cve", severity, "vulnerability"],
                            cycle="atlas",
                            source_type="intelligence",
                            source_name="nvd",
                            metadata={
                                "cvss_score": score,
                                "severity": severity,
                                "references": cve.get("references", []),
                            },
                            created_at=cve.get("published", ""),
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("CVEAdapter fetch failed: %s", e)
            return []


class ExploitDBAdapter(AtlasBaseAdapter):
    """Exploit-DB adapter — public exploits and proof-of-concepts."""

    platform: str = "exploitdb"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("exploitdb", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch recent exploits from Exploit-DB (via GitHub mirror or API)."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://raw.githubusercontent.com/offensive-security/exploitdb/master/files_exploits.csv",
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                import csv
                from io import StringIO

                reader = csv.DictReader(StringIO(resp.text))
                raw_opps: list[RawOpportunity] = []
                for idx, row in enumerate(reader):
                    if idx >= 15:
                        break
                    raw_opps.append(
                        RawOpportunity(
                            id=f"exploitdb_{row.get('id', idx)}",
                            name=row.get("description", "Exploit")[:100],
                            description=f"Type: {row.get('type')} | Platform: {row.get('platform')} | Author: {row.get('author')}",
                            platform="exploitdb",
                            url=f"https://www.exploit-db.com/exploits/{row.get('id')}",
                            reward=0.0,
                            effort_hours=1.5,
                            tags=["exploit", "poc", row.get("type", "").lower(), row.get("platform", "").lower()],
                            cycle="atlas",
                            source_type="intelligence",
                            source_name="exploitdb",
                            metadata={"original": row},
                            created_at=row.get("date_published", ""),
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("ExploitDBAdapter fetch failed: %s", e)
            return []


class GitHubAdvisoryAdapter(AtlasBaseAdapter):
    """GitHub Security Advisories adapter — supply chain vulnerabilities."""

    platform: str = "github_advisory"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("github_advisory", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch recent GitHub Security Advisories."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.github.com/advisories",
                    params={"per_page": 20, "sort": "published", "direction": "desc"},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                advisories = resp.json()

                raw_opps: list[RawOpportunity] = []
                for adv in advisories[:15]:
                    severity = adv.get("severity", "medium")
                    raw_opps.append(
                        RawOpportunity(
                            id=f"github_advisory_{adv.get('ghsa_id')}",
                            name=adv.get("summary") or adv.get("ghsa_id"),
                            description=adv.get("description", "")[:300],
                            platform="github_advisory",
                            url=adv.get("html_url"),
                            reward=0.0,
                            effort_hours=1.5,
                            tags=["supply_chain", severity, "github"],
                            cycle="atlas",
                            source_type="intelligence",
                            source_name="github",
                            metadata={
                                "ghsa_id": adv.get("ghsa_id"),
                                "severity": severity,
                                "vulnerabilities": adv.get("vulnerabilities", []),
                                "references": adv.get("references", []),
                            },
                            created_at=adv.get("published_at"),
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("GitHubAdvisoryAdapter fetch failed: %s", e)
            return []


class GoogleTrendsAdapter(AtlasBaseAdapter):
    """Google Trends adapter — trending topics for research prioritization."""

    platform: str = "google_trends"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("google_trends", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch trending topics from Google Trends (via pytrends)."""
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl="en-US", tz=360)
            trending = pytrends.trending_searches(pn="united_states")

            raw_opps: list[RawOpportunity] = []
            for idx, topic in enumerate(trending[:10]):
                raw_opps.append(
                    RawOpportunity(
                        id=f"gtrends_{topic.replace(' ', '_').lower()}",
                        name=f"Trending: {topic}",
                        description=f"Top {idx + 1} trending search — research opportunity",
                        platform="google_trends",
                        url=f"https://trends.google.com/trends/explore?q={topic.replace(' ', '%20')}",
                        reward=0.0,
                        effort_hours=1.0,
                        tags=["trends", "research", "osint"],
                        cycle="atlas",
                        source_type="intelligence",
                        source_name="google_trends",
                        metadata={"rank": idx + 1},
                        created_at="",
                    )
                )

            return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("GoogleTrendsAdapter fetch failed: %s", e)
            return []


class ShodanAdapter(AtlasBaseAdapter):
    """Shodan adapter — exposed services, vulnerable configurations."""

    platform: str = "shodan"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("shodan", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch exposed services from Shodan."""
        try:
            async with httpx.AsyncClient() as client:
                params = {"key": self.config.get("api_key"), "page": 1, "minify": "true"}
                resp = await client.get(
                    "https://api.shodan.io/shodan/host/search",
                    params=params,
                    timeout=20,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                matches = data.get("matches", [])

                raw_opps: list[RawOpportunity] = []
                for match in matches[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"shodan_{match.get('ip_str', '').replace('.', '_')}",
                            name=f"Exposed: {match.get('product', 'Service')} on {match.get('port')}",
                            description=f"IP: {match.get('ip_str')} | Org: {match.get('org', 'Unknown')} | {match.get('data', '')[:200]}",
                            platform="shodan",
                            url=f"https://www.shodan.io/host/{match.get('ip_str')}",
                            reward=0.0,
                            effort_hours=2.0,
                            tags=["shodan", "recon", match.get("product", "").lower().replace(" ", "_")],
                            cycle="atlas",
                            source_type="recon",
                            source_name="shodan",
                            metadata={
                                "ip": match.get("ip_str"),
                                "port": match.get("port"),
                                "org": match.get("org"),
                                "product": match.get("product"),
                                "version": match.get("version"),
                            },
                            created_at=match.get("timestamp"),
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("ShodanAdapter fetch failed: %s", e)
            return []
