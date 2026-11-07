"""ETHGlobal adapter — discover hackathons and paid competitions.

ethglobal.com/events is server-rendered; each event is an <a href="/events/...">
card with name, dates, location and type badge. No public JSON API (api.ethglobal.com
is Cloudflare-protected), so we parse the SSR HTML.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from html import unescape
from typing import Any

import httpx

logger = logging.getLogger("ownex.adapters.forge.ethglobal")

EVENTS_URL = "https://ethglobal.com/events"
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) OWNEX/1.0", "Accept": "text/html"}

_CARD_RE = re.compile(r'<a[^>]+href="(/events/[a-zA-Z0-9_-]+)"[^>]*>(.*?)</a>', re.S)
_NAME_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S)
_NAME2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)
_TIME_RE = re.compile(r"<time[^>]*>(.*?)</time>", re.S)
_LOC_RE = re.compile(r'<div class="flex-4 hidden md:flex flex-col">\s*<p[^>]*>(.*?)</p>\s*<p[^>]*>(.*?)</p>', re.S)
_TYPE_RE = re.compile(r'rounded-sm">([^<]+)</div>')
_TAG_RE = re.compile(r"<[^>]+>")
_MONTH_RE = re.compile(
    r">(January|February|March|April|May|June|July|August|September|October|November|December)<"
)
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_TYPE2_RE = re.compile(r"(IRL Hackathon|Hackathon|Summit|Conference|Meetup)")
_LOC2_RE = re.compile(r">([A-Z][A-Za-z .'-]{1,40},\s*[A-Z][A-Za-z .'-]{1,40})<")
_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

_PRIZE_HINTS = {
    "hackathon": 5000.0,
    "summit": 0.0,
    "meetup": 0.0,
    "conference": 0.0,
}


def _clean(fragment: str) -> str:
    return unescape(_TAG_RE.sub("", fragment)).strip()


def _parse_events(html: str) -> list[dict[str, Any]]:
    # The page renders "Upcoming" then a "Past" section with the same card
    # markup — truncate before it so only upcoming events are parsed.
    past_idx = html.find(">Past<")
    if past_idx > 0:
        html = html[:past_idx]
    events: list[dict[str, Any]] = []
    for href, card in _CARD_RE.findall(html):
        slug = href.rsplit("/", 1)[-1]
        name_m = _NAME_RE.search(card) or _NAME2_RE.search(card)
        if not name_m:
            continue
        name = _clean(name_m.group(1))
        times = [_clean(t) for t in _TIME_RE.findall(card)]
        loc_m = _LOC_RE.search(card)
        location = _clean(loc_m.group(1)) if loc_m else ""
        country = _clean(loc_m.group(2)) if loc_m else ""
        type_m = _TYPE_RE.search(card)
        event_type = _clean(type_m.group(1)).lower() if type_m else ""

        # Upcoming banner cards use a calendar widget instead of <time>
        # tags: month name + day numbers, year embedded in the event name.
        deadline = ""
        if not times:
            month_m = _MONTH_RE.search(card)
            year_m = _YEAR_RE.search(name) or _YEAR_RE.search(slug.replace("-", " "))
            if month_m and year_m:
                year = int(year_m.group(1))
                day_m = re.search(r'<span class="">(\d{1,2})</span>', card[month_m.end() :])
                day = day_m.group(1) if day_m else "1"
                month_num = _MONTHS.index(month_m.group(1)) + 1
                try:
                    deadline = datetime(year, month_num, int(day), tzinfo=UTC).date().isoformat()
                except ValueError:
                    deadline = ""
            tm2 = _TYPE2_RE.search(_clean(card))
            if tm2:
                event_type = tm2.group(1).lower()
            loc2 = _LOC2_RE.search(re.sub(r"<!--.*?-->", "", card))
            if loc2:
                parts = [p.strip() for p in loc2.group(1).split(",", 1)]
                location = parts[0]
                country = parts[1] if len(parts) > 1 else ""
        if not event_type:
            event_type = "event"
        if "hackathon" in event_type:
            event_type = "hackathon"

        # Skip past events. Cards show dates without a year for future
        # editions (e.g. "Apr 14" meaning 2027) — roll forward a year
        # when the parsed date already passed.
        today = datetime.now(UTC).date()
        if not deadline:
            for t in reversed(times):
                for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d", "%B %d"):
                    try:
                        dt = datetime.strptime(
                            t.replace("th", "").replace("st", "").replace("nd", "").replace("rd", ""), fmt
                        )
                        year = dt.year if dt.year != 1900 else today.year
                        cand = datetime(year, dt.month, dt.day, tzinfo=UTC).date()
                        if cand < today:
                            cand = datetime(year + 1, dt.month, dt.day, tzinfo=UTC).date()
                        deadline = cand.isoformat()
                        break
                    except ValueError:
                        continue
                if deadline:
                    break

        slug = href.rsplit("/", 1)[-1]
        if deadline and deadline < today.isoformat():
            continue
        events.append(
            {
                "id": f"ethglobal_{slug}",
                "name": name,
                "description": f"ETHGlobal {event_type}: {name} — {', '.join(times)} — {location}, {country}".strip(", "),
                "platform": "ethglobal",
                "url": f"https://ethglobal.com{href}",
                "reward": _PRIZE_HINTS.get(event_type, 0.0),
                "effort_hours": 40.0 if event_type == "hackathon" else 8.0,
                "tags": ["web3", "hackathon" if event_type == "hackathon" else event_type, "ethereum"],
                "cycle": "forge",
                "source_type": "competition",
                "source_name": "ethglobal",
                "metadata": {
                    "original": {
                        "event_type": event_type,
                        "dates": times,
                        "location": location,
                        "country": country,
                        "deadline": deadline,
                    }
                },
                "created_at": "",
            }
        )
    return events


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch upcoming ETHGlobal events from the SSR events page."""
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=_UA) as client:
            resp = await client.get(EVENTS_URL)
            if resp.status_code != 200:
                logger.warning("ETHGlobal events page returned %s", resp.status_code)
                return []
            events = _parse_events(resp.text)
    except Exception as exc:
        logger.warning("ETHGlobal fetch failed: %s", exc)
        return []

    # Keep only hackathons (paid prize competitions); drop pure meetups/cons.
    paid = [e for e in events if e["metadata"]["original"]["event_type"] == "hackathon"]
    logger.info("ETHGlobal: %d hackathons found", len(paid))
    return paid[:20]
