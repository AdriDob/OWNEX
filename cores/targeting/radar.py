"""TargetRadar — ranks targets by expected monetary value (EV).

EV = P(bug) × avg_payout × exploit_ease

Built on top of the existing opportunity scoring pipeline. Does not
replace it — adds the monetary-priority lens the existing scoring
intentionally omits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cores.opportunity.models import Opportunity, OpportunityScore
from cores.opportunity.scoring import score_opportunity

logger = logging.getLogger("catseye.targeting.radar")

WASTE_OF_TIME_THRESHOLD = 0.15


@dataclass
class EVScore:
    expected_value: float       # EV = P(bug) × payout × ease
    probability_estimate: float # P(bug) — based on tech stack + pattern history
    avg_payout: float           # historical payout for similar programs
    exploit_ease: float         # 0.0 (hard) — 1.0 (trivial)
    estimated_hours: float      # time to find & submit
    is_waste_of_time: bool      # below threshold
    reasoning: str              # why this rank

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_value": round(self.expected_value, 4),
            "probability_estimate": round(self.probability_estimate, 4),
            "avg_payout": round(self.avg_payout, 2),
            "exploit_ease": round(self.exploit_ease, 4),
            "estimated_hours": round(self.estimated_hours, 2),
            "is_waste_of_time": self.is_waste_of_time,
            "reasoning": self.reasoning,
        }


@dataclass
class TopTargets:
    generated_at: str
    hot: list[dict[str, Any]]
    cold: list[dict[str, Any]]
    wasted: list[dict[str, Any]]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "hot": self.hot,
            "cold": self.cold,
            "wasted": self.wasted,
            "summary": self.summary,
        }


class TargetRadar:
    def __init__(self) -> None:
        self._payout_estimates: dict[str, float] = {
            "web": 500.0, "api": 800.0, "mobile": 400.0,
            "web3": 1500.0, "cloud": 1000.0, "hardware": 300.0,
            "other": 200.0,
        }
        self._ease_by_tech: dict[str, float] = {
            "rest": 0.8, "graphql": 0.6, "oauth": 0.7,
            "jwt": 0.75, "saml": 0.5, "mobile": 0.6,
            "web3": 0.4, "cloud": 0.3, "kubernetes": 0.3,
            "docker": 0.5, "api": 0.8,
        }

    def rank(self, opportunities: list[Opportunity]) -> TopTargets:
        scored: list[tuple[EVScore, Opportunity]] = []
        for opp in opportunities:
            ev = self._compute_ev(opp)
            scored.append((ev, opp))

        scored.sort(key=lambda x: x[0].expected_value, reverse=True)

        hot: list[dict[str, Any]] = []
        cold: list[dict[str, Any]] = []
        wasted: list[dict[str, Any]] = []
        for ev, opp in scored:
            entry = {
                "name": opp.name,
                "url": opp.source.url,
                "category": opp.category,
                "ev_score": ev.to_dict(),
            }
            if ev.is_waste_of_time:
                wasted.append(entry)
            elif ev.expected_value >= 0.4:
                hot.append(entry)
            else:
                cold.append(entry)

        summary_parts = []
        if hot:
            top_ev = hot[0].get("ev_score", {})
            summary_parts.append(f"Top: {hot[0]['name']} (EV {top_ev.get('expected_value', 0):.2f})")
        if wasted:
            summary_parts.append(f"Skip: {len(wasted)} targets below threshold")
        summary_parts.append(f"{len(scored)} targets ranked")
        if hot:
            estimated = sum(float(h.get("ev_score", {}).get("estimated_hours", 0)) for h in hot[:5])
            summary_parts.append(f"Top 5 estimated: {estimated:.1f}h total")

        return TopTargets(
            generated_at=datetime.now(timezone.utc).isoformat(),
            hot=hot[:10],
            cold=cold[:10],
            wasted=wasted[:10],
            summary=" | ".join(summary_parts),
        )

    def _compute_ev(self, opp: Opportunity) -> EVScore:
        opp_score = score_opportunity(opp)

        prob = self._estimate_probability(opp, opp_score)
        payout = self._estimate_payout(opp)
        ease = self._estimate_exploit_ease(opp)
        ev = prob * payout * ease

        hours = self._estimate_hours(opp, ease)
        ev_per_hour = ev / max(hours, 0.5)

        parts = [
            f"P(bug)={prob:.2f}",
            f"payout=${payout:.0f}",
            f"ease={ease:.2f}",
            f"EV=${ev:.0f}",
            f"~{hours:.1f}h",
            f"${ev_per_hour:.0f}/h",
        ]

        return EVScore(
            expected_value=ev_per_hour,
            probability_estimate=prob,
            avg_payout=payout,
            exploit_ease=ease,
            estimated_hours=hours,
            is_waste_of_time=ev_per_hour < WASTE_OF_TIME_THRESHOLD,
            reasoning=" | ".join(parts),
        )

    def _estimate_probability(self, opp: Opportunity, score: OpportunityScore) -> float:
        base = score.reward_potential * 0.3 + score.technology_overlap * 0.3 + score.freshness * 0.2
        if opp.category == "web3":
            base *= 0.7
        if opp.category == "research":
            base *= 0.4
        return max(0.05, min(0.95, base))

    def _estimate_payout(self, opp: Opportunity) -> float:
        text = (opp.reward_info or "").lower()
        for kw, val in [("$1,000,000", 1000000), ("$500,000", 500000),
                         ("$100,000", 100000), ("$10,000", 10000),
                         ("$5,000", 5000), ("$1,000", 1000)]:
            if kw in text:
                return val
        techs = [t.lower() for t in opp.technology_tags]
        for tech in techs:
            if tech in self._payout_estimates:
                return self._payout_estimates[tech]
        return 300.0

    def _estimate_exploit_ease(self, opp: Opportunity) -> float:
        score = 0.5
        techs = [t.lower() for t in opp.technology_tags]
        if not techs:
            return score
        for tech in techs:
            if tech in self._ease_by_tech:
                score = max(score, self._ease_by_tech[tech])
        if opp.category == "web3":
            score *= 0.6
        return max(0.1, min(1.0, score))

    def _estimate_hours(self, opp: Opportunity, ease: float) -> float:
        base = 3.0
        if ease > 0.7:
            base = 1.5
        elif ease < 0.3:
            base = 6.0
        if opp.category == "web3":
            base += 2.0
        return base
