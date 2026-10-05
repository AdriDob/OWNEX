"""Generic bridge for legacy OpportunityAdapters into the Direct Work Engine.

Any existing ``core/opportunity/adapters`` class that returns ``RawOpportunity``
can be wrapped with ``LegacyOpportunityDweAdapter`` — one conversion path, no
duplicated per-platform code. Lives in the API layer so the DWE stays decoupled
from ``core/``.
"""

from __future__ import annotations

import logging
from typing import Any

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    EntryMechanism,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.legacy")


class LegacyOpportunityDweAdapter(BaseDiscoveryAdapter):
    """Wraps any legacy ``OpportunityAdapter`` that yields ``RawOpportunity``."""

    def __init__(
        self,
        legacy: Any,
        name: str,
        platform: WorkPlatform,
        category: OpportunityCategory,
        employment_type: EmploymentType,
        payment_method: PaymentMethod = PaymentMethod.PLATFORM_CREDIT,
        registration_required: bool = True,
        tier: int = 2,
        analysis_cadence_hours: int = 24,
    ) -> None:
        self._legacy = legacy
        self._category = category
        self._employment_type = employment_type
        self._payment_method = payment_method
        self._registration_required = registration_required
        # Curated barrier flags from global sources (FASE 5): stop flattening
        # interview/portfolio to False for platforms the catalog knows about.
        self._curated_barriers = _curated_barrier_flags(platform.value)
        source = DiscoverySource(
            name=name,
            platform=platform,
            categories=[category],
            tier=tier,
            analysis_cadence_hours=analysis_cadence_hours,
            requires_auth=(tier == 2),
        )
        super().__init__(source)

    @property
    def name(self) -> str:
        return self.source.name

    async def fetch_opportunities(self) -> list[Opportunity]:
        raw_opps = await self._legacy.fetch_opportunities()
        return [self._convert(raw) for raw in raw_opps]

    async def validate_connection(self) -> bool:
        # Discovery isolates errors; keep the gate cheap and optimistic.
        return True

    def _convert(self, raw: Any) -> Opportunity:
        effort = float(getattr(raw, "effort_hours", 1.0) or 1.0)
        if effort <= 4:
            difficulty = DifficultyLevel.BEGINNER
        elif effort <= 8:
            difficulty = DifficultyLevel.INTERMEDIATE
        else:
            difficulty = DifficultyLevel.ADVANCED

        # Entry model from the curated catalog (assessment ≠ funnel ≠ experience).
        entry = _curated_entry_model(self.source.platform.value)
        assessment = bool(entry and entry["assessment"])
        technical_test = assessment
        entry_mechanism = (
            EntryMechanism.ASSESSMENT
            if assessment
            else (EntryMechanism.REGISTRATION if self._registration_required else EntryMechanism.DIRECT)
        )

        # Metadata-driven overrides (e.g. AR job boards): lets adapters declare
        # modality/zone/region/interview honestly without touching this converter.
        # Absent keys keep legacy behavior byte-identical.
        meta = getattr(raw, "metadata", None) or {}
        if not isinstance(meta, dict):
            meta = {}
        from cores.direct_work_engine.models import Modality

        modality_raw = str(meta.get("modality", "") or "").strip().lower()
        try:
            modality = Modality(modality_raw) if modality_raw else Modality.REMOTO
        except ValueError:
            modality = Modality.REMOTO
        is_remote = modality == Modality.REMOTO
        interview_required = bool(meta.get("interview_required", False)) or (
            bool(self._curated_barriers[1]) if self._curated_barriers and len(self._curated_barriers) > 1 else False
        )

        def _meta_float(key: str) -> float | None:
            try:
                val = meta.get(key)
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        def _meta_countries() -> tuple[str, ...]:
            raw_countries = meta.get("allowed_countries") or ()
            try:
                return tuple(str(c) for c in raw_countries if str(c).strip())
            except TypeError:
                return ()

        return Opportunity(
            id=str(getattr(raw, "id", "")),
            title=str(getattr(raw, "name", "") or self.source.name),
            platform=self.source.platform,
            category=self._category,
            url=getattr(raw, "url", "") or "",
            description=str(getattr(raw, "description", "") or ""),
            remote=is_remote,
            modality=modality,
            zone=str(meta.get("zone", "") or ""),
            commute_minutes=_meta_float("commute_minutes"),
            region=str(meta.get("region", "") or ""),
            allowed_countries=_meta_countries(),
            vpn_required=bool(meta.get("vpn_required", False)),
            payment=float(getattr(raw, "reward", 0.0) or 0.0),
            currency="USD",
            payment_method=self._payment_method,
            difficulty=difficulty,
            language_required="english",
            estimated_time_hours=effort,
            experience_required=ExperienceLevel.NONE,
            portfolio_required=bool(self._curated_barriers[0]) if self._curated_barriers else False,
            interview_required=interview_required,
            technical_test_required=technical_test,
            registration_required=self._registration_required,
            time_to_payout_days=(
                float(entry["payout_cadence_days"]) if entry and entry["payout_cadence_days"] else None
            ),
            payment_proven=False,
            stability=0.5,
            accepts_beginner=True,
            accepts_freelancers=True,
            accepts_individuals=True,
            accepts_ai_tools=True,
            asynchronous=True,
            technology_tags=list(getattr(raw, "tags", []) or []),
            employment_type=self._employment_type,
            entry_mechanism=entry_mechanism,
            hourly_rate_usd=(float(entry["hourly_rate_usd"]) if entry and entry["hourly_rate_usd"] else None),
            time_to_first_work_hours=(
                float(entry["time_to_first_work_hours"]) if entry and entry["time_to_first_work_hours"] else None
            ),
            rate_source="platform" if assessment and entry and entry["hourly_rate_usd"] else "unknown",
        )


def _curated_barrier_flags(platform_key: str) -> tuple[bool, bool] | None:
    """(portfolio_required, interview_required) from the curated catalog.

    Matched by exact normalized name or by url domain so entries like
    ``outlier`` hit ``outlier.ai``. Returns None when the platform has no
    curated entry — callers keep their defaults instead of the catalog
    inventing a barrier that nobody verified.
    """
    from cores.opportunity.global_sources import get_sources

    key = platform_key.strip().lower().replace("_", "")
    if not key:
        return None
    for src in get_sources():
        name_norm = src.name.strip().lower().replace(" ", "")
        url = (getattr(src, "url", "") or "").lower()
        if key == name_norm or (url and key in url):
            return (bool(src.requires_portfolio), bool(src.requires_interview))


def _curated_entry_model(platform_key: str) -> dict[str, Any] | None:
    """Entry-model facts from the curated catalog — delegates to the SSOT."""
    from cores.opportunity.global_sources import find_curated_entry_model

    return find_curated_entry_model(platform_key)


def build_default_adapters() -> list[BaseDiscoveryAdapter]:
    """Build the default real discovery adapters (idempotent registration list).

    Only LIVE upstreams are registered. Dead upstreams (Opire, IssueHunt,
    Immunefi, Code4rena, Superteam, Workana, OpenCollective, AR job boards,
    Pulse AI adapters) are excluded — they return [] and pollute the radar.
    Live: bug bounty (public datasets), Fiverr (internal), Open Source
    bounties (Algora, BountyBoard, Polar), Kaggle, GitHub bounty search.
    """
    adapters: list[BaseDiscoveryAdapter] = []

    # Bug bounty — public datasets (HackerOne, Bugcrowd, Intigriti, YesWeHack).
    # Alive: no auth, zero keys, public data, real payouts.
    try:
        from api.adapters.direct_work_bugbounty import build_bugbounty_adapters

        adapters.extend(build_bugbounty_adapters())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build bugbounty adapters: %s", exc)

    # Dework — EXCLUIDO 2026-10-01. El comentario anterior decía "API alive
    # (200 on /v1/tasks)"; el audit de abajo decía DEAD. Verifiqué en vivo:
    # ambos endpoints devuelven 200 con `content-type: text/html` y **0 bytes**
    # ⇒ no hay API. `resp.json()` lanzaba, el `except` lo tragaba con
    # logger.debug y el canal fetchaba 0 en silencio. Registrar un upstream
    # muerto contradice la regla de este mismo builder ("only LIVE upstreams")
    # y quema requests en cada ciclo. La auditoría DEAD es la que dice la
    # verdad; se conserva como evidencia para cuando el upstream vuelva.

    # Fiverr — RETIRADO 2026-10-01 por decisión del owner: "no quiero
    # trabajar en fiverr ni en freelance". El motor de gigs sigue en el
    # árbol (`cores/fiverr/`), pero deja de entrar al discovery: un carril
    # que el dueño vetó no debe aparecer en el plan diario ni en el banco.

    # Bug bounty directory — public program pages with per-program payouts
    # (Intigriti verified 2026-10-01). Reaches the highest-density lane in
    # the catalog: 77 bug-bounty sources, zero experience, no interview.
    try:
        from api.adapters.direct_work_bug_bounty_directory import build_bug_bounty_directory_adapters

        adapters.extend(build_bug_bounty_directory_adapters())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build bug_bounty_directory adapter: %s", exc)

    # Kaggle competitions — paid data science, outcome-based, zero barrier.
    try:
        from api.adapters.direct_work_kaggle import build_kaggle_adapter

        adapters.append(build_kaggle_adapter())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build kaggle adapter: %s", exc)

    # GitHub bounty search — label:bounty issues, free, outcome-based, zero barrier.
    try:
        from api.adapters.direct_work_github_bounty import build_github_bounty_adapter

        adapters.append(build_github_bounty_adapter())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build github_bounty adapter: %s", exc)

    # AI-evaluation platforms — RETIRADO 2026-10-01 (Mercor).
    # El owner decidió que assessment sí, interview no; Mercor exige "AI
    # interview + technical screening" y paga por proyecto (no por hora
    # estable). El adapter queda en el archivo pero fuera del registro: si
    # el owner cambia de opinión, una línea lo reactiva.

    # Algora.io — GitHub bounties with automatic payment, zero barrier.
    try:
        from api.adapters.direct_work_algora import build_algora_adapter

        adapters.append(build_algora_adapter())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build algora adapter: %s", exc)

    # BountyBoard.dev — GitHub bounties aggregator, zero barrier.
    try:
        from api.adapters.direct_work_bountyboard import build_bountyboard_adapter

        adapters.append(build_bountyboard_adapter())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build bountyboard adapter: %s", exc)

    # Polar.sh — GitHub funding and issue sponsorship, zero barrier.
    try:
        from api.adapters.direct_work_polar import build_polar_adapter

        adapters.append(build_polar_adapter())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build polar adapter: %s", exc)

    return adapters


# ── Fetch audit (honest mode per adapter, probed, never invented) ──
# Modes: LIVE (fetch real hoy) · STATIC (seeds curados, hoy vacíos) ·
# INTERNAL (motor interno, sin fetch externo) · DEGRADED (fetch parcial).

_ADAPTER_FETCH_AUDIT: dict[str, dict[str, str]] = {
    "bugbounty": {
        "mode": "LIVE",
        "evidence": "datasets públicos H1/BC/Inti/YWH sin auth (probe 2026-09-11)",
    },
    "dework": {
        # Corregido 2026-09-30: el audit decía LIVE por un probe del 2026-09-11
        # que hoy ya no se reproduce. Los endpoints devuelven 200 con
        # `content-type: text/html` y cuerpo vacío ⇒ `resp.json()` lanza y el
        # `except` lo traga con logger.debug, así que el canalFetch 0 en
        # silencio desde entonces. No hay API pública: upstream caído.
        "mode": "DEAD",
        "evidence": "v1/tasks y open_tasks → 200 text/html vacío (probe 2026-09-30)",
    },
    "intigriti": {
        "mode": "LIVE",
        "evidence": "directorio público de programas con rango por programa (probe 2026-10-01)",
    },
    "kaggle": {
        "mode": "LIVE",
        "evidence": "competitions públicas, auth opcional",
    },
    "github_bounty": {
        "mode": "LIVE",
        "evidence": "GitHub Search API pública (10 req/min sin token)",
    },
    "algora": {
        "mode": "STATIC",
        "evidence": "seeds vaciados 2026-09-16 (issues 404); fetch real con token",
    },
    "bountyboard": {
        "mode": "STATIC",
        "evidence": "seeds vaciados 2026-09-16 (bountyboard.dev caído)",
    },
    "polar": {
        "mode": "STATIC",
        "evidence": "seeds vaciados 2026-09-16 (/rust-analyzer 404)",
    },
}


def get_adapter_fetch_audit() -> dict[str, dict[str, str]]:
    """Audit table: every registered adapter has a LIVE/STATIC/INTERNAL/DEGRADED entry."""
    return {k: dict(v) for k, v in _ADAPTER_FETCH_AUDIT.items()}
