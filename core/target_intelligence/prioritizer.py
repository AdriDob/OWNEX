"""Target Prioritizer — expected value × attack plan per target.

Connects revenue history, acceptance prediction, tech fingerprinting,
and recon strategies into a unified target prioritization system.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.priority.ev_engine import EVResult, compute_ev

logger = logging.getLogger("ownex.target_intelligence.prioritizer")

TECH_TO_VULN: dict[str, list[str]] = {
    "api": ["idor", "auth_bypass"],
    "rest": ["idor", "auth_bypass"],
    "graphql": ["idor", "injection", "auth_bypass"],
    "aws": ["ssrf"],
    "gcp": ["ssrf"],
    "azure": ["ssrf"],
    "cloud": ["ssrf"],
    "react": ["xss"],
    "vue": ["xss"],
    "angular": ["xss"],
    "wordpress": ["xss", "sqli"],
    "spring": ["idor", "auth_bypass", "sqli"],
    "django": ["idor", "sqli", "xss"],
    "laravel": ["sqli", "xss", "idor"],
    "php": ["sqli", "xss", "idor"],
    "jwt": ["auth_bypass"],
    "oauth": ["auth_bypass"],
    "docker": ["ssrf"],
    "mysql": ["sqli"],
    "postgres": ["sqli"],
    "mongo": ["sqli"],
}

TECH_EFFORT_HOURS: dict[str, float] = {
    "graphql": 1.0,
    "wordpress": 1.0,
    "express": 1.5,
    "laravel": 1.5,
    "django": 1.5,
    "fastapi": 1.5,
    "react": 2.0,
    "vue": 2.0,
    "spring": 2.5,
    "api": 1.5,
}

_TECH_PHASE_MAP: dict[str, list[str]] = {
    "graphql": ["discover", "recon", "hypothesis", "promote", "validate", "report"],
    "react": ["discover", "recon", "hypothesis", "promote", "validate", "report"],
    "wordpress": ["discover", "recon", "hypothesis", "promote", "report"],
    "api": ["discover", "recon", "hypothesis", "promote", "validate", "report"],
}

_PLATFORM_DOMAINS: dict[str, str] = {
    "hackerone.com": "hackerone",
    "bugcrowd.com": "bugcrowd",
    "intigriti.com": "intigriti",
    "yeswehack.com": "yeswehack",
    "immunefi.com": "immunefi",
    "synack.com": "synack",
    "hackerone": "hackerone",
    "bugcrowd": "bugcrowd",
    "intigriti": "intigriti",
    "yeswehack": "yeswehack",
    "immunefi": "immunefi",
    "synack": "synack",
    "hackenproof": "hackenproof",
}

_PLATFORM_PAYOUT_DAYS: dict[str, float] = {
    "hackerone": 30.0,
    "bugcrowd": 45.0,
    "intigriti": 21.0,
    "yeswehack": 30.0,
    "immunefi": 60.0,
    "synack": 45.0,
}


def compute_tech_adjustment(tech_tags: str, adjustments: dict[str, float]) -> float:
    if not tech_tags:
        return 1.0
    tags_lower = tech_tags.lower()
    best = 1.0
    for tag, vulns in TECH_TO_VULN.items():
        if tag in tags_lower:
            for v in vulns:
                vadj = adjustments.get(v, 1.0)
                if vadj > best:
                    best = vadj
    return best


@dataclass
class AttackPlan:
    strategies: list[str] = field(default_factory=list)
    estimated_hours: float = 0.0
    phases_to_run: list[str] = field(
        default_factory=lambda: ["discover", "recon", "hypothesis", "promote", "validate", "report"]
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategies": self.strategies,
            "estimated_hours": self.estimated_hours,
            "phases_to_run": list(self.phases_to_run),
        }


@dataclass
class PriorityResult:
    target_id: int
    target_name: str
    expected_value: float
    estimated_reward: float
    acceptance_probability: float
    speed_multiplier: float
    confidence: float
    ev_detail: EVResult
    attack_plan: AttackPlan = field(default_factory=AttackPlan)
    priority_score: float = 0.0
    usd_per_hour: float = 0.0
    platform: str | None = None

    def __post_init__(self) -> None:
        if self.priority_score == 0.0:
            object.__setattr__(self, "priority_score", max(0.1, min(self.expected_value / 50.0, 10.0)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "expected_value": round(self.expected_value, 2),
            "estimated_reward": self.estimated_reward,
            "acceptance_probability": round(self.acceptance_probability, 3),
            "priority_score": round(self.priority_score, 2),
            "usd_per_hour": round(self.usd_per_hour, 2),
            "platform": self.platform,
            "ev_detail": {"reasoning": self.ev_detail.reasoning, "breakdown": self.ev_detail.breakdown},
            "attack_plan": self.attack_plan.to_dict(),
        }


class TargetPrioritizer:
    def __init__(self) -> None:
        self._fingerprinter: Any = None
        self._revenue_metrics: Any = None

    def _load_metrics(self) -> None:
        if self._revenue_metrics is None:
            from core.revenue.metrics import RevenueMetrics

            self._revenue_metrics = RevenueMetrics()

    def prioritize(
        self,
        targets: list[Any],
        target_intel_map: dict[int, Any],
        adjustments: dict[str, float] | None = None,
    ) -> tuple[dict[int, float], list[PriorityResult]]:
        self._load_metrics()
        priority_dict: dict[int, float] = {}
        results: list[PriorityResult] = []

        for tgt in targets:
            intel = target_intel_map.get(tgt.id)
            if intel is None:
                priority_dict[tgt.id] = 1.0
                continue

            reward = self._estimate_reward(intel)
            platform = self._detect_platform(tgt, intel)
            speed_days = self._estimate_speed(platform)
            tech_adjustment = compute_tech_adjustment(intel.technology_tags or "", adjustments or {})
            surface = 0.8 + (intel.attack_surface_score or 0.0) * 0.2

            ev = compute_ev(
                estimated_reward=reward,
                platform=platform,
                speed_days=speed_days,
                confidence=intel.reward_confidence or 0.5,
            )

            adjusted_ev = ev.expected_value * tech_adjustment * surface
            plan = self._build_attack_plan(intel)
            usd_per_hour = round(reward / max(plan.estimated_hours, 0.5), 2)

            result = PriorityResult(
                target_id=tgt.id,
                target_name=tgt.name or "",
                expected_value=adjusted_ev,
                estimated_reward=reward,
                acceptance_probability=ev.acceptance_probability,
                speed_multiplier=ev.speed_multiplier,
                confidence=ev.confidence,
                ev_detail=ev,
                attack_plan=plan,
                usd_per_hour=usd_per_hour,
                platform=platform,
            )
            results.append(result)
            priority_dict[tgt.id] = round(result.priority_score, 2)

        results.sort(key=lambda r: -r.priority_score)
        return priority_dict, results

    def _estimate_reward(self, intel: Any) -> float:
        base = float(intel.reward_score) if intel.reward_score and intel.reward_score > 0 else 500.0

        try:
            self._load_metrics()
            prog_url = (intel.program_url or "").lower()
            for prog in self._revenue_metrics.roi_by_program():
                if prog_url and (prog["program"].lower() in prog_url or prog_url in prog["program"].lower()):
                    avg = prog["total_payout"] / max(prog["count"], 1)
                    return (base + avg) / 2
        except Exception:
            logger.debug("Could not load program ROI metrics", exc_info=True)

        return base

    def _detect_platform(self, target: Any, intel: Any) -> str | None:
        url = (
            intel.program_url or getattr(target, "program_url", None) or getattr(target, "domain", None) or ""
        ).lower()
        for domain_key, platform_name in _PLATFORM_DOMAINS.items():
            if domain_key in url:
                return platform_name
        return None

    def _estimate_speed(self, platform: str | None) -> float | None:
        try:
            self._load_metrics()
            dynamic = self._revenue_metrics.platform_speed_days()
            if platform and platform in dynamic:
                return dynamic[platform]
        except Exception:
            logger.debug("Could not load dynamic platform speed", exc_info=True)
        if platform and platform in _PLATFORM_PAYOUT_DAYS:
            return _PLATFORM_PAYOUT_DAYS[platform]
        return None

    def _build_attack_plan(self, intel: Any) -> AttackPlan:
        tech_tags = (intel.technology_tags or "").lower()
        matched_strategies: list[str] = []

        for tech in TECH_EFFORT_HOURS:
            if tech in tech_tags:
                matched_strategies.append(tech)

        estimated_hours = sum(TECH_EFFORT_HOURS.get(s, 1.5) for s in matched_strategies) or 1.5

        phases: list[str] = ["discover", "recon", "hypothesis", "promote"]
        for tech in matched_strategies:
            tech_phases = _TECH_PHASE_MAP.get(tech, ["validate", "report"])
            for p in tech_phases:
                if p not in phases:
                    phases.append(p)

        return AttackPlan(strategies=matched_strategies, estimated_hours=estimated_hours, phases_to_run=phases)
