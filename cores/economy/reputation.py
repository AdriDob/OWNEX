from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import RLock
from typing import Any


class ReputationEventType(str, Enum):
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    DISPUTE_WON = "dispute_won"
    DISPUTE_LOST = "dispute_lost"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_SENT = "payment_sent"
    REVIEW_RECEIVED = "review_received"
    STAKE_INCREASED = "stake_increased"
    STAKE_DECREASED = "stake_decreased"
    SLA_MET = "sla_met"
    SLA_MISSED = "sla_missed"


@dataclass(slots=True)
class ReputationEvent:
    agent_id: str
    event_type: ReputationEventType
    delta: float
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    related_entity_id: str | None = None


@dataclass(slots=True)
class ReputationSnapshot:
    agent_id: str
    score: float
    percentile: float
    tier: str
    components: dict[str, float]
    calculated_at: datetime = field(default_factory=datetime.utcnow)


class ReputationEngine:
    BASE_SCORE = 100.0
    MAX_SCORE = 1000.0
    MIN_SCORE = 0.0

    WEIGHTS = {
        ReputationEventType.JOB_COMPLETED: 2.0,
        ReputationEventType.JOB_FAILED: -5.0,
        ReputationEventType.DISPUTE_WON: 10.0,
        ReputationEventType.DISPUTE_LOST: -15.0,
        ReputationEventType.PAYMENT_RECEIVED: 1.0,
        ReputationEventType.PAYMENT_SENT: 0.5,
        ReputationEventType.REVIEW_RECEIVED: 3.0,
        ReputationEventType.STAKE_INCREASED: 0.1,
        ReputationEventType.STAKE_DECREASED: -0.1,
        ReputationEventType.SLA_MET: 1.5,
        ReputationEventType.SLA_MISSED: -3.0,
    }

    DECAY_HALF_LIFE_DAYS = 90
    TIME_WEIGHT = 0.3
    VOLUME_WEIGHT = 0.2
    QUALITY_WEIGHT = 0.5

    TIERS = [
        (900, "legendary"),
        (750, "elite"),
        (600, "master"),
        (450, "expert"),
        (300, "professional"),
        (200, "verified"),
        (100, "novice"),
        (0, "newbie"),
    ]

    def __init__(self):
        self._scores: dict[str, float] = {}
        self._events: dict[str, list[ReputationEvent]] = {}
        self._lock = RLock()

    def get_score(self, agent_id: str) -> float:
        with self._lock:
            return self._scores.get(agent_id, self.BASE_SCORE)

    def record_event(self, event: ReputationEvent) -> float:
        with self._lock:
            self._events.setdefault(event.agent_id, []).append(event)
            current = self._scores.get(event.agent_id, self.BASE_SCORE)
            weight = self.WEIGHTS.get(event.event_type, 1.0)
            new_score = max(self.MIN_SCORE, min(self.MAX_SCORE, current + event.delta * weight))
            self._scores[event.agent_id] = new_score
            return new_score

    def apply_decay(self, agent_id: str, now: datetime | None = None) -> float:
        now = now or datetime.utcnow()
        with self._lock:
            events = self._events.get(agent_id, [])
            if not events:
                return self._scores.get(agent_id, self.BASE_SCORE)
            current = self._scores.get(agent_id, self.BASE_SCORE)
            total_weight = 0.0
            weighted_sum = 0.0
            for event in events:
                age_days = (now - event.timestamp).days
                if age_days <= 0:
                    continue
                decay_factor = 0.5 ** (age_days / self.DECAY_HALF_LIFE_DAYS)
                weight = self.WEIGHTS.get(event.event_type, 1.0) * decay_factor
                total_weight += weight
                weighted_sum += event.delta * weight
            if total_weight == 0:
                return current
            decayed = self.BASE_SCORE + weighted_sum
            new_score = max(self.MIN_SCORE, min(self.MAX_SCORE, decayed))
            self._scores[agent_id] = new_score
            return new_score

    def get_percentile(self, agent_id: str) -> float:
        with self._lock:
            score = self._scores.get(agent_id, self.BASE_SCORE)
            all_scores = list(self._scores.values())
            if not all_scores:
                return 50.0
            below = sum(1 for s in all_scores if s < score)
            return (below / len(all_scores)) * 100.0

    def get_tier(self, score: float) -> str:
        for threshold, tier in self.TIERS:
            if score >= threshold:
                return tier
        return "newbie"

    def get_snapshot(self, agent_id: str) -> ReputationSnapshot:
        with self._lock:
            score = self.get_score(agent_id)
            events = self._events.get(agent_id, [])
            recent = [e for e in events if (datetime.utcnow() - e.timestamp).days <= 30]
            completed = len([e for e in recent if e.event_type == ReputationEventType.JOB_COMPLETED])
            failed = len([e for e in recent if e.event_type == ReputationEventType.JOB_FAILED])
            disputes_won = len([e for e in recent if e.event_type == ReputationEventType.DISPUTE_WON])
            disputes_lost = len([e for e in recent if e.event_type == ReputationEventType.DISPUTE_LOST])
            total_recent = completed + failed + disputes_won + disputes_lost
            success_rate = (completed + disputes_won) / total_recent if total_recent > 0 else 1.0
            components = {
                "volume": min(1.0, len(events) / 100.0),
                "recency": len(recent) / max(1, len(events)) if events else 0.0,
                "success_rate": success_rate,
                "dispute_ratio": disputes_won / max(1, disputes_won + disputes_lost),
            }
            return ReputationSnapshot(
                agent_id=agent_id,
                score=score,
                percentile=self.get_percentile(agent_id),
                tier=self.get_tier(score),
                components=components,
            )

    def adjust_for_volume(self, agent_id: str, job_count: int) -> float:
        with self._lock:
            current = self._scores.get(agent_id, self.BASE_SCORE)
            volume_bonus = math.log10(max(1, job_count)) * 5
            return min(self.MAX_SCORE, current + volume_bonus)

    def stake_multiplier(self, stake: float) -> float:
        if stake <= 0:
            return 1.0
        return 1.0 + min(0.5, math.log10(stake / 100.0) * 0.1)


reputation_engine = ReputationEngine()
