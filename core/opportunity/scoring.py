from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

from database import db
from database.models import Finding
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


def _difficulty_bucket(d: float) -> str:
    """Bucket a difficulty float into a scoring bucket key.

    - >= 0.7 -> "high"
    - in [0.4, 0.7) -> "med"
    - in [0.25, 0.4) -> "hit_rate"
    - < 0.25 -> "low"
    """
    if d >= 0.7:
        return "high"
    if d >= 0.4:
        return "med"
    if d >= 0.25:
        return "hit_rate"
    return "low"


class PersonalHistoryTracker:
    """Learning from user acceptance/rejection feedback."""

    def __init__(self, user_id: int | None = None) -> None:
        self.user_id = user_id
        self.factors: dict[str, float] = {
            "critical_hit_rate": 0.5,
            "high_hit_rate": 0.3,
            "medium_hit_rate": 0.2,
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
            severity = _normalize_severity(finding.severity)
            key = f"{severity}_hit_rate"
            self.factors[key] = min(1.0, self.factors.get(key, 0.3) + 0.05)
        finally:
            session.close()

    def on_reject(self, finding_id: int, reward: float, difficulty: float) -> None:
        session = db.SessionLocal()
        try:
            finding = session.query(Finding).filter(Finding.id == finding_id).first()
            if not finding:
                return
            severity = _normalize_severity(finding.severity)
            key = f"{severity}_hit_rate"
            self.factors[key] = max(0.0, self.factors.get(key, 0.1) - 0.05)
        finally:
            session.close()

    def get_personal_factor(self, severity: str, difficulty: float) -> float:
        """Return the personal multiplier for a severity/difficulty pair.

        Reads ``{severity}_{difficulty_bucket}`` from the learning factors,
        falling back to 1.0 when no history exists. The ``difficulty`` is not
        normalized so callers may pass the raw stored value.
        """
        bucket = _difficulty_bucket(difficulty)
        return self.factors.get(f"{severity}_{bucket}", 1.0)


def _normalize_severity(s: str) -> str:
    s = (s or "").lower()
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


# Base reward for opportunities without a program/tier.
_REWARD_BASE_MAP = {"critical": 5000, "high": 2000, "medium": 500, "low": 100, "info": 50}

# Severity multiplier applied to bounty-tier max rewards.
_TIER_SEV_MULT = {"critical": 1.0, "high": 0.7, "medium": 0.3, "low": 0.1, "info": 0.05}

# Default multiplier used for the no-program fallback (info opportunities are tiny).
_FALLBACK_SEV_MULT = {"info": 0.05}


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
                reward = self._estimate_reward(f, session=session)
                difficulty = f.difficulty or 0.3
                acceptance_prob = f.confidence or 0.5

                target = getattr(f, "target", None)
                program_id = getattr(target, "program_id", 0) or 0

                evh = (reward * acceptance_prob) / max(f.estimated_effort_hours or 2.0, 0.5)

                personal = self.tracker.get_personal_factor(_normalize_severity(f.severity), difficulty)

                candidate = UnifiedScore(
                    opportunity_id=f.id,
                    target_id=f.target_id,
                    program_id=program_id,
                    title=f.title or f"Finding #{f.id}",
                    severity=_normalize_severity(f.severity),
                    reward=reward,
                    difficulty=difficulty,
                    acceptance_prob=acceptance_prob,
                    evh=evh,
                    diversity_bonus=1.0,
                    personal_factor=personal,
                )
                candidates.append(candidate)

            candidates.sort(key=lambda c: c.final_score, reverse=True)
            return candidates[:limit]
        finally:
            session.close()

    def _estimate_reward(self, finding: Finding, session=None) -> float:
        """Estimate the monetary reward for a finding.

        Uses the bounty tier with the highest ``max_reward`` when the finding
        belongs to a program with tiers, otherwise falls back to a per-severity
        base map (with a small 0.05 multiplier for ``info``/unknown severities).
        """
        owns_session = session is None
        session = session or db.SessionLocal()
        try:
            raw_severity = (finding.severity or "").lower()
            severity = _normalize_severity(raw_severity)
            is_known = raw_severity in _REWARD_BASE_MAP
            target = getattr(finding, "target", None)
            pid = getattr(target, "program_id", None) if target else None
            program = session.query(Program).filter(Program.id == pid).first() if pid is not None else None
            if program:
                tier = session.query(BountyTier).filter(BountyTier.program_id == program.id).first()
                if tier:
                    return round((tier.max_reward or 0) * _TIER_SEV_MULT.get(severity, 0.05), 2)

            # Fallback with no program/tiers: known severities use their base map
            # value at full weight; unknown severities collapse to the small
            # info tier (base 50 * 0.05 = 2.5).
            if is_known:
                return float(_REWARD_BASE_MAP[severity])
            return _REWARD_BASE_MAP["info"] * _FALLBACK_SEV_MULT["info"]
        finally:
            if owns_session:
                session.close()

    def get_top5_by_domain(self, limit: int = 50) -> list[Top5Entry]:
        candidates = self.compute_opportunities(limit)
        return self.top5.compute(candidates)

    def record_feedback(self, finding_id: int, outcome: str | FeedbackOutcome) -> None:
        outcome_str = outcome.value if isinstance(outcome, FeedbackOutcome) else outcome
        if outcome_str == "accept":
            session = db.SessionLocal()
            try:
                finding = session.query(Finding).filter(Finding.id == finding_id).first()
                if finding:
                    self.tracker.on_accept(
                        finding_id, self._estimate_reward(finding, session=session), finding.difficulty or 0.3
                    )
            finally:
                session.close()
        elif outcome_str == "reject":
            session = db.SessionLocal()
            try:
                finding = session.query(Finding).filter(Finding.id == finding_id).first()
                if finding:
                    self.tracker.on_reject(
                        finding_id, self._estimate_reward(finding, session=session), finding.difficulty or 0.3
                    )
            finally:
                session.close()
        else:
            raise ValueError(f"Invalid outcome: {outcome_str}")


class FeedbackOutcome(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


_ENGINE: OpportunityEngine | None = None


def get_engine() -> OpportunityEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = OpportunityEngine()
    return _ENGINE
