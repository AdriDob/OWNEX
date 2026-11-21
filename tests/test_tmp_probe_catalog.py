"""Temporary probe (deleted after reading output)."""

from __future__ import annotations

from cores.opportunity.global_sources import get_base_sources, get_sources
from cores.opportunity.source_families import SourceFamily, source_family_for


def test_probe() -> None:
    capped = {s.name for s in get_sources()}
    base = get_base_sources()
    ai_dropped = [
        (s.name, s.priority, s.quality_score) for s in base if s.name not in capped and source_family_for(s) is SourceFamily.AI_CODING_EVALUATION
    ]
    devops_dropped = [
        (s.name, s.priority, s.quality_score) for s in base if s.name not in capped and source_family_for(s) is SourceFamily.DEVOPS_CLOUD_TASKS
    ]
    raise AssertionError(f"ai_dropped={ai_dropped} devops_dropped={devops_dropped}")
