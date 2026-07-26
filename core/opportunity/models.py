from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PersonalHistory:
    personal_acceptance_rate: float = 0.0
    personal_avg_payout: float = 0.0
    personal_avg_days: float = 0.0
    personal_competition_level: float = 0.5
    total_submissions: int = 0
    total_accepted: int = 0
    by_platform: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_vuln_type: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class UnifiedScore:
    expected_value: float = 0.0
    acceptance_probability: float = 0.0
    speed_days: float = 0.0
    difficulty: float = 0.5
    competition: float = 0.5
    personal_fit: float = 0.5
    confidence: float = 0.5
    overall: float = 0.0

    def reasoning(self) -> list[str]:
        r: list[str] = []
        r.append(f"EV= ${self.expected_value:.2f}")
        r.append(f"acceptance= {self.acceptance_probability:.0%}")
        r.append(f"speed= {self.speed_days:.0f}d")
        r.append(f"difficulty= {self.difficulty:.2f}")
        r.append(f"competition= {self.competition:.2f}")
        r.append(f"fit= {self.personal_fit:.2f}")
        r.append(f"confidence= {self.confidence:.0%}")
        r.append(f"overall= {self.overall:.4f}")
        return r


OWNEX_WORK_CYCLES = {
    "security": "🔵 Rastro — Security Research",
    "forge": "🟣 Forge — Dev Bounty",
    "pulse": "🟢 Pulse — AI Work",
    "vault": "🟡 Vault — Wealth",
    "atlas": "⚪ Atlas — Intelligence",
}

OWNEX_WORK_CYCLE_ORDER = ["security", "forge", "pulse", "vault", "atlas"]


@dataclass
class ScoredOpportunity:
    id: str
    name: str
    cycle: str
    source_type: str
    source_name: str
    reward: float
    effort_hours: float
    platform: str
    technology_tags: list[str]
    url: str | None
    created_at: str
    score: UnifiedScore
    original: Any | None = None


@dataclass
class Top5Recommendation:
    ranked: list[ScoredOpportunity]
    generated_at: str
    total_scored: int
    diversification_note: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_scored": self.total_scored,
            "diversification_note": self.diversification_note,
            "summary": self.summary,
            "top5": [
                {
                    "id": opp.id,
                    "name": opp.name,
                    "cycle": opp.cycle,
                    "source_type": opp.source_type,
                    "source_name": opp.source_name,
                    "reward": opp.reward,
                    "effort_hours": opp.effort_hours,
                    "platform": opp.platform,
                    "url": opp.url,
                    "score": {
                        "overall": opp.score.overall,
                        "expected_value": opp.score.expected_value,
                        "acceptance_probability": opp.score.acceptance_probability,
                        "speed_days": opp.score.speed_days,
                        "difficulty": opp.score.difficulty,
                        "competition": opp.score.competition,
                        "personal_fit": opp.score.personal_fit,
                        "confidence": opp.score.confidence,
                        "reasoning": opp.score.reasoning(),
                    },
                }
                for opp in self.ranked
            ],
        }
