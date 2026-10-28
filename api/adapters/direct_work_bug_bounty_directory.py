"""Bug bounty programs — multi-platform discovery adapter.

Why this file exists
--------------------
145 sources in the catalog are ACTIVE with zero experience and no interview,
and 77 of them are bug-bounty platforms. Until now the only way to reach
them was `bugbounty` (public dataset endpoints), which returns nothing
useful without credentials — so the highest-density lane in the whole
catalog was unreachable in practice.

What it reads
-------------
Each platform's **public program directory** — the same pages a researcher
opens in a browser. No auth, no bypass, no fingerprint evasion:

| Platform       | URL                                          |
|----------------|----------------------------------------------|
| Intigriti      | `intigriti.com/programs`                     |
| Bugcrowd       | `bugcrowd.com/engagements`                  |
| YesWeHack      | `yeswehack.com/programs`                     |

Honesty rules encoded here
--------------------------
- **A program with no published range is skipped**, never emitted as
  `$0`: a range we cannot read is UNKNOWN, not zero.
- Only the platform's own public page is the source of the figure. A
  number scraped from a third-party aggregator is not evidence.
- The platform-level `max_reward` is what a program advertises; it is
  NOT money already earned. A bug bounty is per-report, so these enter
  the radar rather than the deliverable bank.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    EntryMechanism,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.bug_bounty_directory")

_USER_AGENT = "Mozilla/5.0 (compatible; ownex-discovery/1.0)"

#: Above this the figure is not a bug bounty (it is a corporate max or a
#: parsing artifact). Measured ceiling in the directories: ~$150k.
_MAX_PROGRAM_REWARD_USD = 1_000_000.0

#: `$1,200`, `$5,500`, `$1.5M`, `$200` — a bare number is NOT a range.
_AMOUNT_RE = re.compile(r"\$\s*(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?")
_CURRENCY_WORD_RE = re.compile(r"\$\s*(\d[\d,]*)")


class _Platform:
    """One public program directory."""

    __slots__ = ("name", "platform", "list_url", "link_re")

    def __init__(self, name: str, platform: WorkPlatform, list_url: str, link_re: str) -> None:
        self.name = name
        self.platform = platform
        self.list_url = list_url
        self.link_re = link_re


#: Only platforms whose directory was verified to expose a **per-program**
#: range that can be attributed to that program (measured 2026-10-01):
#:
#:  · Intigriti — split on the program link isolates the card, so
#:    `$75 – $15,000` is provably Adobe's own range.
#:
#: Excluded on purpose, NOT for lack of effort:
#:  · Bugcrowd — the engagements page returns 200/111 KB but publishes no
#:    parseable per-program figure.
#:  · YesWeHack — 200/366 KB with ranges, but the markup does not isolate
#:    one program per link, so a number cannot be attributed to a program.
#:    Attributing it anyway is exactly the fabrication this project has
#:    spent two sessions removing. Re-add when the page is parseable.
PLATFORMS: tuple[_Platform, ...] = (
    _Platform(
        "intigriti",
        WorkPlatform.INTIGRITI,
        "https://intigriti.com/programs",
        r'href="(https://app\.intigriti\.com/programs/[^"#?]+)"',
    ),
)


class BugBountyDirectoryDweAdapter(BaseDiscoveryAdapter):
    """Reads public program directories of the main bug bounty platforms."""

    def __init__(self, platform: _Platform | None = None, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._platform = platform or PLATFORMS[0]
        source = DiscoverySource(
            name=self._platform.name,
            platform=self._platform.platform,
            categories=[OpportunityCategory.BUG_BOUNTY],
            tier=1,
            analysis_cadence_hours=24,
            requires_auth=False,
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Read the directory once. One platform per adapter instance."""
        try:
            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
            ) as client:
                resp = await client.get(self._platform.list_url)
        except Exception as exc:  # noqa: BLE001 — discovery must never raise
            logger.warning("%s: fetch failed: %s", self._platform.name, exc)
            return []
        if resp.status_code != 200:
            logger.warning("%s: HTTP %s", self._platform.name, resp.status_code)
            return []

        opps = self._parse(resp.text)
        logger.info("%s: %d programs with a published range", self._platform.name, len(opps))
        return opps

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=20, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
            ) as client:
                resp = await client.get(self._platform.list_url)
            return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    # ── Parsing ───────────────────────────────────────────────────────

    def _parse(self, html: str) -> list[Opportunity]:
        """One opportunity per program segment that publishes a range.

        The directory is a server-rendered grid where each card is
        `href="…/programs/<owner>/<slug>" … <name> … $low – $high`.
        We **split on the link** and read the range from that program's own
        segment: a fixed-size window was measured wrong (distance from
        link to its figure ranged 1 017–24 624 chars, so a window either
        missed most programs or borrowed another program's number).
        """
        out: list[Opportunity] = []
        seen: set[str] = set()
        for segment in re.split(f"(?={self._platform.link_re})", html)[1:]:
            link = re.match(self._platform.link_re, segment)
            if not link:
                continue
            href = link.group(1)
            if href in seen:
                continue
            reward = self._published_reward(segment)
            if reward <= 0.0:
                continue  # UNKNOWN range ⇒ skip, never emit $0
            seen.add(href)
            opp = self._build(href, reward, segment)
            if opp is not None:
                out.append(opp)
        return out

    @staticmethod
    def _published_reward(text: str) -> float:
        """Top of the program's advertised range. 0.0 = UNKNOWN.

        The directories render `$75 – $15,000`: the FIRST figure is the
        floor, not the ceiling. Reporting the floor as "up to $X" would
        understate, and reporting the first figure while labelling it a
        maximum is simply wrong — so we take the maximum of the range and
        say so in the description.
        """
        amounts: list[float] = []
        for match in _AMOUNT_RE.finditer(text):
            raw, suffix = match.group(1), match.group(2)
            try:
                amount = float(raw.replace(",", ""))
            except ValueError:
                continue
            if suffix:
                amount *= {"k": 1_000.0, "m": 1_000_000.0}[suffix.lower()]
            if 0.0 < amount <= _MAX_PROGRAM_REWARD_USD:
                amounts.append(amount)
        if not amounts:
            return 0.0
        return max(amounts)

    def _build(self, href: str, reward: float, segment: str = "") -> Opportunity | None:
        url = href if href.startswith("http") else _absolute(self._platform, href)
        label = self._program_label(href, segment)
        if not label:
            return None
        return self._create_opportunity(
            external_id=href,
            title=f"[{self._platform.name}] {label}",
            category=OpportunityCategory.BUG_BOUNTY,
            url=url,
            description=(
                f"Public bug bounty program on {self._platform.name}. "
                f"Advertised range up to ${reward:,.0f}. Paid per accepted report."
            ),
            company=label.split("/")[0] if "/" in label else label,
            country="Global",
            payment=reward,
            currency="USD",
            payment_method=PaymentMethod.OTHER,
            difficulty=DifficultyLevel.INTERMEDIATE,
            language_required="english",
            # UNKNOWN until the program states it: inventing the denominator
            # of a $/h is how a bounty board becomes fake pipeline.
            estimated_time_hours=0.0,
            experience_required=ExperienceLevel.NONE,
            portfolio_required=False,
            interview_required=False,
            technical_test_required=False,
            registration_required=True,
            asynchronous=True,
            employment_type=EmploymentType.CONTRACT,
            entry_mechanism=EntryMechanism.REGISTRATION,
            payment_proven=True,  # the platform's payout is documented
            international_payment=True,
        )

    @staticmethod
    def _program_label(href: str, segment: str = "") -> str:
        """Human name of the program.

        Preferred: the `<h4>`/title text inside the program's own segment
        (the URL slug is a poor label: yeswehack's `/programs/x` yielded
        "Programs" for every entry). Falls back to the owner slug.
        """
        if segment:
            heading = re.search(r"<h[1-6][^>]*>([^<]{3,60})</h[1-6]>", segment)
            if heading:
                name = heading.group(1).strip()
                if name and name.lower() not in {"programs", "program", "engagements"}:
                    return name
        parts = [p for p in href.split("/") if p and not p.endswith(".com")]
        if len(parts) < 2:
            return ""
        return parts[-2].replace("-", " ").replace("_", " ").strip().title()


def _absolute(platform: _Platform, href: str) -> str:
    base = platform.list_url.split("/programs")[0].split("/engagements")[0].rstrip("/")
    return f"{base}{href}" if href.startswith("/") else href


def build_bug_bounty_directory_adapters() -> list[BugBountyDirectoryDweAdapter]:
    """One adapter per verified-reachable public directory."""
    return [BugBountyDirectoryDweAdapter(p) for p in PLATFORMS]
