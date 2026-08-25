"""Fallback strategy chain — Income Multiplier Fase F (spec §22).

OWNEX never depends on a single platform: the recommendation carries a
PRIMARY plus up to N FALLBACKS on *different* platforms, each with an
explicit activation trigger ("si X no tiene tareas disponibles...").

Honesty contract: this is pure selection over ALREADY-RANKED
opportunities — it invents no opportunities and assigns no scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_FALLBACKS = 3


@dataclass(frozen=True, slots=True)
class FallbackEntry:
    rank: int
    platform: str
    title: str
    expected_cash_date: str | None = None
    confidence_band: str | None = None
    trigger: str = ""


@dataclass(frozen=True, slots=True)
class FallbackChain:
    primary: FallbackEntry | None
    fallbacks: list[FallbackEntry] = field(default_factory=list)
    warnings: tuple[str, ...] = ()

    def as_list(self) -> list[FallbackEntry]:
        """Primary + fallbacks en orden de ejecución."""
        if self.primary is None:
            return []
        return [self.primary, *self.fallbacks]


def _entry_from(item: dict, rank: int, trigger: str) -> FallbackEntry:
    opp = item.get("opportunity") or {}
    cash = item.get("expected_cash") or {}
    return FallbackEntry(
        rank=rank,
        platform=str(opp.get("platform", item.get("platform", "?"))),
        title=str(opp.get("title", item.get("title", ""))),
        expected_cash_date=cash.get("expected_date"),
        confidence_band=item.get("confidence_band"),
        trigger=trigger,
    )


def build_fallback_chain(
    ranked_items: list[dict],
    *,
    max_fallbacks: int = MAX_FALLBACKS,
) -> FallbackChain:
    """Select primary + diversified fallbacks over pre-ranked payload.

    Diversity rule (§22): cada fallback vive en una plataforma distinta a
    la del primary y entre sí — si la plataforma primaria se cae o se queda
    sin tareas, la alternativa ya no compite por el mismo punto único de
    falla. Los items deben venir rankeados (rank descendente); esta función
    NO reordena ni puntúa.
    """
    warnings: list[str] = []
    if not ranked_items:
        warnings.append("sin oportunidades rankeadas")
        return FallbackChain(primary=None, warnings=tuple(warnings))

    ordered = sorted(ranked_items, key=lambda i: i.get("rank", 10**6))
    primary = _entry_from(ordered[0], 1, "mejor opción actual")

    fallbacks: list[FallbackEntry] = []
    seen_platforms = {primary.platform}
    for item in ordered[1:]:
        if len(fallbacks) >= max_fallbacks:
            break
        probe = _entry_from(item, 0, "")
        if probe.platform in seen_platforms:
            continue  # misma plataforma = mismo punto único de falla
        fallback_no = len(fallbacks) + 1
        fallbacks.append(
            FallbackEntry(
                rank=fallback_no + 1,
                platform=probe.platform,
                title=probe.title,
                expected_cash_date=probe.expected_cash_date,
                confidence_band=probe.confidence_band,
                trigger=(
                    f"fallback #{fallback_no}: si {primary.platform} no tiene tareas disponibles o falla la postulación"
                ),
            )
        )
        seen_platforms.add(probe.platform)

    if not fallbacks:
        warnings.append("sin alternativas en plataformas distintas — riesgo de dependencia única")

    return FallbackChain(
        primary=primary,
        fallbacks=fallbacks,
        warnings=tuple(warnings),
    )
