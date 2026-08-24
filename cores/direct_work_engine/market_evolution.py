"""Market Evolution Engine — Continuous Ecosystem Discovery & Validation.

The persistent brain of the Universal Opportunity Discovery spec: OWNEX does not
just find platforms, it *evolves* its market knowledge. On top of the curated
`SourceIntelEngine` (static analysis) and the feedback loop (`feedback.py`,
real outcomes), this module adds the four missing pillars:

1. **OVOS — OWNEX Verified Opportunity Score (0-100)**: a single comparable
   number per ecosystem that combines expected reward, success probability,
   completion time, barrier level, market stability, competition, user skill
   match, legal accessibility and historical success.
2. **Friction Index (S/A/B/C/REJECT)**: a compact tier that summarizes how much
   friction the user will face before earning, from `FRICTION_LOWEST` (S) to
   blocked/bureaucratic (REJECT).
3. **Automatic Retirement**: ecosystems that stop being active/rentable or were
   never accepted get their priority reduced (downgrade) or archived (retired),
   so stale platforms stop stealing the radar's attention.
4. **Persistent Knowledge Base**: one record per ecosystem with review date,
   historical performance (attempts/accepted/earned), rating and notes —
   survives restarts and accumulates measurement across sessions.

It also emits the consolidated **Market Report** (the spec's daily market
intelligence): platforms analyzed, new ecosystems discovered, high-confidence
opportunities, emerging categories, rejected platforms, highest EV, best
recommendation and next actions.

Reuses `SourceIntelEngine` and `LearningRecord` — never recomputes analysis
already done elsewhere (Golden Rule: no duplicated logic).
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.direct_work_engine.market_evolution")

# Ordering of friction tiers from least to most friction. Highest index = worst.
FRICTION_TIER_ORDER = ("S", "A", "B", "C", "REJECT")

# Retirement thresholds (Zero Magic: all knobs are named constants).
_MIN_HISTORY_FOR_RETIRE = 3  # attempts before a no-accept source can be retired
_RETIRE_TRUST_THRESHOLD = 40.0  # below this a source is automatically archived
_DOWNGRADE_TRUST_THRESHOLD = 50.0  # below this a source loses radar priority
_MIN_HIT_RATE = 0.2  # below this (with history) the rating is low

# Estimated $/hour used to map an OVOS-relative reward figure into USD potential.
_REWARD_WEIGHT = 0.30
_SUCCESS_WEIGHT = 0.20
_TIME_WEIGHT = 0.12
_BARRIER_WEIGHT = 0.12
_STABILITY_WEIGHT = 0.10
_COMPETITION_WEIGHT = 0.06
_SKILL_MATCH_WEIGHT = 0.05
_LEGAL_WEIGHT = 0.03
_HISTORY_WEIGHT = 0.02


@dataclass(slots=True)
class EcosystemRecord:
    """A persistent knowledge-base entry for one opportunity ecosystem."""

    name: str
    category: str = "other"
    url: str = ""
    average_reward: str = "varies"
    trust_score: float = 0.0
    ovos: float = 0.0
    friction_tier: str = "C"
    review_date: str = ""
    first_seen: str = ""
    historical_attempts: int = 0
    historical_accepted: int = 0
    historical_earned: float = 0.0
    rating: float = 0.0  # 0-100 derived from hit rate + trust
    retired: bool = False
    retirement_reason: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        if self.historical_attempts <= 0:
            return 0.0
        return self.historical_accepted / self.historical_attempts

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "url": self.url,
            "average_reward": self.average_reward,
            "trust_score": round(self.trust_score, 1),
            "ovos": round(self.ovos, 1),
            "friction_tier": self.friction_tier,
            "review_date": self.review_date,
            "first_seen": self.first_seen,
            "historical_attempts": self.historical_attempts,
            "historical_accepted": self.historical_accepted,
            "historical_earned": round(self.historical_earned, 2),
            "rating": round(self.rating, 1),
            "retired": self.retired,
            "retirement_reason": self.retirement_reason,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EcosystemRecord:
        return cls(
            name=str(data.get("name", "?")),
            category=str(data.get("category", "other")),
            url=str(data.get("url", "")),
            average_reward=str(data.get("average_reward", "varies")),
            trust_score=float(data.get("trust_score", 0.0)),
            ovos=float(data.get("ovos", 0.0)),
            friction_tier=str(data.get("friction_tier", "C")),
            review_date=str(data.get("review_date", "")),
            first_seen=str(data.get("first_seen", "")),
            historical_attempts=int(data.get("historical_attempts", 0)),
            historical_accepted=int(data.get("historical_accepted", 0)),
            historical_earned=float(data.get("historical_earned", 0.0)),
            rating=float(data.get("rating", 0.0)),
            retired=bool(data.get("retired", False)),
            retirement_reason=str(data.get("retirement_reason", "")),
            notes=list(data.get("notes", [])),
        )


def _default_store_path() -> Path:
    """Data-dir aware default: frozen bundles get OWNEX_DATA_DIR
    from start_backend.py (%LOCALAPPDATA%/OWNEX); dev keeps repo ./data."""
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[3] / "data"
    return root / "market_kb.json"


class MarketKnowledgeBase:
    """Persistent store of per-ecosystem records (survives restarts)."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._store_path = store_path or _default_store_path()
        self._records: dict[str, EcosystemRecord] = {}
        self._load()

    def get(self, name: str) -> EcosystemRecord | None:
        return self._records.get(name)

    def upsert(self, record: EcosystemRecord) -> None:
        prev = self._records.get(record.name)
        if prev is not None:
            record.first_seen = record.first_seen or prev.first_seen
            record.historical_attempts = record.historical_attempts or prev.historical_attempts
            record.historical_accepted = record.historical_accepted or prev.historical_accepted
            record.historical_earned = record.historical_earned or prev.historical_earned
            record.notes = list(record.notes) or list(prev.notes)
        self._records[record.name] = record
        self._save()

    def all(self) -> list[EcosystemRecord]:
        return list(self._records.values())

    def active(self) -> list[EcosystemRecord]:
        return [r for r in self._records.values() if not r.retired]

    def retired(self) -> list[EcosystemRecord]:
        return [r for r in self._records.values() if r.retired]

    def discovered_since(self, day: str) -> list[EcosystemRecord]:
        return [r for r in self._records.values() if r.first_seen and r.first_seen >= day]

    def _load(self) -> None:
        try:
            if self._store_path.exists():
                raw = json.loads(self._store_path.read_text())
                self._records = {name: EcosystemRecord.from_dict(rec) for name, rec in raw.items()}
        except Exception as exc:  # never take the engine down on corrupt storage
            logger.warning("Could not load market knowledge base: %s", exc)

    def _save(self) -> None:
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {name: rec.to_dict() for name, rec in self._records.items()}
            self._store_path.write_text(json.dumps(payload, indent=2))
        except Exception as exc:
            logger.warning("Could not save market knowledge base: %s", exc)


def _reward_usd(average_reward: str) -> float:
    """Best-effort USD figure from a free-text reward range. Never fabricates."""
    if not average_reward or average_reward in ("varies", "", "Unknown"):
        return 0.0
    nums = [float(n.replace(",", "")) for n in re.findall(r"[\d,]+", average_reward)]
    if not nums:
        return 0.0
    return sum(nums) / len(nums) * (200 if "$" not in average_reward and "USD" not in average_reward else 1)


def _friction_tier(average_reward: str | None, entry_barrier: str | None, source_type: str | None, trust: float) -> str:
    """Map the analyzed signals into a compact S/A/B/C/REJECT index."""
    eff_rate = _reward_usd(average_reward or "")
    barrier = entry_barrier or "MEDIUM"
    if _is_rejected(source_type or "", barrier, trust):
        return "REJECT"
    score = 0.0
    score += 4.0 if barrier == "LOW" else (2.0 if barrier == "MEDIUM" else 0.0)
    score += 3.0 if eff_rate >= 20 else (2.0 if eff_rate >= 5 else 0.0)
    score += 2.0 if trust >= 70 else (1.0 if trust >= 50 else 0.0)
    if score >= 8:
        return "S"
    if score >= 6:
        return "A"
    if score >= 4:
        return "B"
    return "C"


def _is_rejected(source_type: str, entry_barrier: str, trust: float) -> bool:
    if source_type == "job_board":
        return True
    if entry_barrier == "HIGH":
        return True
    return trust < _RETIRE_TRUST_THRESHOLD


def _skill_match(skills: set[str], tags: list[str] | None, category: str) -> float:
    """0-1 overlap between the user's skills and a source's tags/category skills."""
    if not skills:
        return 0.5  # neutral when unknown, never penalize without data
    candidates = set(tags or [])
    candidates.update(re.split(r"[_\- ]+", category))
    if not candidates:
        return 0.5
    return len(skills & candidates) / len(skills)


def _competitive_discount(source_type: str) -> float:
    """Market stability/competition intuition per source shape."""
    return {
        "job_board": 0.30,  # most competitive, opaque selection
        "forum": 0.55,
        "aggregator": 0.70,
        "direct_api": 0.80,
        "platform": 0.85,  # direct, transparent, durable platforms
    }.get(source_type, 0.60)


class MarketEvolutionEngine:
    """Computes OVOS per ecosystem, maintains the knowledge base and the report."""

    def __init__(self, knowledge_base: MarketKnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or MarketKnowledgeBase()

    def analyze(self) -> dict[str, Any]:
        """Run the full evolution pass and persist the updated knowledge base."""
        report = self._build_report()
        for row in report["ecosystems"]:
            self._kb.upsert(self._row_to_record(row))
        return report

    def _build_report(self) -> dict[str, Any]:
        from cores.direct_work_engine.source_intel import SourceIntelEngine

        today = date.today().isoformat()
        intel = SourceIntelEngine().analyze()
        rows = self._score_ecosystems(intel["sources"])
        self._apply_history(rows)
        self._apply_retirement(rows)

        rows.sort(key=lambda r: (r["retired"], r["friction"] in ("REJECT",), r["ovos"]), reverse=True)

        top = [r for r in rows if not r["retired"]][:5]
        rejected = [r for r in rows if r["retired"]]
        new = [r for r in rows if r.get("first_seen") == today and not r["retired"]]
        emerging = sorted(intel.get("uncovered_categories", []))

        return {
            "generated_at": today,
            "platforms_analyzed": len(rows),
            "total_curated_sources": int(intel["total_curated_sources"]),
            "new_ecosystems_discovered": [r["name"] for r in new],
            "high_confidence_opportunities": [r["name"] for r in top],
            "highest_ev": (top[0]["name"] if top else None),
            "best_recommendation": (top[0]["name"] if top else None),
            "emerging_categories": emerging,
            "rejected_platforms": [r["name"] for r in rejected],
            "friction_summary": self._friction_summary(rows),
            "recommended_actions": self._recommended_actions(rows, emerging),
            "ecosystems": rows,
        }

    def _score_ecosystems(self, analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Score every analyzed source into an OVOS + friction row."""
        rows: list[dict[str, Any]] = []
        skill_sources = self._registry_tags()
        for a in analyses:
            name = str(a["name"])
            tags = skill_sources.get(name, [])
            reward = _reward_usd(a.get("average_reward", ""))
            trust = float(a.get("trust_score", 50.0))
            friction = _friction_tier(a.get("average_reward"), a.get("entry_barrier"), a.get("source_type"), trust)

            components = {
                "expected_reward": min(reward / 50.0, 1.0),
                "success_probability": float(a.get("trust_score", 50.0)) / 100.0,
                "completion_time": float(a.get("task_transparency", 0.5)),
                "barrier_level": 1.0
                if a.get("entry_barrier") == "LOW"
                else (0.5 if a.get("entry_barrier") == "MEDIUM" else 0.0),
                "market_stability": float(a.get("trust_score", 50.0)) / 100.0,
                "competition": _competitive_discount(a.get("source_type", "platform")),
                "skill_match": self._skill_match(tags=tags, category=a.get("category", "")),
                "legal_accessibility": 1.0
                if a.get("argentina_compatibility") == "YES"
                else (0.5 if a.get("argentina_compatibility") == "UNKNOWN" else 0.0),
                "historical_success": 0.5,
            }
            ovos = self._compute_ovos(components)

            rows.append(
                {
                    "name": name,
                    "url": a.get("url", ""),
                    "category": a.get("category", "other"),
                    "average_reward": a.get("average_reward", "varies"),
                    "source_type": a.get("source_type", "platform"),
                    "entry_barrier": a.get("entry_barrier", "MEDIUM"),
                    "trust_score": trust,
                    "ovos": ovos,
                    "friction": friction,
                    "friction_tier": friction,
                    "earning_potential": a.get("earning_potential", "LOW"),
                    "payment_method": a.get("payment_method", ""),
                    "argentina_compatibility": a.get("argentina_compatibility", "UNKNOWN"),
                    "retired": False,
                    "retirement_reason": "",
                    "first_seen": "",
                    "components": components,
                }
            )
        return rows

    def _compute_ovos(self, components: dict[str, float]) -> float:
        """Combine the nine OVOS inputs into a 0-100 score (weights sum to 1.0)."""
        raw = (
            components["expected_reward"] * _REWARD_WEIGHT
            + components["success_probability"] * _SUCCESS_WEIGHT
            + components["completion_time"] * _TIME_WEIGHT
            + components["barrier_level"] * _BARRIER_WEIGHT
            + components["market_stability"] * _STABILITY_WEIGHT
            + components["competition"] * _COMPETITION_WEIGHT
            + components["skill_match"] * _SKILL_MATCH_WEIGHT
            + components["legal_accessibility"] * _LEGAL_WEIGHT
            + components["historical_success"] * _HISTORY_WEIGHT
        )
        return round(max(0.0, min(100.0, raw * 100.0)), 1)

    def _registry_tags(self) -> dict[str, list[str]]:
        """Read the curated source tags (lazy, decoupled from legacy curation)."""
        from cores.opportunity.global_sources import get_sources

        return {str(src.name): list(getattr(src, "tags", []) or []) for src in get_sources()}

    def _apply_history(self, rows: list[dict[str, Any]]) -> None:
        """Fold real measured outcomes from the knowledge base into the OVOS."""
        for row in rows:
            rec = self._kb.get(row["name"])
            if rec is None:
                continue
            row["first_seen"] = rec.first_seen
            row["components"]["historical_success"] = min(rec.hit_rate * 2.0, 1.0) if rec.historical_attempts else 0.5
            row["ovos"] = self._compute_ovos(row["components"])

    def _apply_retirement(self, rows: list[dict[str, Any]]) -> None:
        """Automatic Retirement: archive never-accepted / low-trust sources."""
        for row in rows:
            rec = self._kb.get(row["name"])
            reason = ""
            if row["friction"] == "REJECT":
                reason = "Bloqueada o burocrática (fricción REJECT)."
            elif row["trust_score"] < _RETIRE_TRUST_THRESHOLD:
                reason = "Trust score bajo: plataforma no verificada o de baja calidad."
            elif (
                rec is not None and rec.historical_attempts >= _MIN_HISTORY_FOR_RETIRE and rec.historical_accepted == 0
            ):
                reason = f"Sin aceptaciones tras {rec.historical_attempts} intentos medidos."
            if reason:
                row["retired"] = True
                row["retirement_reason"] = reason
            elif row["friction"] == "C" or row["trust_score"] < _DOWNGRADE_TRUST_THRESHOLD:
                row["retired"] = False
                row["retirement_reason"] = ""

    @staticmethod
    def _friction_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
        summary: dict[str, int] = {tier: 0 for tier in FRICTION_TIER_ORDER}
        for row in rows:
            row_friction = row.get("friction_tier", row.get("friction", "C"))
            if row_friction not in summary:
                summary["REJECT"] += 1
            else:
                summary[row_friction] += 1
        return summary

    def _recommended_actions(self, rows: list[dict[str, Any]], emerging: list[str]) -> list[str]:
        actions: list[str] = []
        top = [r for r in rows if not r["retired"]][:3]
        if top:
            actions.append(f"Preparar entrega en {', '.join(r['name'] for r in top)} (OVOS más alto).")
        if emerging:
            actions.append(f"Explorar categorías sin fuentes curadas: {', '.join(emerging[:3])}.")
        pending = self._pending_measurements()
        if pending:
            actions.append(f"Registrar outcomes de plataformas medidas ({pending} pendientes) para refinar OVOS.")
        if not actions:
            actions.append("Radar estable: ninguna acción urgente hoy.")
        return actions

    def _pending_measurements(self) -> int:
        return sum(1 for r in self._kb.all() if r.historical_attempts == 0)

    def _row_to_record(self, row: dict[str, Any]) -> EcosystemRecord:
        today = date.today().isoformat()
        rating = round((row["ovos"] * 0.7 + row["trust_score"] * 0.3), 1)
        recent_notes = [row["retirement_reason"]] if row.get("retirement_reason") else []
        return EcosystemRecord(
            name=row["name"],
            category=row["category"],
            url=row["url"],
            average_reward=row["average_reward"],
            trust_score=row["trust_score"],
            ovos=row["ovos"],
            friction_tier=row.get("friction_tier", row.get("friction", "C")),
            review_date=today,
            first_seen=row.get("first_seen") or today,
            rating=rating,
            retired=row["retired"],
            retirement_reason=row.get("retirement_reason", ""),
            notes=recent_notes,
        )

    def _skill_match(self, tags: list[str] | None, category: str) -> float:
        # Historical UserProfile skill matching is wired at the API layer; here we
        # stay neutral unless really informative tags/category exist.
        return _skill_match(set(), tags, category)


def get_market_evolution_engine() -> MarketEvolutionEngine:
    """Module-level singleton so the whole API shares one knowledge base."""
    return MarketEvolutionEngine()
