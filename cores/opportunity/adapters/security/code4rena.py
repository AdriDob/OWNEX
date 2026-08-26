"""Code4rena Adapter — Security Work Cycle.

Web3 audit contest platform. No public REST API: contest data is embedded
in the Next.js App Router RSC payload of code4rena.com/contests. This
adapter extracts per-contest JSON fragments from the streamed chunks and
degrades to an empty list on any structural change.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.code4rena")

C4_CONTESTS_URL = "https://code4rena.com/contests"
_C4_CHUNK_RE = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.DOTALL)
# Campos por nombre (no por índice de chunk — los índices cambian por build).
# Limitación documentada: se extraen los campos que aparecen DESPUÉS de
# contestId dentro del mismo fragmento RSC (title/status/dates/amount lo hacen).
_FIELD_RE = r'"([a-zA-Z_]+)":("(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?|true|false|null)'
_WINDOW = 2500
_ACTIVE_STATUSES = {"live", "reporting", "upcoming"}
_AMOUNT_RE = re.compile(r"([\d,]+(?:\.\d+)?)")


def _unquote(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].encode().decode("unicode_escape")
    return value


def _extract_contests_from_html(html: str) -> list[dict[str, Any]]:
    """Extract contest dicts from RSC chunks containing a ``contestId`` field."""
    contests: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for chunk_match in _C4_CHUNK_RE.finditer(html):
        chunk = chunk_match.group(1)
        if "contestId" not in chunk:
            continue
        try:
            decoded = chunk.encode().decode("unicode_escape")
        except (UnicodeDecodeError, ValueError):
            continue
        for id_match in re.finditer(r'"contestId":(\d+)', decoded):
            contest_id = id_match.group(1)
            if contest_id in seen_ids:
                continue
            window = decoded[id_match.start() : id_match.start() + _WINDOW]
            pairs = dict(re.findall(_FIELD_RE, window))
            title = _unquote(pairs.get("title", "")).strip()
            if not title:
                continue
            seen_ids.add(contest_id)
            contests.append(
                {
                    "contest_id": contest_id,
                    "title": title,
                    "status": _unquote(pairs.get("status", "")),
                    "start_time": _unquote(pairs.get("startTime", "")),
                    "end_time": _unquote(pairs.get("endTime", "")),
                    "amount_label": _unquote(pairs.get("formattedAmount", "")),
                    "league": _unquote(pairs.get("league", "")),
                    "slug": _unquote(pairs.get("slug", "")),
                }
            )
    return contests


def _parse_amount(label: str) -> float:
    match = _AMOUNT_RE.search(label or "")
    if match is None:
        return 0.0
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return 0.0


class Code4renaAdapter(OpportunityAdapter):
    """Adapter for Code4rena web3 audit contests via RSC payload extraction."""

    platform: str = "code4rena"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._url = self.config.get("contests_url") or C4_CONTESTS_URL
        self._headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(self._url, headers=self._headers)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.warning("[Code4rena] fetch error: %s", exc)
            return []

        raw_opps: list[RawOpportunity] = []
        for contest in _extract_contests_from_html(html):
            status = contest["status"].lower()
            if status and status not in _ACTIVE_STATUSES:
                continue
            slug = contest["slug"] or contest["contest_id"]
            league_tag = [contest["league"].lower()] if contest["league"] else []

            raw_opps.append(
                RawOpportunity(
                    id=f"code4rena_{contest['contest_id']}",
                    name=contest["title"],
                    description=f"Code4rena audit contest: {contest['title']}"
                    + (f" ({contest['league']})" if contest["league"] else ""),
                    platform="code4rena",
                    url=f"https://code4rena.com/contests/{slug}",
                    reward=_parse_amount(contest["amount_label"]),
                    effort_hours=10.0,
                    tags=["web3", "smart-contracts", "audit-contest", *league_tag],
                    cycle="security",
                    source_type="platform",
                    source_name="code4rena",
                    metadata={"original": contest, "personal": personal},
                )
            )

        logger.info("[Code4rena] %d contests fetched", len(raw_opps))
        return raw_opps
