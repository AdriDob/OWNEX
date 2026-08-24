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
