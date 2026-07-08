"""
core_engines.bounty_scraper.scraper — Scrapes public bug bounty listings
from multiple platforms and converts them into database targets.

Sources:
  - HackerOne directory API + hacktivity
  - Bugcrowd public programs.json
  - Intigriti community API
  - YesWeHack public API
  - Immunefi explore page (Next.js __NEXT_DATA__)
  - arkadiyt/bounty-targets-data GitHub repo (6 platforms)
  - HackenProof direct scraper
  - OpenBugBounty directory
  - Web search dorking (DuckDuckGo)
  - GitHub security policy search (public API)
  - Web scanner (security.txt, robots.txt, disclosure paths)
  - RFC 9116 security.txt parser
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cores.scope_reader import read_program_scope

logger = logging.getLogger("cateye.bounty_scraper")

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _rate_limit(min_s: float = 1.0, max_s: float = 2.0):
    time.sleep(random.uniform(min_s, max_s))


def _fetch_json(url: str, timeout: int = 20) -> tuple[Any | None, str | None]:
    """Fetch a URL and parse JSON response."""
    try:
        req = urllib.request.Request(url, headers=REQUEST_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body), None
    except urllib.error.HTTPError as e:
        msg = f"HTTP {e.code} fetching {url}: {e.reason}"
        logger.warning("%s", msg)
        return None, msg
    except urllib.error.URLError as e:
        msg = f"URL error fetching {url}: {e.reason}"
        logger.warning("%s", msg)
        return None, msg
    except (json.JSONDecodeError, TypeError) as e:
        msg = f"JSON parse error for {url}: {e}"
        logger.warning("%s", msg)
        return None, msg
    except Exception as e:
        msg = f"Error fetching {url}: {e}"
        logger.warning("%s", msg)
        return None, msg


def _fetch_text(url: str, timeout: int = 20) -> tuple[str | None, str | None]:
    """Fetch a URL and return raw text."""
    try:
        req = urllib.request.Request(url, headers=REQUEST_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return body, None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, f"URL error: {e.reason}"
    except Exception as e:
        return None, str(e)


def _parse_reward_range(text: str) -> tuple[str, float]:
    """Extract max payout from reward range text like '$500 - $10,000'."""
    if not text:
        return "", 0.0
    amounts = re.findall(r"\$?([\d,]+(?:\.\d+)?)", str(text).replace(",", ""))
    parsed = []
    for a in amounts:
        try:
            parsed.append(float(a.replace(",", "")))
        except ValueError:
            continue
    if not parsed:
        return str(text), 0.0
    return str(text), max(parsed)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ScrapedProgram:
    """A program discovered from a public bug bounty listing.

    Extended with additional fields for new discovery sources.
    """
    name: str
    platform: str
    scope_url: str | None = None
    source: str = ""
    domains: list[str] = field(default_factory=list)
    wildcards: list[str] = field(default_factory=list)
    has_rewards: bool = True
    estimated_payout: int = 0
    raw_payout_range: str = ""
    technologies: list[str] = field(default_factory=list)
    program_url: str = ""
    is_new: bool = True
    description: str = ""
    confidence: float = 0.8
    scopes: list[str] = field(default_factory=list)
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

    # ── Immunefi ─────────────────────────────────────────────────────

    def scrape_immunefi(self) -> list[ScrapedProgram]:
        """Scrape Immunefi smart contract bounty programs."""
        results: list[ScrapedProgram] = []
        body, err = _fetch_text("https://immunefi.com/explore/")
        if not body:
            logger.warning("Immunefi: %s", err)
            return results

        try:
            # Try Next.js __NEXT_DATA__ embedded JSON
            match = re.search(
                r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*type=["\']application/json["\'][^>]*>'
                r'(.*?)</script>',
                body, re.DOTALL,
            )
            if match:
                data = json.loads(match.group(1))
                props = data.get("props", {}).get("pageProps", {})
                projects = props.get("projects", props.get("bounties", []))
                for item in projects:
                    name = item.get("name", item.get("project", item.get("title", "")))
                    if not name:
                        continue
                    slug = item.get("slug", item.get("id", name.lower().replace(" ", "-")))
                    payout_raw = item.get("maxPayout", item.get("maximum_payout", item.get("reward", 0)))
                    if isinstance(payout_raw, (int, float)):
                        payout = int(float(payout_raw))
                    else:
                        _, payout = _parse_reward_range(str(payout_raw))
                    techs = item.get("technologies", item.get("techStack", []))
                    if isinstance(techs, str):
                        techs = [t.strip() for t in techs.split(",") if t.strip()]

                    prog = ScrapedProgram(
                        name=name,
                        platform="immunefi",
                        source="immunefi_explore",
                        has_rewards=True,
                        estimated_payout=payout,
                        raw_payout_range=f"${payout:,}" if payout else "",
                        technologies=techs if isinstance(techs, list) else [],
                        program_url=f"https://immunefi.com/bounty/{slug}/",
                        raw_data=item,
                    )
                    results.append(prog)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Immunefi parse error: %s", e)

        # Fallback: regex-based HTML extraction
        if not results:
            cards = re.findall(
                r'<a[^>]*href=["\'](/bounty/[^"\'/]+/)["\'][^>]*>(.*?)</a>',
                body, re.DOTALL,
            )
            for href, title_html in cards:
                name = re.sub(r"<[^>]+>", "", title_html).strip()
                if not name:
                    continue
                results.append(ScrapedProgram(
                    name=name, platform="immunefi",
                    source="immunefi_explore", has_rewards=True,
                    program_url=f"https://immunefi.com{href}",
                ))

        logger.info("Immunefi: %d programs scraped", len(results))
        return results

    # ── BountyTargetsData (arkadiyt GitHub repo) ──────────────────────

    _BOUNTY_TARGETS_DATA_URLS = {
        "hackerone": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/hackerone_data.json",
        "bugcrowd": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/bugcrowd_data.json",
        "intigriti": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/intigriti_data.json",
        "yeswehack": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/yeswehack_data.json",
        "hackenproof": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/hackenproof_data.json",
        "federacy": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/federacy_data.json",
    }

    def scrape_bounty_targets_data(self) -> list[ScrapedProgram]:
        """Scrape curated bounty program data from arkadiyt/bounty-targets-data."""
        results: list[ScrapedProgram] = []
        seen: set[str] = set()

        for platform, url in self._BOUNTY_TARGETS_DATA_URLS.items():
            data, err = _fetch_json(url)
            if not data:
                logger.warning("BountyTargetsData %s: %s", platform, err)
                _rate_limit(0.5, 1.0)
                continue

            items = data if isinstance(data, list) else data.get("programs", [])
            for item in items:
                name = item.get("name") or item.get("program_name") or item.get("title") or ""
                if not name:
                    continue
                prog_url = item.get("url") or item.get("program_url") or item.get("link") or ""
                if not prog_url or prog_url in seen:
                    continue
                seen.add(prog_url)

                _, payout = _parse_reward_range(
                    item.get("bounty", item.get("rewards_range", item.get("payout", "")))
                )
                techs = item.get("technologies", item.get("tech_stack", []))
                if isinstance(techs, str):
                    techs = [t.strip() for t in techs.split(",") if t.strip()]
                scopes_raw = item.get("targets", item.get("scopes", item.get("domains", [])))
                scopes = [s.get("asset_identifier", s) if isinstance(s, dict) else str(s) for s in scopes_raw] if isinstance(scopes_raw, list) else []

                results.append(ScrapedProgram(
                    name=name, platform=platform,
                    source="bounty_targets_data",
                    has_rewards=bool(item.get("offers_bounties", item.get("has_bounty", True))),
                    estimated_payout=int(payout),
                    raw_payout_range=item.get("bounty", ""),
                    technologies=techs,
                    program_url=prog_url,
                    domains=[s for s in scopes if not s.startswith("*.") and s != prog_url],
                    wildcards=[s[2:] for s in scopes if s.startswith("*.")],
                    raw_data=item,
                ))

            _rate_limit(0.5, 1.0)

        logger.info("BountyTargetsData: %d programs across %d platforms", len(results), len(self._BOUNTY_TARGETS_DATA_URLS))
        return results

    # ── Web Scanner: security.txt, robots.txt, disclosure paths ────────

    _DISCLOSURE_PATHS = [
        "/.well-known/security.txt", "/security.txt",
        "/responsible-disclosure", "/bug-bounty", "/security",
        "/report", "/vulnerability-disclosure", "/bugbounty",
        "/security-policy", "/.well-known/security",
    ]

    def scan_domain(self, domain: str) -> ScrapedProgram | None:
        """Scan a single domain for disclosure/bounty paths."""
        found_paths: list[str] = []
        for path in self._DISCLOSURE_PATHS:
            body, _ = _fetch_text(f"https://{domain}{path}", timeout=10)
            if body is not None:
                found_paths.append(path)
            _rate_limit(0.3, 0.8)

        if not found_paths:
            return None
        return ScrapedProgram(
            name=domain, platform="web",
            source="web_scanner",
            has_rewards=True,
            program_url=f"https://{domain}",
            description=f"Disclosure paths: {', '.join(found_paths)}",
            scopes=[f"https://{domain}{p}" for p in found_paths],
            confidence=0.6,
        )

    def scan_domains(self, domains: list[str]) -> list[ScrapedProgram]:
        """Scan multiple domains for disclosure/bounty paths."""
        results: list[ScrapedProgram] = []
        for domain in domains:
            prog = self.scan_domain(domain.strip().lower())
            if prog:
                results.append(prog)
        logger.info("Web scanner: %d/%d domains have disclosure paths", len(results), len(domains))
        return results

    # ── Security.txt parser (RFC 9116) ────────────────────────────────

    def check_security_txt(self, domain: str) -> ScrapedProgram | None:
        """Check domain for RFC 9116 security.txt and parse it."""
        for path in ("/.well-known/security.txt", "/security.txt"):
            body, _ = _fetch_text(f"https://{domain}{path}", timeout=10)
            if not body:
                continue

            fields: dict[str, list[str]] = {}
            for line in body.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, _, value = line.partition(":")
                fields.setdefault(key.strip().lower(), []).append(value.strip())

            contacts = fields.get("contact", [])
            policies = fields.get("policy", [])
            if not contacts:
                return None

            return ScrapedProgram(
                name=domain, platform="web",
                source="security_txt",
                has_rewards=bool(policies),
                program_url=f"https://{domain}",
                description=f"security.txt: {len(contacts)} contact(s), {len(policies)} policy(ies)",
                confidence=0.7,
                scopes=contacts,
                raw_data=fields,
            )
        return None

    def check_security_txt_bulk(self, domains: list[str]) -> list[ScrapedProgram]:
        """Check multiple domains for security.txt files."""
        results: list[ScrapedProgram] = []
        for domain in domains:
            prog = self.check_security_txt(domain.strip().lower())
            if prog:
                results.append(prog)
            _rate_limit(0.5, 1.0)
        logger.info("Security.txt: %d/%d domains have valid security.txt", len(results), len(domains))
        return results

    # ── HackenProof ────────────────────────────────────────────────────

    def scrape_hackenproof(self) -> list[ScrapedProgram]:
        """Scrape public HackenProof programs."""
        results: list[ScrapedProgram] = []
        body, err = _fetch_text("https://hackenproof.com/programs")
        if not body:
            logger.warning("HackenProof: %s", err)
            return results
        try:
            cards = re.findall(
                r'<a[^>]*href=["\'](/program/[^"\'/]+/)["\'][^>]*>\s*<[^>]*>\s*([^<]+)',
                body, re.DOTALL,
            )
            seen: set[str] = set()
            for href, name_html in cards:
                name = re.sub(r"<[^>]+>", "", name_html).strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                results.append(ScrapedProgram(
                    name=name, platform="hackenproof",
                    source="hackenproof_direct", has_rewards=True,
                    program_url=f"https://hackenproof.com{href}",
                    confidence=0.7,
                ))
        except Exception as e:
            logger.warning("HackenProof parse error: %s", e)
        logger.info("HackenProof: %d programs scraped", len(results))
        return results

    # ── OpenBugBounty ──────────────────────────────────────────────────

    def scrape_openbugbounty(self, max_pages: int = 2) -> list[ScrapedProgram]:
        """Scrape public OpenBugBounty programs."""
        results: list[ScrapedProgram] = []
        seen: set[str] = set()
        for page in range(max_pages):
            body, err = _fetch_text(f"https://www.openbugbounty.org/bugbounty/page/{page + 1}/")
            if not body:
                logger.warning("OpenBugBounty page %d: %s", page + 1, err)
                continue
            try:
                for match in re.finditer(
                    r'<a[^>]*href=["\'](/bugbounty/[^"\'/]+/)["\'][^>]*>([^<]+)</a>',
                    body,
                ):
                    name = match.group(2).strip()
                    if not name or name in seen:
                        continue
                    seen.add(name)
                    results.append(ScrapedProgram(
                        name=name, platform="openbugbounty",
                        source="openbugbounty_direct", has_rewards=True,
                        program_url=f"https://www.openbugbounty.org{match.group(1)}",
                        confidence=0.7,
                    ))
            except Exception as e:
                logger.warning("OpenBugBounty parse error page %d: %s", page + 1, e)
        logger.info("OpenBugBounty: %d programs scraped", len(results))
        return results

    # ── Web search dorking (DuckDuckGo) ─────────────────────────────────

    _WEB_SEARCH_QUERIES = [
        '"bug bounty" program rewards',
        '"security.txt" "bounty"',
        'inurl:"/bug-bounty"',
        'inurl:"/responsible-disclosure"',
        '"vulnerability disclosure" program rewards',
        '"bounty program" security researchers',
    ]

    def scrape_web_search(self) -> list[ScrapedProgram]:
        """Search the web for bug bounty programs.

        Uses DuckDuckGo (no API key). Returns empty if search fails.
        """
        results: list[ScrapedProgram] = []
        seen_urls: set[str] = set()

        for query in self._WEB_SEARCH_QUERIES:
            try:
                encoded = urllib.parse.quote(query)
                url = f"https://html.duckduckgo.com/html/?q={encoded}"
                body, err = _fetch_text(url, timeout=8)
                if not body:
                    continue

                for match in re.finditer(
                    r'<a[^>]*class=["\']result__a["\'][^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
                    body,
                ):
                    href = match.group(1)
                    title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
                    domain = urllib.parse.urlparse(href).netloc
                    if any(p in domain for p in [
                        "hackerone.com", "bugcrowd.com", "intigriti.com",
                        "yeswehack.com", "immunefi.com", "hackenproof.com",
                        "openbugbounty.org",
                    ]):
                        continue
                    if not title or href in seen_urls:
                        continue
                    seen_urls.add(href)
                    results.append(ScrapedProgram(
                        name=title[:100], platform="web_search",
                        source="web_search_dorking", has_rewards=True,
                        program_url=href, description=f"Found via: {query}",
                        confidence=0.5,
                    ))
            except Exception:
                pass

        return results

    # ── GitHub security policy search ───────────────────────────────────

    _GITHUB_API_BASE = "https://api.github.com"

    def scrape_github_security(self) -> list[ScrapedProgram]:
        """Search GitHub for repos with security policies mentioning bounties.

        Requires GITHUB_TOKEN env var for authenticated API access.
        Without it, returns empty — GitHub Code Search API requires auth.
        """
        results: list[ScrapedProgram] = []
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            logger.info("GitHub search: skipped (no GITHUB_TOKEN env var)")
            return results

        seen: set[str] = set()
        headers = {**REQUEST_HEADERS, "Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

        queries = [
            "SECURITY.md bounty",
            "security.txt bounty",
            "bug bounty policy in:path:docs",
            "responsible disclosure rewards",
        ]

        def _fetch_json_auth(url: str, timeout: int = 10) -> tuple[Any | None, str | None]:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    return json.loads(body), None
            except urllib.error.HTTPError as e:
                return None, f"HTTP {e.code}"
            except Exception as e:
                return None, str(e)

        for query in queries:
            try:
                encoded = urllib.parse.quote(f"{query} repo:>50 stars")
                url = f"{self._GITHUB_API_BASE}/search/code?q={encoded}&per_page=10"
                data, err = _fetch_json_auth(url)
                if not data:
                    continue

                items = data if isinstance(data, list) else data.get("items", [])
                for item in items:
                    repo_url = item.get("repository", {}).get("html_url", "")
                    repo_name = item.get("repository", {}).get("full_name", "")
                    if not repo_url or repo_name in seen:
                        continue
                    raw_url = item.get("raw_url", "")
                    if raw_url:
                        content, _ = _fetch_text(raw_url)
                        if content and ("bounty" in content.lower() or "reward" in content.lower()):
                            seen.add(repo_name)
                            payout = 0
                            payout_match = re.search(r"\$[\d,]+(?:\.\d+)?", content)
                            if payout_match:
                                payout = int(float(payout_match.group(0).replace(",", "").replace("$", "")))
                            results.append(ScrapedProgram(
                                name=repo_name, platform="github",
                                source="github_security_search", has_rewards=True,
                                estimated_payout=payout,
                                raw_payout_range=f"${payout:,}" if payout else "Not specified",
                                program_url=repo_url,
                                description="GitHub repo with security policy mentioning bounties",
                                confidence=0.5,
                            ))
            except Exception as e:
                logger.warning("GitHub search '%s' failed: %s", query, e)

        logger.info("GitHub: %d programs found", len(results))
        return results

    # ── All platforms ──────────────────────────────────────────────────

    def scrape_all(self, max_pages: int = 2, domains: list[str] | None = None, web_search: bool = True, github_search: bool = True) -> list[ScrapedProgram]:
        """Scrape all supported platforms + optional web scans."""
        all_programs: list[ScrapedProgram] = []
        seen_names: set[str] = set()

        scrapers = [
            ("HackerOne", lambda: self.scrape_hackerone(max_pages)),
            ("Bugcrowd", lambda: self.scrape_bugcrowd(max_pages)),
            ("Intigriti", lambda: self.scrape_intigriti(max(1, max_pages - 1))),
            ("YesWeHack", lambda: self.scrape_yeswehack(max(1, max_pages - 1))),
            ("Immunefi", lambda: self.scrape_immunefi()),
            ("BountyTargetsData", lambda: self.scrape_bounty_targets_data()),
            ("HackenProof", lambda: self.scrape_hackenproof()),
            ("OpenBugBounty", lambda: self.scrape_openbugbounty(max(1, max_pages - 1))),
            ("WebSearch", lambda: self.scrape_web_search() if web_search else []),
            ("GitHub", lambda: self.scrape_github_security() if github_search else []),
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

        # Web scanner for provided domains
        if domains:
            try:
                for prog in self.scan_domains(domains):
                    dedup_key = f"web:{prog.name.lower().strip()}"
                    if dedup_key not in seen_names:
                        seen_names.add(dedup_key)
                        all_programs.append(prog)
                for prog in self.check_security_txt_bulk(domains):
                    dedup_key = f"stxt:{prog.name.lower().strip()}"
                    if dedup_key not in seen_names:
                        seen_names.add(dedup_key)
                        all_programs.append(prog)
            except Exception as e:
                logger.warning("Web scan failed: %s", e)

        self._programs = all_programs
        self._last_refresh = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Total: %d unique reward-offering programs scraped across all sources",
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
