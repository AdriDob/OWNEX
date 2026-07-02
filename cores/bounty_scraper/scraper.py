"""
core_engines.bounty_scraper.scraper — Scrapes public bug bounty listings
from multiple platforms and converts them into database targets.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cores.scope_reader import read_program_scope, extract_assets

logger = logging.getLogger("catseye.bounty_scraper")

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class ScrapedProgram:
    """A program discovered from a public bug bounty listing."""
    name: str
    platform: str
    scope_url: str | None = None
    domains: list[str] = field(default_factory=list)
    wildcards: list[str] = field(default_factory=list)
    has_rewards: bool = True
    estimated_payout: int = 0
    raw_payout_range: str = ""
    technologies: list[str] = field(default_factory=list)
    program_url: str = ""
    is_new: bool = True
    raw_data: dict[str, Any] = field(default_factory=dict)


class BountyScraper:
    """Scrapes public bounty programs from major platforms.

    Uses only public endpoints and HTML scraping — no API keys required.
    Each platform has its own scraper method.
    """

    def __init__(self):
        self._programs: list[ScrapedProgram] = []
        self._last_refresh: str | None = None

    # ── HackerOne ─────────────────────────────────────────────────────

    def scrape_hackerone(self, max_pages: int = 3) -> list[ScrapedProgram]:
        """Scrape public HackerOne programs from their directory API.

        HackerOne exposes a public search endpoint.
        """
        results: list[ScrapedProgram] = []
        for page in range(max_pages):
            try:
                url = (
                    "https://hackerone.com/programs/search?"
                    f"query=sort%3Apublished_at&page%5Bnumber%5D={page + 1}"
                    "&page%5Bsize%5D=50"
                )
                req = urllib.request.Request(url, headers=REQUEST_HEADERS)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    items = data if isinstance(data, list) else data.get("data", [])

                    for item in items:
                        attrs = item.get("attributes", {})
                        name = attrs.get("name", attrs.get("handle", ""))
                        if not name:
                            continue

                        scope_url = (
                            f"https://hackerone.com{attrs.get('url', '')}"
                            if attrs.get("url")
                            else None
                        )
                        payout = attrs.get("offers_bounties", False)
                        submission_state = attrs.get("submission_state", "")

                        prog = ScrapedProgram(
                            name=name,
                            platform="hackerone",
                            scope_url=scope_url,
                            has_rewards=bool(payout),
                            program_url=f"https://hackerone.com/{attrs.get('handle', name)}",
                            raw_data=attrs,
                        )

                        # Extract domains from structured scope if available
                        structured_scope = attrs.get("structured_scope", {})
                        if structured_scope:
                            for asset in structured_scope.get("assets", []):
                                asset_id = asset.get("asset_identifier", "")
                                if asset_id:
                                    if asset_id.startswith("*."):
                                        prog.wildcards.append(asset_id[2:])
                                    else:
                                        prog.domains.append(asset_id)

                        results.append(prog)

            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
                logger.warning("HackerOne page %d: %s", page + 1, e)
                continue
            except Exception as e:
                logger.warning("HackerOne unexpected error on page %d: %s", page + 1, e)
                continue

        logger.info("HackerOne: %d programs scraped", len(results))
        return results

    # ── Bugcrowd ──────────────────────────────────────────────────────

    def scrape_bugcrowd(self, max_pages: int = 3) -> list[ScrapedProgram]:
        """Scrape public Bugcrowd programs from their directory.

        Bugcrowd's program directory returns JSON when properly requested.
        """
        results: list[ScrapedProgram] = []
        for page in range(max_pages):
            try:
                url = (
                    "https://bugcrowd.com/programs.json?"
                    f"page={page + 1}&sort=promoted&order=desc"
                )
                req = urllib.request.Request(url, headers=REQUEST_HEADERS)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    programs = data if isinstance(data, list) else data.get("programs", [])

                    for item in programs:
                        name = item.get("name", item.get("handle", ""))
                        if not name:
                            continue

                        code = item.get("code", item.get("slug", ""))
                        prog = ScrapedProgram(
                            name=name,
                            platform="bugcrowd",
                            scope_url=f"https://bugcrowd.com/{code}" if code else None,
                            has_rewards=bool(item.get("payout", False)),
                            program_url=f"https://bugcrowd.com/{code}" if code else "",
                            raw_payout_range=item.get("reward_range", ""),
                            raw_data=item,
                        )
                        results.append(prog)

            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
                logger.warning("Bugcrowd page %d: %s", page + 1, e)
                continue
            except Exception as e:
                logger.warning("Bugcrowd unexpected error on page %d: %s", page + 1, e)
                continue

        logger.info("Bugcrowd: %d programs scraped", len(results))
        return results

    # ── Intigriti ──────────────────────────────────────────────────────

    def scrape_intigriti(self, max_pages: int = 2) -> list[ScrapedProgram]:
        """Scrape public Intigriti programs.

        Intigriti has a public directory of programs.
        """
        results: list[ScrapedProgram] = []
        for page in range(max_pages):
            try:
                offset = page * 20
                url = f"https://api.intigriti.com/community/programs?offset={offset}&limit=20&sort=-date"
                req = urllib.request.Request(
                    url,
                    headers={
                        **REQUEST_HEADERS,
                        "Referer": "https://www.intigriti.com/programs",
                    },
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    items = data if isinstance(data, list) else data.get("records", [])

                    for item in items:
                        name = item.get("name", item.get("title", item.get("programName", "")))
                        if not name:
                            continue

                        prog = ScrapedProgram(
                            name=name,
                            platform="intigriti",
                            scope_url=item.get("scopeUrl", item.get("url", "")),
                            has_rewards=True,
                            program_url=item.get("publicUrl", item.get("url", "")),
                            raw_payout_range=item.get("rewardRange", item.get("maxBounty", "")),
                            technologies=item.get("technologies", []),
                            raw_data=item,
                        )
                        results.append(prog)

            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
                logger.warning("Intigriti page %d: %s", page + 1, e)
                continue
            except Exception as e:
                logger.warning("Intigriti unexpected error on page %d: %s", page + 1, e)
                continue

        logger.info("Intigriti: %d programs scraped", len(results))
        return results

    # ── YesWeHack ─────────────────────────────────────────────────────

    def scrape_yeswehack(self, max_pages: int = 2) -> list[ScrapedProgram]:
        """Scrape public YesWeHack programs."""
        results: list[ScrapedProgram] = []
        for page in range(max_pages):
            try:
                url = f"https://api.yeswehack.com/public/programs?page={page + 1}&per_page=50"
                req = urllib.request.Request(
                    url,
                    headers={
                        **REQUEST_HEADERS,
                        "Accept": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    items = data if isinstance(data, list) else data.get("items", data.get("data", []))

                    for item in items:
                        name = item.get("title", item.get("name", ""))
                        if not name:
                            continue

                        prog = ScrapedProgram(
                            name=name,
                            platform="yeswehack",
                            scope_url=item.get("scope_url", item.get("url", "")),
                            has_rewards=True,
                            program_url=item.get("public_url", ""),
                            raw_payout_range=item.get("reward_range", ""),
                            technologies=item.get("technologies", []),
                            raw_data=item,
                        )
                        results.append(prog)

            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
                logger.warning("YesWeHack page %d: %s", page + 1, e)
                continue
            except Exception as e:
                logger.warning("YesWeHack unexpected error on page %d: %s", page + 1, e)
                continue

        logger.info("YesWeHack: %d programs scraped", len(results))
        return results

    # ── All platforms ──────────────────────────────────────────────────

    def scrape_all(self, max_pages: int = 2) -> list[ScrapedProgram]:
        """Scrape all supported platforms."""
        all_programs: list[ScrapedProgram] = []
        seen_names: set[str] = set()

        scrapers = [
            ("HackerOne", lambda: self.scrape_hackerone(max_pages)),
            ("Bugcrowd", lambda: self.scrape_bugcrowd(max_pages)),
            ("Intigriti", lambda: self.scrape_intigriti(max(1, max_pages - 1))),
            ("YesWeHack", lambda: self.scrape_yeswehack(max(1, max_pages - 1))),
        ]

        for platform_name, scraper_fn in scrapers:
            try:
                programs = scraper_fn()
                for prog in programs:
                    if not prog.has_rewards:
                        continue
                    dedup_key = f"{prog.platform}:{prog.name.lower().strip()}"
                    if dedup_key not in seen_names:
                        seen_names.add(dedup_key)
                        all_programs.append(prog)
            except Exception as e:
                logger.warning("Failed to scrape %s: %s", platform_name, e)

        self._programs = all_programs
        self._last_refresh = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Total: %d unique reward-offering programs scraped across all platforms",
            len(all_programs),
        )
        return all_programs

    # ── Convert to DB targets ──────────────────────────────────────────

    def convert_to_targets(
        self,
        programs: list[ScrapedProgram],
        session,
        models,
    ) -> list[Any]:
        """Convert scraped programs into DB Target + ScopeDocument records.

        Skips programs that already exist (matched by platform + slug).
        """
        created_targets: list[Any] = []
        for prog in programs:
            try:
                slug = re.sub(r"[^a-zA-Z0-9_-]", "_", prog.name.lower().strip())
                platform_slug = f"{prog.platform}_{slug}"

                existing = (
                    session.query(models.Target)
                    .filter(models.Target.name == platform_slug)
                    .first()
                )
                if existing:
                    continue

                domain = prog.domains[0] if prog.domains else (
                    prog.wildcards[0] if prog.wildcards else f"{slug}.com"
                )

                target = models.Target(
                    name=platform_slug,
                    domain=domain,
                )
                session.add(target)
                session.flush()
                session.refresh(target)

                # Create scope document
                if prog.scope_url:
                    try:
                        scope_result = read_program_scope(
                            url=prog.scope_url,
                            program_name=prog.name,
                        )
                        if "error" not in scope_result:
                            scope_doc = models.ScopeDocument(
                                target_id=target.id,
                                platform=prog.platform,
                                program_name=prog.name,
                                scope_url=prog.scope_url,
                                raw_text=scope_result.get("raw_text", ""),
                                summary=scope_result.get("summary", ""),
                                assets_extracted=scope_result.get("assets_extracted", "[]"),
                                hash_value=scope_result.get("hash", ""),
                                content_type=scope_result.get("content_type", ""),
                            )
                            session.add(scope_doc)

                            # Extract domains from scope if not already set
                            assets = json.loads(
                                scope_result.get("assets_extracted", "{}")
                            )
                            if isinstance(assets, dict):
                                if assets.get("wildcards") and not target.domain:
                                    target.domain = assets["wildcards"][0]
                                if assets.get("domains") and not target.domain:
                                    target.domain = assets["domains"][0]
                    except Exception as e:
                        logger.warning(
                            "Failed to read scope for %s: %s", prog.name, e
                        )

                session.commit()
                created_targets.append(target)
                logger.info("Created target: %s (%s)", platform_slug, prog.platform)

            except Exception as e:
                logger.warning("Failed to convert program %s: %s", prog.name, e)
                session.rollback()

        return created_targets

    # ── Prioritize ─────────────────────────────────────────────────────

    def prioritize(self, programs: list[ScrapedProgram]) -> list[ScrapedProgram]:
        """Sort programs by estimated value and freshness (newest first)."""
        def sort_key(p: ScrapedProgram) -> tuple:
            payout = p.estimated_payout if p.estimated_payout > 0 else 500
            new_bonus = 1 if p.is_new else 0
            reward_bonus = 1 if p.has_rewards else 0
            return (-payout, -new_bonus, -reward_bonus)

        return sorted(programs, key=sort_key)

    @property
    def program_count(self) -> int:
        return len(self._programs)


_SCRAPER: BountyScraper | None = None


def get_bounty_scraper() -> BountyScraper:
    global _SCRAPER
    if _SCRAPER is None:
        _SCRAPER = BountyScraper()
    return _SCRAPER
