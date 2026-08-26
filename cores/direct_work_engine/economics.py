"""Economic engine — single ExpectedValue contract (FASE 3, P0-3).

One implementation answers "how much money is this opportunity worth".
Both ``IntelligentRecommender`` and ``EVScorer`` (autonomous discovery)
delegate here; no ranking path may compute EV with private math.

Honesty rules (project charter §"nunca inventar"):

* Task availability is never silently assumed. When unknown, the factor
  is EXCLUDED from the multiplicative core and surfaced via
  ``availability_state="unknown"`` + an explicit warning — the caller
  decides how to rank ties (e.g. platform tier / recency), not this
  module by pretending availability is 1.0.
* Cold-start acceptance priors are a caller concern: this module takes
  the probability it is given. Engines deriving probabilities from
  curated tables must label them as cold-start priors in their output.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _clamp01(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


@dataclass(frozen=True, slots=True)
class TaskAvailability:
    """Explicit known/unknown state for p(task_available).

    The audit (2026-08-24) found zero live availability signals in any
    adapter; assuming 1.0 was the largest optimistic bias in the system's
    decision number. Callers without a real signal MUST use
    :meth:`unknown` and surface the warning downstream.
    """

    known: bool
    value: float = 0.0

    @classmethod
    def of(cls, probability: float) -> TaskAvailability:
        return cls(known=True, value=_clamp01(probability))

    @classmethod
    def unknown(cls) -> TaskAvailability:
        return cls(known=False)


UNKNOWN_AVAILABILITY = TaskAvailability.unknown()


@dataclass(frozen=True, slots=True)
class ExpectedValueResult:
    ev_usd: float
    availability_state: str  # "known" | "unknown"
    factors: dict[str, float] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


_UNKNOWN_WARNING = (
    "task_availability=UNKNOWN -> partial EV; ranking must break ties by "
    "tier/recency instead of assuming the task exists"
)


def compute_expected_value(
    *,
    payment: float,
    acceptance_probability: float,
    task_availability: TaskAvailability = UNKNOWN_AVAILABILITY,
    payment_reliability: float = 1.0,
) -> ExpectedValueResult:
    """Money expectation: the ONLY EV math allowed in ranking paths.

    Core = payment x clamp01(acceptance) x reliability, further scaled by
    availability only when it is genuinely known. Reliability defaults to
    neutral 1.0 here (engines that track payout-method reliability pass
    theirs explicitly).
    """
    warnings: tuple[str, ...] = ()
    acceptance = _clamp01(acceptance_probability)
    reliability = min(max(payment_reliability, 0.0), 1.0)

    ev = float(payment) * acceptance * reliability

    if task_availability.known:
        state = "known"
        ev *= task_availability.value
        factors = {
            "payment": float(payment),
            "acceptance": acceptance,
            "reliability": reliability,
            "task_availability": task_availability.value,
        }
    else:
        state = "unknown"
        warnings = (_UNKNOWN_WARNING,)
        factors = {
            "payment": float(payment),
            "acceptance": acceptance,
            "reliability": reliability,
        }

    return ExpectedValueResult(
        ev_usd=round(ev, 2),
        availability_state=state,
        factors=factors,
        warnings=warnings,
    )


# ── Expected Human Value (2026-08-25) ────────────────────────────────────────
# "Maximizar dinero esperado por hora de intervención humana" — the ranking
# currency for MAX_INCOME. Same honesty rules as the per-result contract:
# unknown inputs are surfaced, never silently assumed.


@dataclass(frozen=True, slots=True)
class HumanValueResult:
    """Expected dollars per human-hour + how fast cash actually arrives.

    ``ev_per_human_hour_usd`` is None when the human hours are unknown or
    zero — dividing by a guess would be inventing data. Same for
    ``cash_speed_days`` when no payment-timing signal exists.
    ``ev_usd`` exposes the underlying SSOT total so callers never re-derive
    money math from ``factors`` (convergencia P0-3, audit 2026-08-25).
    """

    ev_per_human_hour_usd: float | None
    cash_speed_days: float | None
    availability_state: str
    ev_usd: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


_HOURS_WARNING = "human_hours unknown/zero -> $/human-hour not computable; rank by EV only"
_CASH_WARNING = "time_to_first_payment unknown -> cash speed not computable"


def compute_expected_human_value(
    *,
    payment: float | None = None,
    hourly_rate: float | None = None,
    human_hours: float | None,
    acceptance_probability: float,
    task_availability: TaskAvailability = UNKNOWN_AVAILABILITY,
    payment_reliability: float = 1.0,
    time_to_first_payment_days: float | None = None,
) -> HumanValueResult:
    """Expected income per hour of HUMAN work, plus time-to-cash.

    Income base is ``hourly_rate * human_hours`` when an hourly stream is
    known, else the one-shot ``payment``. The EV core delegates to
    :func:`compute_expected_value` so there is exactly ONE money-expectation
    math in the system.
    """
    warnings: list[str] = []

    if hourly_rate is not None and hourly_rate > 0:
        if human_hours is None or human_hours <= 0:
            warnings.append(_HOURS_WARNING)
            income_base = 0.0
        else:
            income_base = float(hourly_rate) * float(human_hours)
    elif payment is not None:
        income_base = float(payment)
        if human_hours is not None and human_hours <= 0:
            warnings.append(_HOURS_WARNING)
    else:
        income_base = 0.0

    core = compute_expected_value(
        payment=income_base,
        acceptance_probability=acceptance_probability,
        task_availability=task_availability,
        payment_reliability=payment_reliability,
    )
    warnings.extend(core.warnings)

    ev_per_hour: float | None = None
    if core.ev_usd > 0 and human_hours is not None and human_hours > 0:
        ev_per_hour = round(core.ev_usd / float(human_hours), 2)
    elif core.ev_usd > 0 and _HOURS_WARNING not in warnings:
        warnings.append(_HOURS_WARNING)

    cash_days: float | None = None
    if time_to_first_payment_days is not None and time_to_first_payment_days >= 0:
        cash_days = float(time_to_first_payment_days)
    else:
        warnings.append(_CASH_WARNING)

    factors = dict(core.factors)
    if hourly_rate is not None:
        factors["hourly_rate"] = float(hourly_rate)
    factors["human_hours"] = float(human_hours) if human_hours is not None else -1.0

    return HumanValueResult(
        ev_per_human_hour_usd=ev_per_hour,
        cash_speed_days=cash_days,
        availability_state=core.availability_state,
        ev_usd=core.ev_usd,
        factors=factors,
        warnings=tuple(warnings),
    )


# ── Immediate vs Long-term earning profile ───────────────────────────────────
# Curated defaults per canonical category (source="curated"): qualitative
# anchors, NOT measured probabilities. Real OWNEX history overrides via
# RevenueTracker when it exists. Mirrors PAYMENT_RELIABILITY pattern.

_IMMEDIATE_DEFAULT = 50
_LONG_TERM_DEFAULT = 50

CATEGORY_EARNING_PROFILE: dict[str, dict[str, int]] = {
    "data_annotation": {"immediate": 80, "long_term": 40},
    "ai_evaluation": {"immediate": 60, "long_term": 80},
    "dev_bounty": {"immediate": 85, "long_term": 85},
    "bug_bounty": {"immediate": 35, "long_term": 95},
    "prompt_engineering": {"immediate": 55, "long_term": 75},
    "technical_writing": {"immediate": 70, "long_term": 70},
    "code_review": {"immediate": 65, "long_term": 85},
    "qa_automation": {"immediate": 70, "long_term": 75},
    "software_engineering": {"immediate": 60, "long_term": 80},
}


@dataclass(frozen=True, slots=True)
class EarningScores:
    """Immediate vs long-term earning potential (0-100 each)."""

    immediate: int
    long_term: int
    source: str  # curated | ownex_history

    def to_dict(self) -> dict[str, object]:
        return {"immediate": self.immediate, "long_term": self.long_term, "source": self.source}

    @staticmethod
    def for_category(category_value: str) -> EarningScores:
        """Curated default profile; never invents precision beyond the table."""
        profile = CATEGORY_EARNING_PROFILE.get(category_value)
        if profile is None:
            return EarningScores(_IMMEDIATE_DEFAULT, _LONG_TERM_DEFAULT, "curated")
        return EarningScores(profile["immediate"], profile["long_term"], "curated")


# ── HumanTimeAdjustedROI — Fase C (versioned, spec Income Multiplier §4) ──

HTROI_FORMULA_VERSION = "HTROI-V1"


@dataclass(frozen=True, slots=True)
class HumanTimeAdjustedROI:
    """Income per HUMAN hour — the metric that actually matters (§38).

    human_hours = execution + qualification + review (human-only time).
    Automation fields are optional and only populate compression when a
    measured manual baseline exists — never fabricated (§14 honesty).
    """

    roi_usd_per_hour: float | None
    expected_income_usd: float
    human_hours_total: float
    confidence_applied: float
    compression_pct: float | None
    automation_ratio: float | None
    formula_version: str
    warnings: tuple[str, ...] = ()


def compute_htroi(
    *,
    expected_income_usd: float,
    human_hours: float,
    confidence: float = 1.0,
    automation_hours: float | None = None,
    manual_baseline_hours: float | None = None,
) -> HumanTimeAdjustedROI:
    """Expected income scaled by confidence, divided by HUMAN hours only.

    Automation time is excluded from the denominator by design: it is the
    machine's cost, not yours. Compression is reported ONLY when a real
    manual baseline was measured — otherwise None (never invented).
    """
    warnings: list[str] = []
    conf = _clamp01(confidence)
    hours = float(human_hours)

    if hours <= 0:
        warnings.append("human_hours<=0 -> ROI indefinido (no hay tiempo humano declarado)")
        return HumanTimeAdjustedROI(
            roi_usd_per_hour=None,
            expected_income_usd=float(expected_income_usd),
            human_hours_total=hours,
            confidence_applied=conf,
            compression_pct=None,
            automation_ratio=None,
            formula_version=HTROI_FORMULA_VERSION,
            warnings=tuple(warnings),
        )

    compression: float | None = None
    ratio: float | None = None
    if automation_hours is not None and manual_baseline_hours:
        if manual_baseline_hours <= 0:
            warnings.append("manual_baseline_hours<=0 ignorado")
        else:
            compression = round((1 - automation_hours / manual_baseline_hours) * 100, 1)
            ratio = round(automation_hours / hours, 2) if hours else None

    roi = round(float(expected_income_usd) * conf / hours, 2)
    return HumanTimeAdjustedROI(
        roi_usd_per_hour=roi,
        expected_income_usd=float(expected_income_usd),
        human_hours_total=hours,
        confidence_applied=conf,
        compression_pct=compression,
        automation_ratio=ratio,
        formula_version=HTROI_FORMULA_VERSION,
        warnings=tuple(warnings),
    )


# ── Confidence Engine — Fase E (versioned, spec Income Multiplier §26) ──

CONFIDENCE_FORMULA_VERSION = "CONF-V1"


@dataclass(frozen=True, slots=True)
class ConfidenceResult:
    score: float  # 0-100
    band: str  # HIGH | MEDIUM | LOW | UNKNOWN
    formula_version: str
    warnings: tuple[str, ...] = ()


def compute_confidence(
    *,
    source_reliability: float | None = None,  # 0-100 del catálogo/logs
    data_freshness_days: float | None = None,  # días desde última verificación
    historical_samples: int = 0,  # outcomes terminales medidos
    missing_fields: int = 0,  # campos críticos ausentes en la oportunidad
) -> ConfidenceResult:
    """Confianza 0-100 de una recomendación, por sustracción documentada.

    V1 (determinista, sin pesos inventados como 'modelo'): cada input
    desconocido o débil penaliza una cantidad fija y explícita. Inputs
    todos-desconocidos fuerzan banda UNKNOWN — el sistema admite que no
    sabe en lugar de fingir certeza media.
    """
    warnings: list[str] = []
    score = 100.0

    known_inputs = 0

    if source_reliability is None:
        score -= 30
        warnings.append("source_reliability desconocido (-30)")
    else:
        known_inputs += 1
        rel = max(0.0, min(100.0, float(source_reliability)))
        delta = (100.0 - rel) * 0.3  # reliability 60 => -12
        if delta > 0:
            score -= delta
            warnings.append(f"source_reliability {rel:.0f} (-{delta:.1f})")

    if data_freshness_days is None:
        score -= 20
        warnings.append("data_freshness desconocida (-20)")
    else:
        known_inputs += 1
        days = max(0.0, float(data_freshness_days))
        if days > 90:
            score -= 30
            warnings.append(f"frescura {days:.0f}d > 90 (-30)")
        elif days > 30:
            score -= 15
            warnings.append(f"frescura {days:.0f}d > 30 (-15)")

    known_inputs += 1  # historical_samples siempre tiene valor numérico
    samples = int(historical_samples)
    if samples <= 0:
        score -= 25
        warnings.append("sin outcomes históricos (-25)")
    elif samples < 3:
        score -= 10
        warnings.append(f"solo {samples} outcomes (-10)")

    missing = max(0, int(missing_fields))
    if missing:
        penalty = min(24.0, missing * 8.0)
        score -= penalty
        warnings.append(f"{missing} campos críticos ausentes (-{penalty:.0f})")

    final = max(0.0, min(100.0, round(score, 1)))

    if known_inputs <= 1:
        band = "UNKNOWN"
        warnings.append("inputs primarios desconocidos -> banda UNKNOWN")
    elif final >= 70:
        band = "HIGH"
    elif final >= 45:
        band = "MEDIUM"
    else:
        band = "LOW"

    return ConfidenceResult(
        score=final,
        band=band,
        formula_version=CONFIDENCE_FORMULA_VERSION,
        warnings=tuple(warnings),
    )
