"""OWNEX Result-Based Opportunity Model — classification & first-day guidance.

Implements the OWNEX RESULT-BASED OPPORTUNITY MODEL: classify every opportunity
into a result-based level and steer the user toward systems where value is
proven by the delivered result, not by a hiring funnel.

Key principle (from the model): "no interview" != "no competition". Competition
just moves from the CV to the delivered result. OWNEX optimizes *where* to
compete: highest expected reward x success probability / time, and a
first-day path that leads a beginner to real rewards without experience.

Levels:
  S  direct-result     (bug bounty, dev bounty)  — no interview, pay by result
  A  low-friction      (AI eval, data)           — simple reg, pay by work
  B  skill-proof       (OSS bounty)              — no interview, sample judged
  C  traditional       (hiring funnel)           — deprioritized for result work
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.result_based")

# Result-based employment types that prove value by delivered work.
_RESULT_EMPLOYMENT = frozenset({"bounty", "open_call", "microtask", "challenge", "prize"})

# Non-result (hiring-funnel) employment types.
_TRADITIONAL_EMPLOYMENT = frozenset({"full_time", "part_time", "contract", "retainer"})

# Hiring-funnel friction: gates on WHO you are. Capability assessments
# (technical tests) are deliberately NOT here — they gate on WHAT you can
# do, amortize once, and never demote an opportunity on their own
# ("Zero Experience does not mean Zero Barrier", 2026-08-25).
_FUNNEL_FLAGS = ("interview_required", "portfolio_required")

_LEVEL_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}


@dataclass(slots=True)
class LevelAssessment:
    level: str  # S | A | B | C
    label: str
    score: float  # 0-100 result-based score
    reasons: list[str]
    expectations: list[str]
    recommendation: str  # "compete" | "consider" | "skip"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResultBasedClassifier:
    """Classifies an opportunity into result-based levels S/A/B/C."""

    def classify(self, opportunity: dict[str, Any]) -> LevelAssessment:
        employment = str(opportunity.get("employment_type") or opportunity.get("employmentType") or "")
        payment = float(opportunity.get("payment") or opportunity.get("max_payout") or 0.0)
        remote = bool(opportunity.get("remote", True))
        has_interview = bool(opportunity.get("interview_required", False))
        has_portfolio = bool(opportunity.get("portfolio_required", False))
        has_test = bool(opportunity.get("technical_test_required", False))
        intl = bool(opportunity.get("international_payment", True))

        friction_flags: list[str] = []
        if has_interview:
            friction_flags.append("requiere entrevista")
        if has_portfolio:
            friction_flags.append("requiere portfolio")
        if has_test:
            # Capability assessment: one-time, amortizable — surfaced as an
            # expectation, never as funnel friction.
            friction_flags.append("assessment de capacidad único")

        is_funnel = has_interview or has_portfolio
        assessment_only = has_test and not is_funnel

        # Level S — direct result: open bounty (public task, defined payout).
        # A capability assessment does NOT disqualify S: proving you can do
        # the work is the same act as delivering it.
        if employment in {"bounty", "open_call"} and not has_interview and not has_portfolio and remote and intl:
            score = min(100.0, 60.0 + (payment / 2000.0 * 40.0))
            reasons = [f"Pago por resultado ({employment}), sin entrevista/portfolio"]
            expectations = ["Entrega el resultado y la verificación es el pago."]
            if has_test:
                reasons.append("Assessment de capacidad único para entrar (no experiencia previa)")
                expectations.append("Inversión única de tiempo en el assessment antes de cobrar.")
            return LevelAssessment(
                level="S",
                label="Direct Result",
                score=round(score, 1),
                reasons=reasons,
                expectations=expectations,
                recommendation="compete",
            )

        # Level A — low friction: public/simple registration pay-by-work,
        # INCLUDING capability-assessed hourly streams (AI training family):
        # entry via assessment with no experience requirement is low
        # friction by design, not a hiring funnel.
        assessed_stream = (
            assessment_only
            and employment in _TRADITIONAL_EMPLOYMENT
            and str(opportunity.get("entry_mechanism") or "") in {"assessment", "training", "test"}
        )
        if (employment in {"microtask", "challenge", "prize"} and not is_funnel) or assessed_stream:
            base = 55.0 if not assessed_stream else 50.0
            score = min(90.0, base + (payment / 2000.0 * 35.0))
            reasons = [f"Trabajo por unidad/aceptación ({employment}), simple registro"] + friction_flags
            expectations = ["Calidad aceptada = pago; reputación puede crecer con cada entrega."]
            if assessed_stream:
                reasons = [
                    f"Stream por hora con entry por assessment ({employment}); sin experiencia previa requerida"
                ] + friction_flags
                expectations = ["Assessment único al entrar; después ingreso recurrente mientras haya tareas."]
            return LevelAssessment(
                level="A",
                label="Low Friction",
                score=round(score, 1),
                reasons=reasons,
                expectations=expectations,
                recommendation="compete" if score >= 60 else "consider",
            )

        # Level B — skill proof: no interview, but sample/reputation judged.
        if not is_funnel:
            score = min(80.0, 40.0 + (payment / 2000.0 * 35.0))
            return LevelAssessment(
                level="B",
                label="Skill-Proof",
                score=round(score, 1),
                reasons=["Sin entrevista tradicional; tu trabajo entregado es la prueba."] + friction_flags,
                expectations=["La muestra de trabajo y reputación afectan la aceptación."],
                recommendation="consider",
            )

        # Level C — traditional hiring funnel (identity/history gates only).
        funnel_only = [f for f in friction_flags if "assessment" not in f]
        score = max(10.0, 30.0 - len(funnel_only) * 8.0)
        return LevelAssessment(
            level="C",
            label="Traditional",
            score=round(score, 1),
            reasons=["Proceso de contratación tradicional (entrevista/portfolio/etapas)."] + friction_flags,
            expectations=["Requiere CV, entrevistas y validación previa."],
            recommendation="skip" if score < 25 else "consider",
        )


# ── First-day guidance for a beginner with no experience ──────────────────────


class FirstDayGuide:
    """Steps that take a zero-experience user to first real rewards."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._store_path = Path(store_path or Path(__file__).resolve().parents[3] / "data" / "first_day.json")
        self._data: dict[str, Any] = self._load()

    def guidance(self) -> dict[str, Any]:
        """The ordered first-day path: what to set up, win quick, then scale."""
        steps = [
            {
                "step": 1,
                "title": "Configurá canales públicos",
                "why": "Sin keys ni setup, OWNEX ya descubre opire/issuehunt/algora + bug bounties públicos.",
                "action": "Corré el daily cycle; el work bank se llena solo.",
                "effort_hours": 0.5,
            },
            {
                "step": 2,
                "title": "Primera victoria rápida (dev bounty micro)",
                "why": "Issues públicos de bajo esfuerzo con recompensa real ($50-$150) son el mejor primer cobro: cero entrevista, pago por PR aceptado.",
                "action": "Tomá el top pick del daily-brief con score alto y entregalo vía work bank.",
                "effort_hours": 2.0,
            },
            {
                "step": 3,
                "title": "Bug bounty low-hanging (Level S)",
                "why": "Programas abiertos con recompensa publicada (H1/Bugcrowd/Intigriti) pagan por hallazgo verificado, sin experiencia previa requerida.",
                "action": "Elegí del radar los programas con scope simple y baja competencia; prepará el reporte.",
                "effort_hours": 4.0,
            },
            {
                "step": 4,
                "title": "Subí a freelancer/outlier con setup manual",
                "why": "Estos pagan por trabajo entregado, pero necesitan cuenta/configuración una vez.",
                "action": "Completá el setup en /direct-work/access/explain y el descubrimiento los incorpora.",
                "effort_hours": 0.5,
            },
            {
                "step": 5,
                "title": "Fiverr: vendé soluciones, no horas",
                "why": "Un gig correctamente posicionado genera pedidos repetidos y clientes recurrentes.",
                "action": "Elegí del catálogo Fiverr el gig con pricing de demanda alta y prepará el paquete de entrega.",
                "effort_hours": 2.0,
            },
        ]
        total_hours = round(sum(s["effort_hours"] for s in steps), 1)
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_effort_hours": total_hours,
            "philosophy": "Sin entrevista no significa sin competencia: la competencia pasa del CV al resultado entregado.",
            "principle": "Maximizá: recompensa esperada x probabilidad de éxito / tiempo invertido.",
            "steps": steps,
        }

    def save_step_complete(self, step: int) -> None:
        self._data.setdefault("completed_steps", []).append(step)
        self._data["completed_steps"] = sorted(set(self._data["completed_steps"]))
        self._save()

    def progress(self) -> dict[str, Any]:
        completed = self._data.get("completed_steps", [])
        total = len(self.guidance()["steps"])
        return {
            "completed_steps": completed,
            "total_steps": total,
            "pct": round(len(completed) / total * 100, 1) if total else 0.0,
        }

    def _load(self) -> dict[str, Any]:
        try:
            if self._store_path.exists():
                return json.loads(self._store_path.read_text())
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not load first-day guide: %s", exc)
        return {}

    def _save(self) -> None:
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            self._store_path.write_text(json.dumps(self._data, indent=2))
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not save first-day guide: %s", exc)


def classify_opportunity(opportunity: dict[str, Any]) -> LevelAssessment:
    return ResultBasedClassifier().classify(opportunity)
