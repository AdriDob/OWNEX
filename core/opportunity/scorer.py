from __future__ import annotations

import logging
from math import exp

from core.opportunity.models import PersonalHistory, ScoredOpportunity, UnifiedScore
from core.priority.ev_engine import compute_ev

logger = logging.getLogger("ownex.opportunity.scorer")

_DIFFICULTY_TAGS: dict[str, float] = {
    "web3": 0.8,
    "solidity": 0.85,
    "rust": 0.75,
    "move": 0.8,
    "reverse.engineering": 0.85,
    "firmware": 0.8,
    "hardware": 0.8,
    "llm": 0.7,
    "ai": 0.65,
    "ml": 0.65,
    "kubernetes": 0.6,
    "docker": 0.45,
    "cloud": 0.5,
    "graphql": 0.45,
    "api": 0.35,
    "rest": 0.3,
    "mobile": 0.5,
    "ios": 0.55,
    "android": 0.55,
}

_EASY_TAGS: set[str] = {
    "xss",
    "csrf",
    "cors",
    "clickjacking",
    "open.redirect",
    "information.disclosure",
    "missing.header",
}

_REWARD_SOURCE_MULTIPLIERS: dict[str, float] = {
    "hackerone": 0.8,
    "bugcrowd": 0.7,
    "immunefi": 1.5,
    "intigriti": 0.6,
    "yeswehack": 0.6,
    "code4rena": 1.2,
    "superteam": 1.0,
    "opire": 0.8,
    "linkedin": 0.5,
    "freelancer": 0.5,
    "coingecko": 0.3,
    "firefly": 0.3,
}


def _sigmoid(x: float, midpoint: float = 0.5, steepness: float = 5.0) -> float:
    return 1.0 / (1.0 + exp(-steepness * (x - midpoint)))


def _estimate_difficulty(tags: list[str]) -> float:
    tag_set = set(t.lower().replace(" ", "_") for t in tags)
    score = 0.4
    for tag, diff in _DIFFICULTY_TAGS.items():
        if any(tag in t for t in tag_set):
            score = max(score, diff)
    if tag_set & _EASY_TAGS:
        score = min(score, 0.3)
    return max(0.0, min(1.0, score))


def _estimate_competition(platform: str, personal: PersonalHistory) -> float:
    base = 0.5
    platform_lower = platform.lower()
    if platform_lower in ("hackerone", "bugcrowd", "immunefi"):
        base = 0.7
    elif platform_lower in ("intigriti", "yeswehack", "code4rena"):
        base = 0.6
    elif platform_lower in ("superteam", "opire"):
        base = 0.4
    elif platform_lower in ("linkedin", "freelancer", "coingecko"):
        base = 0.3
    plat_data = personal.by_platform.get(platform_lower, {})
    plat_total = plat_data.get("total", 0) if plat_data else 0
    if plat_total >= 3:
        plat_rate = plat_data.get("acceptance_rate", 0.5) if plat_data else 0.5
        return max(0.0, min(1.0, (base + (1.0 - plat_rate)) / 2))
    return base


def _personal_fit(tags: list[str], personal: PersonalHistory) -> float:
    tag_set = set(t.lower().replace(" ", "_") for t in tags)
    if not tag_set:
        return 0.5
    if not personal.by_vuln_type:
        simple_ratio = sum(1 for t in tag_set if t in _EASY_TAGS) / max(len(tag_set), 1)
        return 0.3 + simple_ratio * 0.4
    proven_types = set(personal.by_vuln_type.keys())
    proven_lower = set(k.lower().replace(" ", "_") for k in proven_types)
    overlap = tag_set & proven_lower
    if overlap:
        return min(1.0, 0.3 + len(overlap) * 0.15)
    return 0.3


def score_opportunity(
    opp_id: str,
    name: str,
    cycle: str,
    source_type: str,
    source_name: str,
    reward: float,
    effort_hours: float,
    platform: str,
    technology_tags: list[str] | None = None,
    url: str | None = None,
    created_at: str = "",
    personal: PersonalHistory | None = None,
    original: object | None = None,
) -> ScoredOpportunity:
    tags = technology_tags or []
    ph = personal or PersonalHistory()

    difficulty = _estimate_difficulty(tags)
    competition = _estimate_competition(platform, ph)
    fit = _personal_fit(tags, ph)

    plat_acceptance = ph.by_platform.get(platform.lower(), {})
    plat_accepted = plat_acceptance.get("accepted", 0) if plat_acceptance else 0
    plat_total = plat_acceptance.get("total", 0) if plat_acceptance else 0

    ev_result = compute_ev(
        estimated_reward=reward,
        platform=platform,
        speed_days=effort_hours * 2 if effort_hours else None,
        confidence=1.0 - difficulty * 0.3,
        historical_success_count=plat_accepted,
        historical_total_count=plat_total,
    )

    ev = ev_result.expected_value
    prob = ev_result.acceptance_probability
    speed = effort_hours * 2 if effort_hours else 30.0

    ev_norm = _sigmoid(ev / 100.0, midpoint=0.3)
    prob_norm = prob
    diff_norm = 1.0 - difficulty
    comp_norm = 1.0 - competition
    fit_norm = fit
    speed_norm = _sigmoid(1.0 / max(speed, 1), midpoint=0.1)

    overall = (
        0.30 * ev_norm
        + 0.15 * prob_norm
        + 0.10 * diff_norm
        + 0.10 * comp_norm
        + 0.10 * fit_norm
        + 0.05 * speed_norm
        + 0.20 * (ev_norm * prob_norm)
    )
    overall = max(0.0, min(1.0, overall))

    score = UnifiedScore(
        expected_value=round(ev, 2),
        acceptance_probability=round(prob, 3),
        speed_days=round(speed, 1),
        difficulty=round(difficulty, 3),
        competition=round(competition, 3),
        personal_fit=round(fit, 3),
        confidence=round(ev_result.confidence, 3),
        overall=round(overall, 4),
    )

    return ScoredOpportunity(
        id=opp_id,
        name=name,
        cycle=cycle,
        source_type=source_type,
        source_name=source_name,
        reward=round(reward, 2),
        effort_hours=round(effort_hours, 1),
        platform=platform,
        technology_tags=tags,
        url=url,
        created_at=created_at,
        score=score,
        original=original,
    )
