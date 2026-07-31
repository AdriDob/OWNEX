from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

from database import db
from database.models import Finding, Target
from database.models_economic import BountyTier, Program

logger = logging.getLogger("opportunity_engine")


@dataclass
class UnifiedScore:
    """A single opportunity score based on reward, difficulty, and acceptance."""

    opportunity_id: int
    target_id: int
    program_id: int
    title: str
    severity: str
    reward: float
    difficulty: float
    acceptance_prob: float
    evh: float  # Expected Value per Hour
    diversity_bonus: float = 0.0
    personal_factor: float = 1.0
    final_score: float = 0.0

    def __post_init__(self) -> None:
        self.final_score = (
            self.reward * self.acceptance_prob * (1.0 - self.difficulty) * self.diversity_bonus * self.personal_factor
        )


@dataclass
class Top5Entry:
    """Top 5 engine result per business domain."""

    domain: str
    entries: list[UnifiedScore] = field(default_factory=list)
    total_score: float = 0.0

    def __post_init__(self) -> None:
        self.total_score = sum(e.final_score for e in self.entries)


class Top5Engine:
    """Diversified selection: top 5 unique domains per portfolio."""

    def __init__(self) -> None:
        self.domains_cache: dict[str, float] = {}

    def compute(self, candidates: list[UnifiedScore]) -> list[Top5Entry]:
        for c in candidates:
            title = c.title.lower()
            domain = title.split()[0] if title.split() else "general"
            self.domains_cache[domain] = self.domains_cache.get(domain, 0.0) + c.final_score

        sorted_domains = sorted(self.domains_cache.items(), key=lambda kv: kv[1], reverse=True)
        top_domains = [d for d, _ in sorted_domains[:5]]

        result = []
        for domain in top_domains:
            domain_candidates = [c for c in candidates if c.title.lower().split()[0] == domain]
            domain_candidates.sort(key=lambda c: c.final_score, reverse=True)
            result.append(Top5Entry(domain=domain, entries=domain_candidates))

        return result


class PersonalHistoryTracker:
    """Learning from user acceptance/rejection feedback."""

    def __init__(self, user_id: int | None = None) -> None:
        self.user_id = user_id
        self.factors: dict[str, float] = {
            "critical_hit_rate": 0.5,
            "medium_hit_rate": 0.3,
            "low_hit_rate": 0.1,
            "retry_boost": 1.2,
            "avoid_boost": 0.5,
        }

    def on_accept(self, finding_id: int, reward: float, difficulty: float) -> None:
        session = db.SessionLocal()
        try:
            finding = session.query(Finding).filter(Finding.id == finding_id).first()
            if not finding:
                return
            key = f"{finding.severity}_{finding.difficulty}"
            self.factors[key] = self.factors.get(key, 0.0) + 0.05
        finally:
            session.close()

    def on_reject(self, finding_id: int, reward: float, difficulty: float) -> None:
        session = db.SessionLocal()
        try:
            finding = session.query(Finding).filter(Finding.id == finding_id).first()
            if not finding:
                return
            key = f"{finding.severity}_{finding.difficulty}"
            self.factors[key] = max(0.0, self.factors.get(key, 0.0) - 0.05)
        finally:
            session.close()

    def get_personal_factor(self, severity: str, difficulty: float) -> float:
        key = f"{severity}_{difficulty}"
        return self.factors.get(key, 1.0)


def _normalize_severity(s: str) -> str:
    s = s.lower()
    if s in {"critical", "high", "medium", "low", "info"}:
        return s
    if s.startswith("crit"):
        return "critical"
    if s.startswith("high"):
        return "high"
    if s.startswith("medium") or s.startswith("med"):
        return "medium"
    if s.startswith("low") or s == "lo":
        return "low"
    if s.startswith("info") or s.startswith("information") or s == "inf":
        return "info"
    return "medium"


class OpportunityEngine:
    """Main orchestrator for scoring and prioritization."""

    def __init__(self) -> None:
        self.unified_scorer = UnifiedScore
        self.top5 = Top5Engine()
        self.tracker = PersonalHistoryTracker()

    def compute_opportunities(self, limit: int = 50) -> list[UnifiedScore]:
        session = db.SessionLocal()
        try:
            findings = session.query(Finding).filter(Finding.status == "confirmed").all()
            candidates = []
            for f in findings:
                reward = self._estimate_reward(f)
                difficulty = f.difficulty or 0.3
                acceptance_prob = f.confidence or 0.5

                target = session.query(Target).filter(Target.id == f.target_id).first()
                program = session.query(Program).filter(Program.id == target.program_id).first() if target else None

                evh = (reward * acceptance_prob) / max(f.estimated_effort_hours or 2.0, 0.5)

                personal = self.tracker.get_personal_factor(_normalize_severity(f.severity), difficulty)

                candidate = UnifiedScore(
                    opportunity_id=f.id,
                    target_id=f.target_id,
                    program_id=program.id if program else 0,
                    title=f.title or f"Finding #{f.id}",
                    severity=_normalize_severity(f.severity),
                    reward=reward,
                    difficulty=difficulty,
                    acceptance_prob=acceptance_prob,
                    evh=evh,
                    personal_factor=personal,
                )
                candidates.append(candidate)

            candidates.sort(key=lambda c: c.final_score, reverse=True)
            return candidates[:limit]
        finally:
            session.close()

    def _estimate_reward(self, finding: Finding) -> float:
        session = db.SessionLocal()
        try:
            program = (
                session.query(Program).filter(Program.id == finding.target.program_id).first()
                if finding.target
                else None
            )
            if program:
                tiers = session.query(BountyTier).filter(BountyTier.program_id == program.id).all()
                if tiers:
                    max_tier = max(tiers, key=lambda t: t.max_reward or 0)
                    sev_mult = {"critical": 1.0, "high": 0.7, "medium": 0.3, "low": 0.1, "info": 0.05}
                    base = max_tier.max_reward or 0
                    severity = _normalize_severity(finding.severity)
                    return round(base * sev_mult.get(severity, 0.1), 2)

            base_map = {"critical": 5000, "high": 2000, "medium": 500, "low": 100, "info": 50}
            return base_map.get(_normalize_severity(finding.severity), 100)
        finally:
            session.close()

    def get_top5_by_domain(self, limit: int = 50) -> list[Top5Entry]:
        candidates = self.compute_opportunities(limit)
        return self.top5.compute(candidates)

    def record_feedback(self, finding_id: int, outcome: FeedbackOutcome) -> None:
        if outcome == "accept":
            session = db.SessionLocal()
            try:
                finding = session.query(Finding).filter(Finding.id == finding_id).first()
                if finding:
                    self.tracker.on_accept(finding_id, self._estimate_reward(finding), finding.difficulty or 0.3)
            finally:
                session.close()
        elif outcome == "reject":
            session = db.SessionLocal()
            try:
                finding = session.query(Finding).filter(Finding.id == finding_id).first()
                if finding:
                    self.tracker.on_reject(finding_id, self._estimate_reward(finding), finding.difficulty or 0.3)
            finally:
                session.close()


class FeedbackOutcome(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


_ENGINE: OpportunityEngine | None = None


def get_engine() -> OpportunityEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = OpportunityEngine()
    return _ENGINE
