"""Data source priority model — tracks provenance of every data point.

Explicit hierarchy:
  1. REAL_EXTERNAL (verified API sync)
  2. SYNCED_CACHE (cached from external)
  3. MANUAL_INPUT (user-entered)
  4. SEED_DATA (dev only — never in production)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class DataProvenance(StrEnum):
    EXTERNAL_API = "external_api"
    SYNCED_CACHE = "synced_cache"
    MANUAL_INPUT = "manual_input"
    SYSTEM = "system"
    SEED_DATA = "seed_data"

    @property
    def priority(self) -> int:
        return {"external_api": 4, "synced_cache": 3, "manual_input": 2, "system": 1, "seed_data": 0}[self.value]

    @property
    def is_production_safe(self) -> bool:
        return self != DataProvenance.SEED_DATA


@dataclass
class ProvenancedValue:
    value: Any
    provenance: DataProvenance
    source_label: str = ""
    timestamp: str = ""
    stale: bool = False

    @property
    def display_label(self) -> str:
        labels = {
            DataProvenance.EXTERNAL_API: "🔵 Sincronizado",
            DataProvenance.SYNCED_CACHE: "🟡 Cache",
            DataProvenance.MANUAL_INPUT: "🟢 Manual",
            DataProvenance.SEED_DATA: "⚪ Demo",
            DataProvenance.SYSTEM: "⚫ Sistema",
        }
        return labels.get(self.provenance, self.provenance.value)


def resolve(*values: ProvenancedValue | None) -> ProvenancedValue | None:
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return max(valid, key=lambda v: v.provenance.priority)
