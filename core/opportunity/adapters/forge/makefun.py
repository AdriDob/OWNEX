"""make.fun adapter — AI-agent coding competitions with USDC/Solana prizes.

Public JSON API (no key needed for reads): GET /api/competitions returns
paginated items with reward pot, deadline, skills, entry counts and the
per-place reward breakdown. Entries are graded in a sandbox; payout is
USDC on Solana to winners only — advertised pot is NOT expected income.

Terms caveat surfaced in metadata: entries require a public repo + AI
transcripts and grant make.fun a broad license — never submit proprietary
OWNEX code.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("ownex.adapters.forge.makefun")

API_URL = "https://make.fun/api/competitions"
_UA = {
    "User-Agent": "OWNEX/1.0 (+https://github.com/AdriDob/OWNEX)",
    "Accept": "application/json",
}
_PAGE_LIMIT = 50
_MAX_PAGES = 3


def _parse_deadline(raw: Any) -> str:
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).isoformat()
    except (TypeError, ValueError):
        return ""


def _top_rewards(item: dict[str, Any]) -> list[dict[str, str]]:
    rewards = item.get("rewardsNow") or []
    return [
        {"place": str(r.get("place")), "amount_usd": str(r.get("amountUsd") or "")}
        for r in rewards[:5]
        if isinstance(r, dict)
    ]


def _to_raw(item: dict[str, Any]) -> dict[str, Any] | None:
    slug = str(item.get("slug") or item.get("id") or "")
    if not slug:
        return None
    deadline = _parse_deadline(item.get("deadline"))
    if deadline:
        try:
            if datetime.fromisoformat(deadline) < datetime.now(UTC):
                return None  # closed competition
        except ValueError:
            pass
    pot = item.get("potUsd") or item.get("rewardAmount") or 0
    try:
        reward = float(pot)
    except (TypeError, ValueError):
        reward = 0.0
    skills = [str(s) for s in (item.get("skills") or [])][:8]
    title = str(item.get("title") or slug)[:300]
    description = str(item.get("description") or "")[:2000]
    sponsor = item.get("sponsor") or {}
    return {
        "id": f"makefun_{slug}",
        "name": title,
        "description": description,
        "platform": "makefun",
        "url": f"https://make.fun/bounty/{slug}",
        "reward": reward,
        "currency": "USD",  # paid in USDC on Solana
        "effort_hours": 12.0,
        "tags": ["ai_competition", "usdc", "solana", "makefun", *skills],
        "cycle": "forge",
        "source_type": "competition",
        "source_name": "makefun",
        "metadata": {
            "original": {
                "slug": slug,
                "deadline": deadline,
                "submission_count": item.get("submissionCount"),
                "category": item.get("category"),
                "skills": skills,
                "pot_usd": str(pot),
                "top_rewards": _top_rewards(item),
                "entry_fee_usd": item.get("entryFeeUsd"),
                "sponsor": sponsor.get("name") if isinstance(sponsor, dict) else None,
                "paid_by_position_only": True,
                "requires_public_repo_and_ai_transcripts": True,
            }
        },
        "created_at": str(item.get("publishedAt") or ""),
    }


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch open make.fun competitions from the public API."""
    out: list[dict[str, Any]] = []
    cursor = ""
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=_UA) as client:
            for _ in range(_MAX_PAGES):
                params: dict[str, Any] = {"limit": _PAGE_LIMIT}
                if cursor:
                    params["cursor"] = cursor
                resp = await client.get(API_URL, params=params)
                if resp.status_code != 200:
                    logger.warning(
                        "make.fun competitions returned %s", resp.status_code
                    )
                    break
                data = resp.json()
                items = data.get("items") or []
                for item in items:
                    raw = _to_raw(item)
                    if raw:
                        out.append(raw)
                cursor = str(data.get("next_cursor") or data.get("nextCursor") or "")
                if not cursor or not items:
                    break
    except Exception as exc:
        logger.warning("make.fun fetch failed: %s", exc)
        return []
    logger.info("make.fun: %d open competitions", len(out))
    return out[:60]
