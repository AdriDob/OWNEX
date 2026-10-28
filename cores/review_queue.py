import contextlib
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

LOG = logging.getLogger("ownex.review_queue")


class ConfidenceTier(Enum):
    HIGH = "HIGH_CONFIDENCE"
    MEDIUM = "MEDIUM_CONFIDENCE"
    LOW = "LOW_CONFIDENCE"

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceTier":
        if score >= 0.7:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        return cls.LOW


@dataclass
class ReviewItem:
    item_id: str
    item_type: str
    label: str
    tier: str
    confidence_score: float
    reason: str
    factors: list[dict[str, Any]] = field(default_factory=list)
    target_id: int | None = None
    target_name: str | None = None
    created_at: str | None = None
    # Cola unificada (vNext): carril + EV para ordenar entre lanes.
    # lane: security | work | ai_work. ev_usd None = sin monto observable.
    lane: str = "security"
    ev_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewQueue:
    high_confidence: list[ReviewItem] = field(default_factory=list)
    medium_confidence: list[ReviewItem] = field(default_factory=list)
    low_confidence: list[ReviewItem] = field(default_factory=list)
    total_items: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def add(self, item: ReviewItem) -> None:
        if item.tier == "HIGH_CONFIDENCE":
            self.high_confidence.append(item)
        elif item.tier == "MEDIUM_CONFIDENCE":
            self.medium_confidence.append(item)
        else:
            self.low_confidence.append(item)
        self.total_items += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "high_confidence": [i.to_dict() for i in self.high_confidence],
            "medium_confidence": [i.to_dict() for i in self.medium_confidence],
            "low_confidence": [i.to_dict() for i in self.low_confidence],
            "total_items": self.total_items,
            "counts": {
                "high": len(self.high_confidence),
                "medium": len(self.medium_confidence),
                "low": len(self.low_confidence),
            },
            "generated_at": self.generated_at,
        }


def _classify_tier(score: float) -> str:
    return ConfidenceTier.from_score(score).value


def _build_reason(tier: str, score: float, factors: list[dict[str, Any]]) -> str:
    if tier == "HIGH_CONFIDENCE":
        return f"Strong confidence ({score:.2f}) — reliable signal, ready for human review"
    elif tier == "MEDIUM_CONFIDENCE":
        return f"Moderate confidence ({score:.2f}) — requires human assessment"
    return f"Low confidence ({score:.2f}) — needs additional validation before review"


def _work_review_items(limit: int = 20, store_path: str | Path | None = None) -> list[ReviewItem]:
    """Items WorkBank listos o bloqueados (carril work). Best-effort: [] si falla."""
    try:
        from cores.direct_work_engine.workbank import WorkBank

        # Construcción directa (NO el singleton global: el path inyectable
        # debe respetarse siempre, sobre todo en tests).
        wb = WorkBank(store_path=store_path) if store_path else WorkBank()
        items = [i for i in wb._items.values() if getattr(i, "status", "") in ("ready_to_deliver", "needs_access")][
            : max(0, limit)
        ]
        out: list[ReviewItem] = []
        for i in items:
            ready = getattr(i, "status", "") == "ready_to_deliver"
            reward = float(getattr(i, "reward", 0.0) or 0.0)
            out.append(
                ReviewItem(
                    item_id=f"work_{getattr(i, 'id', '?')}",
                    item_type="work",
                    label=str(getattr(i, "title", "Untitled"))[:120],
                    tier="HIGH_CONFIDENCE" if ready else "MEDIUM_CONFIDENCE",
                    confidence_score=0.75 if ready else 0.5,
                    reason=(
                        "Listo para entregar: solo falta tu aprobación"
                        if ready
                        else f"Bloqueado por paso humano: {getattr(i, 'access_requirement', '') or 'ver requisito'}"
                    ),
                    factors=[
                        {"name": "work_status", "value": getattr(i, "status", ""), "description": "Estado en WorkBank"},
                        {"name": "platform", "value": getattr(i, "platform", ""), "description": "Plataforma destino"},
                        {"name": "reward", "value": reward, "description": "Recompensa observable (no promesa)"},
                    ],
                    lane="work",
                    ev_usd=reward if reward > 0 else None,
                )
            )
        return out
    except Exception as exc:
        LOG.warning("review_queue: workbank no disponible: %s", exc)
        return []


def _assessment_review_items(limit: int = 20, store_path: str | Path | None = None) -> list[ReviewItem]:
    """Assessments pendientes AI-training (carril ai_work). Best-effort: [] si falla."""
    try:
        from cores.application_assistant import STATUS_ACCEPTED, STATUS_PAUSED, STATUS_REJECTED, ApplicationAssistant

        assistant = ApplicationAssistant(Path(store_path) if store_path else None)
        plan = assistant.get_plan()
        out: list[ReviewItem] = []
        for platform in (plan.get("platforms") or [])[: max(0, limit)]:
            status = platform.get("status", "pending")
            if status in (STATUS_ACCEPTED, STATUS_REJECTED, STATUS_PAUSED):
                continue
            pending = [s for s in (platform.get("steps") or []) if not s.get("done")]
            if not pending:
                continue
            step = pending[0]
            out.append(
                ReviewItem(
                    item_id=f"assess_{platform.get('key', '?')}",
                    item_type="assessment",
                    label=f"Assessment: {platform.get('name', '?')} — {step.get('title', '?')}",
                    tier="MEDIUM_CONFIDENCE",
                    confidence_score=0.5,
                    reason=f"Siguiente paso humano: {step.get('detail', '') or step.get('title', '')}",
                    factors=[
                        {"name": "platform", "value": platform.get("key", ""), "description": "Plataforma AI-training"},
                        {
                            "name": "est_minutes",
                            "value": step.get("est_minutes", 0),
                            "description": "Minutos estimados",
                        },
                    ],
                    lane="ai_work",
                    ev_usd=None,
                )
            )
        return out
    except Exception as exc:
        LOG.warning("review_queue: assessments no disponibles: %s", exc)
        return []


def unified_ranked(queue: ReviewQueue, limit: int = 20) -> list[dict[str, Any]]:
    """Una sola lista ordenada por (EV desc, confianza desc) entre carriles.

    Puro: no toca DB ni stores. EV None cuenta como 0 (sin monto observable
    no lidera el ranking, pero sigue visible).
    """
    items = list(queue.high_confidence) + list(queue.medium_confidence) + list(queue.low_confidence)
    items.sort(key=lambda i: (-(i.ev_usd or 0.0), -i.confidence_score))
    return [i.to_dict() for i in items[: max(0, limit)]]


def build_review_queue(limit: int = 100) -> ReviewQueue:
    from database.db import SessionLocal

    session = SessionLocal()
    try:
        from database.models import Finding, Target, Verdict

        queue = ReviewQueue()

        # Verdict review items
        verdicts = session.query(Verdict).order_by(Verdict.created_at.desc()).limit(limit).all()
        for v in verdicts:
            raw_conf = 0.0
            if v.confidence:
                with contextlib.suppress(ValueError, TypeError):
                    raw_conf = float(v.confidence)

            status = v.status or "inconclusive"
            status_bonus = {"confirmed": 0.2, "inconclusive": 0.0, "rejected": -0.1}
            adjusted = raw_conf + status_bonus.get(status, 0.0)
            adjusted = max(0.0, min(1.0, adjusted))

            factors = [
                {
                    "name": "stored_confidence",
                    "value": round(raw_conf, 4),
                    "description": "Raw confidence from validation",
                },
                {"name": "status", "value": status, "description": f"Verdict status: {status}"},
                {"name": "retry_count", "value": v.retry_count, "description": f"Retry attempts: {v.retry_count}"},
            ]

            tier = _classify_tier(adjusted)
            reason = _build_reason(tier, adjusted, factors)

            target_name = ""
            if v.endpoint_id:
                ep = session.query(type("EP", (), {"target_id": 0})()).from_statement(type("stmt", (), {})())
                from database.models import Endpoint

                ep = session.query(Endpoint).filter(Endpoint.id == v.endpoint_id).first()
                if ep:
                    t = session.query(Target).filter(Target.id == ep.target_id).first()
                    if t:
                        target_name = t.name

            queue.add(
                ReviewItem(
                    item_id=f"verdict_{v.id}",
                    item_type="verdict",
                    label=f"Verdict #{v.id} — {status}",
                    tier=tier,
                    confidence_score=round(adjusted, 4),
                    reason=reason,
                    factors=factors,
                    target_id=v.endpoint_id,
                    target_name=target_name,
                    created_at=v.created_at.isoformat() if v.created_at else None,
                )
            )

        # High-severity finding review items
        findings = (
            session.query(Finding)
            .filter(Finding.severity.in_(["critical", "high"]))
            .order_by(Finding.created_at.desc())
            .limit(limit)
            .all()
        )
        for f in findings:
            severity_bonus = {"critical": 0.8, "high": 0.6, "medium": 0.4, "low": 0.2}
            score = severity_bonus.get(f.severity, 0.3)

            factors = [
                {"name": "severity", "value": f.severity, "description": f"Severity: {f.severity}"},
                {"name": "has_endpoint", "value": f.endpoint_id is not None, "description": "Linked to endpoint"},
            ]

            if f.endpoint_id:
                from database.models import Verdict as VerdictModel

                related = session.query(VerdictModel).filter(VerdictModel.endpoint_id == f.endpoint_id).count()
                if related > 0:
                    score = min(score + 0.15, 1.0)
                    factors.append(
                        {"name": "verified", "value": related, "description": f"{related} related verdict(s)"}
                    )

            tier = _classify_tier(score)
            reason = _build_reason(tier, score, factors)

            target_name = ""
            t = session.query(Target).filter(Target.id == f.target_id).first()
            if t:
                target_name = t.name

            # Submit-gate en vivo: el humano ve POR QUÉ está aparcado (o listo).
            # Best-effort por item: si el gate falla, el item sigue en cola sin el factor.
            with contextlib.suppress(Exception):
                from cores.auto_submit.submit_gate import submit_gate_for_finding

                gate = submit_gate_for_finding(int(f.id))
                factors.append(
                    {
                        "name": "submit_gate",
                        "value": "ready" if gate.allow_submit else f"parked:{gate.parked_reason}",
                        "description": "Veredicto live del submit gate (scope + repro + dedupe)",
                    }
                )

            queue.add(
                ReviewItem(
                    item_id=f"finding_{f.id}",
                    item_type="finding",
                    label=f.finding_title
                    if hasattr(f, "finding_title") and f.finding_title
                    else (f.title or "Untitled"),
                    tier=tier,
                    confidence_score=round(score, 4),
                    reason=reason,
                    factors=factors,
                    target_id=f.target_id,
                    target_name=target_name,
                    created_at=f.created_at.isoformat() if f.created_at else None,
                )
            )

        # Cola unificada (vNext P0): work + assessments junto a findings.
        # Cada sección es best-effort; si falla, la cola sigue con el resto.
        for item in _work_review_items(limit=20) + _assessment_review_items(limit=20):
            queue.add(item)

        return queue

    finally:
        session.close()
