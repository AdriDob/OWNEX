"""Expected Value Engine — reward × acceptance_prob × speed_of_payout.

Provides a unified, reusable EV calculator for every prioritization need:
- Reports (which report to submit first)
- Hypotheses (which vulnerability type to test first)
- Targets (which program to hunt first)
- Opportunities (which opportunity to pursue first)

All inputs are optional with sensible defaults so it can be used anywhere
without complex setup, while remaining precise when real data is available.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("orion.core.priority.ev")

# Speed-of-payout multipliers: faster = higher EV
_SPEED_MULTIPLIERS = {
    "immediate": 1.5,  # hours
    "today": 1.3,  # 1 day
    "this_week": 1.0,  # baseline
    "this_month": 0.8,  # 30 days
    "quarter": 0.5,  # 90 days
    "slow": 0.3,  # 6+ months
}

# Baseline acceptance probabilities by platform when no history is available
_BASE_ACCEPTANCE = {
    "hackerone": 0.35,
    "bugcrowd": 0.30,
    "immunefi": 0.25,
    "intigriti": 0.40,
    "yeswehack": 0.30,
    "synack": 0.20,
    "code4rena": 0.15,
}


def _speed_multiplier(eta_days: float | None) -> float:
    """Map an estimated ETA in days to a speed multiplier."""
    if eta_days is None:
        return _SPEED_MULTIPLIERS["this_week"]
    if eta_days < 1:
        return _SPEED_MULTIPLIERS["today"]
    if eta_days < 7:
        return _SPEED_MULTIPLIERS["this_week"]
    if eta_days < 30:
        return _SPEED_MULTIPLIERS["this_month"]
    if eta_days < 90:
        return _SPEED_MULTIPLIERS["quarter"]
    return _SPEED_MULTIPLIERS["slow"]


@dataclass
class EVResult:
    """Result of an expected value calculation."""

    expected_value: float
    estimated_reward: float
    acceptance_probability: float
    speed_multiplier: float
    confidence: float
    reasoning: str
    breakdown: dict[str, Any]


def compute_ev(
    estimated_reward: float = 0.0,
    acceptance_probability: float | None = None,
    speed_days: float | None = None,
    confidence: float = 0.5,
    platform: str | None = None,
    vulnerability_type: str | None = None,
    historical_success_count: int = 0,
    historical_total_count: int = 0,
) -> EVResult:
    """Compute expected value = reward × acceptance_prob × speed.

    Args:
        estimated_reward: Dollar amount expected for a successful outcome.
        acceptance_probability: Override probability (0-1). Auto-estimated if None.
        speed_days: Estimated days until payout. Auto-mapped if None.
        confidence: Confidence in the estimate (0-1), used to discount EV.
        platform: Platform name for base acceptance rate lookup.
        vulnerability_type: Vuln type for acceptance rate adjustment.
        historical_success_count: Number of accepted submissions for this context.
        historical_total_count: Total submissions for this context.

    """
    parts: list[str] = []
    values: dict[str, float] = {}

    # 1. Acceptance probability
    if acceptance_probability is not None:
        prob = max(0.0, min(1.0, acceptance_probability))
        parts.append(f"acceptance_prob={prob:.0%} (provided)")
    else:
        prob = 0.3  # global default
        if platform and platform in _BASE_ACCEPTANCE:
            prob = _BASE_ACCEPTANCE[platform]
        if historical_total_count > 0:
            historical_rate = historical_success_count / historical_total_count
            prob = (prob + historical_rate) / 2  # blend base + personal history
        base_prob = _BASE_ACCEPTANCE.get(platform, 0.3) if platform else 0.3
        parts.append(f"acceptance_prob={prob:.0%} (base={base_prob:.0%})")
    values["acceptance_probability"] = prob

    # 2. Speed multiplier
    speed = _speed_multiplier(speed_days)
    values["speed_multiplier"] = speed
    eta_tag = (
        "immediate"
        if speed_days is not None and speed_days < 1
        else "within_week"
        if speed_days is not None and speed_days < 7
        else "within_month"
        if speed_days is not None and speed_days < 30
        else "within_quarter"
        if speed_days is not None and speed_days < 90
        else "slow"
    )
    parts.append(f"speed={speed:.1f}x ({eta_tag})")

    # 3. Confidence discount
    confidence = max(0.0, min(1.0, confidence))
    values["confidence"] = confidence

    # 4. Expected value
    ev = estimated_reward * prob * speed * confidence
    values["estimated_reward"] = estimated_reward

    parts.append(f"reward=${estimated_reward:.0f} × {prob:.0%} × {speed:.1f}x × {confidence:.0%} = ${ev:.2f}")

    return EVResult(
        expected_value=round(ev, 2),
        estimated_reward=estimated_reward,
        acceptance_probability=prob,
        speed_multiplier=speed,
        confidence=confidence,
        reasoning=" | ".join(parts),
        breakdown=values,
    )


def rank(
    items: list[dict[str, Any]],
    reward_key: str = "estimated_reward",
    platform_key: str = "platform",
    vuln_key: str = "vulnerability_type",
) -> list[dict[str, Any]]:
    """Rank a list of items by expected value, injecting EVResult into each."""
    scored: list[dict[str, Any]] = []
    for item in items:
        reward = float(item.get(reward_key, 0))
        platform = item.get(platform_key)
        vuln = item.get(vuln_key)
        ev = compute_ev(
            estimated_reward=reward,
            platform=platform,
            vulnerability_type=vuln,
        )
        scored.append({**item, "_ev": ev})
    scored.sort(key=lambda x: x["_ev"].expected_value, reverse=True)
    return scored
