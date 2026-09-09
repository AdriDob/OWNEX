from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.opportunity.models import OWNEX_WORK_CYCLE_ORDER, ScoredOpportunity, Top5Recommendation

logger = logging.getLogger("ownex.opportunity.top5")


class Top5Engine:
    def __init__(self, max_per_cycle: int = 2, max_per_source: int = 1) -> None:
        self._max_per_cycle = max_per_cycle
        self._max_per_source = max_per_source

    def compute(
        self,
        opportunities: list[ScoredOpportunity],
        now: str | None = None,
    ) -> Top5Recommendation:
        if not opportunities:
            return Top5Recommendation(
                ranked=[],
                generated_at=now or datetime.now(UTC).isoformat(),
                total_scored=0,
                diversification_note="No opportunities to score.",
                summary="No opportunities available.",
            )

        ranked = sorted(opportunities, key=lambda o: o.score.overall, reverse=True)
        total_scored = len(ranked)
        selected = self._select_diversified(ranked)

        summary = self._build_summary(selected, total_scored)
        note = self._build_diversification_note(selected, total_scored)

        return Top5Recommendation(
            ranked=selected,
            generated_at=now or datetime.now(UTC).isoformat(),
            total_scored=total_scored,
            diversification_note=note,
            summary=summary,
        )

    def _select_diversified(self, ranked: list[ScoredOpportunity]) -> list[ScoredOpportunity]:
        selected: list[ScoredOpportunity] = []
        used_cycles: dict[str, int] = {}
        used_sources: dict[str, int] = {}
        used_ids: set[str] = set()

        scored_with_index = list(enumerate(ranked))
        scored_with_index.sort(
            key=lambda x: (
                -x[1].score.overall,
                OWNEX_WORK_CYCLE_ORDER.index(x[1].cycle) if x[1].cycle in OWNEX_WORK_CYCLE_ORDER else 99,
            )
        )

        for _idx, opp in scored_with_index:
            if len(selected) >= 5:
                break
            if opp.id in used_ids:
                continue
            if used_cycles.get(opp.cycle, 0) >= self._max_per_cycle:
                continue
            if used_sources.get(opp.source_name, 0) >= self._max_per_source:
                continue
            selected.append(opp)
            used_ids.add(opp.id)
            used_cycles[opp.cycle] = used_cycles.get(opp.cycle, 0) + 1
            used_sources[opp.source_name] = used_sources.get(opp.source_name, 0) + 1

        if len(selected) < 5:
            for opp in ranked:
                if len(selected) >= 5:
                    break
                if opp.id in used_ids:
                    continue
                if used_sources.get(opp.source_name, 0) >= self._max_per_source:
                    continue
                selected.append(opp)
                used_ids.add(opp.id)
                used_sources[opp.source_name] = used_sources.get(opp.source_name, 0) + 1

        return selected[:5]

    def _build_summary(self, selected: list[ScoredOpportunity], total: int) -> str:
        if not selected:
            return "No opportunities selected."
        top_name = selected[0].name
        top_ev = selected[0].score.expected_value
        top_cycle = selected[0].cycle
        cycles_covered = len(set(o.cycle for o in selected))
        return (
            f"Top 1: {top_name} (${top_ev:.0f} EV, {top_cycle}). "
            f"Scored {total} opportunities across {cycles_covered} cycles."
        )

    def _build_diversification_note(self, selected: list[ScoredOpportunity], total: int) -> str:
        if not selected:
            return "No opportunities selected."
        cycles = [o.cycle for o in selected]
        unique_cycles = list(dict.fromkeys(cycles))
        return f"Selected {len(selected)} from {total} scored. Cycles: {', '.join(unique_cycles)}."
