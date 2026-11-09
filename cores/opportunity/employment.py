"""Employment relationship for remote job vacancies.

A vacancy is not income, and a permanent remote job is not the same kind of
opportunity as a freelance gig or a three-month contract. This module answers
one question — *what kind of relationship does this vacancy offer?* — so the
income plan can keep permanent employment available in its own category without
letting contract work outrank the deliveries and bounties that actually pay.

Vocabulary is ``cores.direct_work_engine.models.EmploymentType``: no second enum.
Nothing here invents data: when the feed does not say, the result is ``UNKNOWN``
with ``evidence="none"``, never a guessed "permanent".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cores.direct_work_engine.models import EmploymentType


class RelationshipGroup(StrEnum):
    """How the work is contracted — the axis that decides placement, not value."""

    PERMANENT_EMPLOYMENT = "permanent_employment"
    TEMPORARY_EMPLOYMENT = "temporary_employment"
    INDEPENDENT_WORK = "independent_work"
    MICROTASK = "microtask"
    BOUNTY = "bounty"
    UNKNOWN = "unknown"


# The only group allowed in the main income ranking by default. Everything else
# stays reachable in its own category (see scope_for / include_non_permanent).
PRIMARY_GROUPS: frozenset[RelationshipGroup] = frozenset({RelationshipGroup.PERMANENT_EMPLOYMENT})

_GROUP_BY_TYPE: dict[EmploymentType, RelationshipGroup] = {
    EmploymentType.FULL_TIME: RelationshipGroup.PERMANENT_EMPLOYMENT,
    EmploymentType.PART_TIME: RelationshipGroup.PERMANENT_EMPLOYMENT,
    EmploymentType.ROLLING: RelationshipGroup.PERMANENT_EMPLOYMENT,
    EmploymentType.CONTRACT: RelationshipGroup.TEMPORARY_EMPLOYMENT,
    EmploymentType.FREELANCE: RelationshipGroup.INDEPENDENT_WORK,
    EmploymentType.RETAINER: RelationshipGroup.INDEPENDENT_WORK,
    EmploymentType.PROJECT: RelationshipGroup.INDEPENDENT_WORK,
    EmploymentType.OPEN_CALL: RelationshipGroup.INDEPENDENT_WORK,
    EmploymentType.MICROTASK: RelationshipGroup.MICROTASK,
    EmploymentType.CHALLENGE: RelationshipGroup.MICROTASK,
    EmploymentType.BOUNTY: RelationshipGroup.BOUNTY,
    EmploymentType.PRIZE: RelationshipGroup.BOUNTY,
}

# Fields a feed may already carry an explicit answer in, most specific first.
_EXPLICIT_FIELDS: tuple[str, ...] = ("employment_type", "job_type", "contract_type", "type")

# Keyword fallbacks, only used when no explicit field is present. Every entry
# maps to an EmploymentType so there is one vocabulary, not two.
_KEYWORDS: tuple[tuple[EmploymentType, tuple[str, ...]], ...] = (
    (
        EmploymentType.CONTRACT,
        ("temporary", "fixed-term", "fixed term", "temporal", "por tiempo determinado", "maternity cover", "contrato por"),
    ),
    (
        EmploymentType.FREELANCE,
        ("freelance", "contractor", "independent contractor", "autónomo", "autonomo", "por proyecto", "per project"),
    ),
    (
        EmploymentType.MICROTASK,
        ("microtask", "data annotation", "data labeling", "ai training", "evaluación de ia", "model evaluation"),
    ),
    (
        EmploymentType.BOUNTY,
        ("bounty", "bug bounty", "recompensa por vulnerabilidad"),
    ),
    (
        EmploymentType.FULL_TIME,
        ("full-time", "full time", "permanent", "tiempo completo", "relación de dependencia", "relacion de dependencia"),
    ),
    (
        EmploymentType.PART_TIME,
        ("part-time", "part time", "medio tiempo"),
    ),
)


@dataclass(frozen=True)
class EmploymentClassification:
    """What the vacancy offers, with the evidence that says so."""

    employment_type: EmploymentType | None
    relationship: RelationshipGroup
    evidence: str
    inferred: bool

    @property
    def group(self) -> str:
        return str(self.relationship)

    @property
    def is_primary(self) -> bool:
        """True when this may sit in the main income ranking by default."""
        return self.relationship in PRIMARY_GROUPS

    def as_dict(self) -> dict[str, Any]:
        return {
            "employment_type": str(self.employment_type) if self.employment_type else None,
            "relationship": self.group,
            "relationship_evidence": self.evidence,
            "relationship_inferred": self.inferred,
            "primary_eligible": self.is_primary,
        }


def _coerce_employment_type(raw: Any) -> EmploymentType | None:
    """Accept an enum, a feed string ("Full-Time", "CONTRACT") or nothing."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, EmploymentType):
        return raw
    key = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    for member in EmploymentType:
        if member.value == key:
            return member
    return None


def classify(job: dict[str, Any] | None) -> EmploymentClassification:
    """Classify one vacancy. Never guesses: no signal means UNKNOWN."""
    job = job or {}

    for field in _EXPLICIT_FIELDS:
        explicit = _coerce_employment_type(job.get(field))
        if explicit is not None:
            return EmploymentClassification(
                employment_type=explicit,
                relationship=_GROUP_BY_TYPE[explicit],
                evidence=f"field:{field}",
                inferred=False,
            )

    haystack = " ".join(str(job.get(k) or "") for k in ("title", "description", "summary")).lower()
    if haystack.strip():
        for employment_type, keywords in _KEYWORDS:
            for keyword in keywords:
                if keyword in haystack:
                    return EmploymentClassification(
                        employment_type=employment_type,
                        relationship=_GROUP_BY_TYPE[employment_type],
                        evidence=f"keyword:{keyword}",
                        inferred=True,
                    )

    return EmploymentClassification(
        employment_type=None,
        relationship=RelationshipGroup.UNKNOWN,
        evidence="none",
        inferred=False,
    )


def zero_experience_required(job: dict[str, Any] | None, match: dict[str, Any] | None = None) -> bool | None:
    """Whether the vacancy needs no prior professional experience.

    Returns ``None`` when neither the job nor the match says — a vacancy is not
    assumed beginner-friendly just because it was saved.
    """
    for source in (job or {}, match or {}):
        for field in ("zero_experience", "accepts_beginner", "no_experience_required"):
            value = source.get(field)
            if isinstance(value, bool):
                return value
        years = source.get("experience_years")
        if isinstance(years, (int, float)):
            return years <= 0
        for field in ("min_experience_years", "years_required"):
            years = source.get(field)
            if isinstance(years, (int, float)):
                return years <= 0
    return None


def salary_range(job: dict[str, Any] | None, match: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Reported salary as a range with its currency and period — never as cash.

    ``None`` when the feed did not report a salary. A vacancy's advertised pay is
    not a payout and must not be summed with real income.
    """
    job = job or {}
    match = match or {}
    low = match.get("salary_min", job.get("salary_min"))
    high = match.get("salary_max", job.get("salary_max", low))
    if not isinstance(low, (int, float)) and not isinstance(high, (int, float)):
        return None
    currency = job.get("salary_currency") or match.get("salary_currency") or job.get("currency") or "USD"
    period = job.get("salary_period") or match.get("salary_period") or "unknown"
    return {"low": low, "high": high, "currency": currency, "period": period, "source": "feed_reported"}
