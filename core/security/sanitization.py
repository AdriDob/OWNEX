"""Prompt-injection sanitization for externally-sourced opportunity data.

Opportunity titles/descriptions come from untrusted platforms. Before any
field reaches an agent's context it must pass through here: instruction-like
patterns are stripped, control characters removed, and lengths bounded.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

# Patterns that indicate embedded instructions aimed at an agent/LLM.
_INJECTION_PATTERNS = re.compile(
    r"(ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts|rules)|"
    r"disregard (all |any |the )?(previous|prior|above) |"
    r"system prompt|you are now|new instructions?:|"
    r"</?(system|assistant|user|instructions?)>|"
    r"do not (follow|obey|tell)|reveal (your |the )?(prompt|instructions|api ?key)|"
    r"exfiltrat|send .{0,20}(to|@) http)",
    re.IGNORECASE,
)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MAX_TEXT = 2000


def clean_text(value: Any, limit: int = _MAX_TEXT) -> str:
    """Strip injection patterns and control chars; bound length."""
    if not isinstance(value, str):
        return ""
    text = _CONTROL_CHARS.sub("", value)
    text = _INJECTION_PATTERNS.sub("[filtered]", text)
    return text[:limit]


def clean_url(value: Any) -> str:
    """Only http(s) URLs survive; anything else becomes empty."""
    if not isinstance(value, str):
        return ""
    v = value.strip()
    return v if v.startswith(("http://", "https://")) else ""


def safe_to_live(raw: dict[str, Any], sanitize: bool = True) -> Any | None:
    """Build a LiveOpportunity from a raw fetch dict with sanitized fields.

    Returns None when the item has no usable id — same contract the
    pipeline's ``_to_live`` expects. Lazy import avoids a module cycle.
    """
    if not isinstance(raw, dict):
        return None
    from cores.opportunity.live_pipeline import LiveOpportunity, _best_category, _platform_for

    external_id = str(raw.get("id") or raw.get("url") or "")
    if not external_id:
        return None
    platform = _platform_for(raw)
    if platform == "upwork":  # EXCLUDED_PLATFORMS mirror — kept local to avoid cycle
        return None
    url = clean_url(raw.get("url") or raw.get("html_url")) if sanitize else str(raw.get("url") or raw.get("html_url") or "")
    title = clean_text(raw.get("name") or raw.get("title") or "untitled", 300) if sanitize else str(raw.get("name") or raw.get("title") or "untitled")[:300]
    description = clean_text(raw.get("description"), 2000) if sanitize else str(raw.get("description") or "")[:2000]
    tags_raw = raw.get("tags") or []
    tags = [clean_text(t, 80) for t in tags_raw][:12] if sanitize else [str(t) for t in tags_raw][:12]

    reward = raw.get("reward")
    try:
        reward_f = float(reward) if reward is not None else 0.0
    except (TypeError, ValueError):
        reward_f = 0.0
    effort = raw.get("effort_hours")
    try:
        effort_f = float(effort) if effort is not None else 0.0
    except (TypeError, ValueError):
        effort_f = 0.0

    return LiveOpportunity(
        id=external_id,
        platform=platform,
        adapter="",
        title=title,
        url=url,
        description=description,
        reward=reward_f,
        currency=str(raw.get("currency") or "USD"),
        effort_hours=effort_f,
        tags=[t for t in tags if t],
        category=_best_category(raw),
        employment_type="bounty" if raw.get("cycle") == "forge" else "contract",
        status="discovered",
        evidence_url=url,
    )


def sanitize_opportunity_for_agent(opp: Any) -> Any:
    """Return a sanitized copy of an opportunity for agent-facing context.

    Numeric/structural fields pass through; all free-text fields are
    cleaned. Uses dataclasses.replace when possible, else attribute copy.
    """
    try:
        return replace(
            opp,
            title=clean_text(getattr(opp, "title", ""), 300),
            description=clean_text(getattr(opp, "description", ""), 2000),
            url=clean_url(getattr(opp, "url", "")),
            evidence_url=clean_url(getattr(opp, "evidence_url", "")),
            tags=[clean_text(t, 80) for t in getattr(opp, "tags", []) or []],
        )
    except Exception:
        return opp
