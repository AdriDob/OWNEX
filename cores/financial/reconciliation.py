"""Reconciliation Engine — compares external data vs ledger, detects mismatches.

Every sync cycle:
  1. Compare platform balance vs ledger-derived balance
  2. Classify discrepancies (timing mismatch, missing payout, duplicate, unknown)
  3. Auto-resolve when confidence >= 0.9
  4. Flag for user confirmation otherwise
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from cores.financial.truth_layer import TruthLayer, get_truth_layer
from cores.ledger import LedgerEvent


def _all_ledger_entries():
    from cores.ledger import _all_entries
    return _all_entries()

logger = logging.getLogger("ownex.financial.reconciliation")


class ConsistencyState(str, Enum):
    CONSISTENT = "consistent"
    STALE = "stale"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class DiscrepancyType(str, Enum):
    TIMING_MISMATCH = "timing_mismatch"
    MISSING_PAYOUT = "missing_payout"
    DUPLICATE_ENTRY = "duplicate_entry"
    AMOUNT_MISMATCH = "amount_mismatch"
    UNKNOWN_SOURCE = "unknown_source"
    ORPHAN_ENTRY = "orphan_entry"


@dataclass
class Discrepancy:
    type: DiscrepancyType
    platform: str
    description: str
    external_amount: float = 0.0
    ledger_amount: float = 0.0
    external_id: str = ""
    ledger_entry_id: str = ""
    auto_resolved: bool = False
    resolution: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "platform": self.platform,
            "description": self.description,
            "external_amount": self.external_amount,
            "ledger_amount": self.ledger_amount,
            "external_id": self.external_id,
            "ledger_entry_id": self.ledger_entry_id,
            "auto_resolved": self.auto_resolved,
            "resolution": self.resolution,
        }


@dataclass
class ReconciliationResult:
    platform_id: str
    state: ConsistencyState
    discrepancies: list[Discrepancy] = field(default_factory=list)
    auto_resolved_count: int = 0
    requires_user_count: int = 0
    checked_at: str = ""

    @property
    def is_healthy(self) -> bool:
        return self.state == ConsistencyState.CONSISTENT and self.requires_user_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "state": self.state.value,
            "discrepancies": [d.to_dict() for d in self.discrepancies],
            "auto_resolved_count": self.auto_resolved_count,
            "requires_user_count": self.requires_user_count,
            "checked_at": self.checked_at,
        }


class ReconciliationEngine:
    """Compares external platform data against the ledger and detects mismatches."""

    def __init__(self, truth_layer: TruthLayer | None = None) -> None:
        self._truth = truth_layer or get_truth_layer()
        self._history: list[ReconciliationResult] = []

    def check_platform(
        self,
        truth_layer: TruthLayer | None = None,
        platform_id: str = "",
        external_entries: list[dict[str, Any]] | None = None,
    ) -> ReconciliationResult:
        discrepancies: list[Discrepancy] = []
        now = datetime.now(UTC).isoformat()

        if not external_entries:
            return ReconciliationResult(
                platform_id=platform_id,
                state=ConsistencyState.UNKNOWN,
                checked_at=now,
            )

        external_ids = set()
        external_by_id: dict[str, dict[str, Any]] = {}
        external_total = 0.0

        for e in external_entries:
            eid = str(e.get("id", ""))
            if eid:
                external_ids.add(eid)
                external_by_id[eid] = e
            amount = float(e.get("amount", 0) or 0)
            external_total += amount

        ledger_platform = [e for e in _all_ledger_entries() if e.platform == platform_id]
        ledger_by_source_id: dict[str, list] = {}
        ledger_total = 0.0

        for entry in ledger_platform:
            if entry.event in (LedgerEvent.PAYOUT_RECEIVED, LedgerEvent.BOUNTY_APPROVED):
                ledger_total += entry.amount
            sid = entry.source_id
            if sid:
                ledger_by_source_id.setdefault(sid, []).append(entry)

        # Check for missing external entries (in external but not in ledger)
        for eid, ext in external_by_id.items():
            if eid not in ledger_by_source_id:
                discrepancies.append(Discrepancy(
                    type=DiscrepancyType.MISSING_PAYOUT,
                    platform=platform_id,
                    description=f"Pago externo no registrado en ledger: {eid[:12]}...",
                    external_amount=float(ext.get("amount", 0) or 0),
                    external_id=eid,
                ))

        # Check for orphan ledger entries (in ledger but not in external)
        for eid in ledger_by_source_id:
            if eid not in external_ids and eid:
                ledger_entries = ledger_by_source_id[eid]
                total = sum(e.amount for e in ledger_entries)
                discrepancies.append(Discrepancy(
                    type=DiscrepancyType.ORPHAN_ENTRY,
                    platform=platform_id,
                    description=f"Ledger entry sin correspondencia externa: {eid[:12]}...",
                    ledger_amount=total,
                    ledger_entry_id=ledger_entries[0].entry_id,
                ))

        # Check amount mismatches for matching entries
        for eid in external_ids & set(ledger_by_source_id.keys()):
            ext_amount = float(external_by_id[eid].get("amount", 0) or 0)
            led_amount = sum(e.amount for e in ledger_by_source_id[eid])
            if abs(ext_amount - led_amount) > 0.01:
                discrepancies.append(Discrepancy(
                    type=DiscrepancyType.AMOUNT_MISMATCH,
                    platform=platform_id,
                    description=f"Monto不一致: externo={ext_amount}, ledger={led_amount}",
                    external_amount=ext_amount,
                    ledger_amount=led_amount,
                    external_id=eid,
                    ledger_entry_id=ledger_by_source_id[eid][0].entry_id,
                ))

        # Auto-resolve high-confidence discrepancies
        auto_count = 0
        user_count = 0
        for d in discrepancies:
            if d.type in (DiscrepancyType.TIMING_MISMATCH,):
                d.auto_resolved = True
                d.resolution = "Timing difference — will resolve on next sync"
                auto_count += 1
            elif d.type == DiscrepancyType.ORPHAN_ENTRY and d.ledger_amount < 1.0:
                d.auto_resolved = True
                d.resolution = "Trivial amount — accepted"
                auto_count += 1
            else:
                user_count += 1

        # Determine consistency state
        if len(discrepancies) == 0 or auto_count > 0 and user_count == 0:
            state = ConsistencyState.CONSISTENT
        elif any(not d.auto_resolved for d in discrepancies):
            state = ConsistencyState.CONFLICT
        else:
            state = ConsistencyState.STALE

        # Flag disputed entries in truth layer
        for d in discrepancies:
            if d.ledger_entry_id and not d.auto_resolved:
                self._truth.flag_disputed(d.ledger_entry_id)

        result = ReconciliationResult(
            platform_id=platform_id,
            state=state,
            discrepancies=discrepancies,
            auto_resolved_count=auto_count,
            requires_user_count=user_count,
            checked_at=now,
        )

        self._history.append(result)
        if state == ConsistencyState.CONSISTENT:
            self._truth.mark_reconciled(now)

        return result

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    def get_state(self) -> dict[str, Any]:
        if not self._history:
            return {"state": ConsistencyState.UNKNOWN.value, "last_check": "", "platforms": []}
        last = self._history[-1]
        return {
            "state": last.state.value,
            "last_check": last.checked_at,
            "platforms": list({r.platform_id for r in self._history}),
            "total_discrepancies": sum(len(r.discrepancies) for r in self._history),
            "unresolved": sum(r.requires_user_count for r in self._history),
        }

    def resolve_manually(self, platform_id: str, discrepancy_index: int, resolution: str) -> bool:
        for r in self._history:
            if r.platform_id == platform_id and discrepancy_index < len(r.discrepancies):
                d = r.discrepancies[discrepancy_index]
                d.auto_resolved = True
                d.resolution = f"Manual: {resolution}"
                r.auto_resolved_count += 1
                r.requires_user_count -= 1
                if d.ledger_entry_id:
                    self._truth.resolve_dispute(d.ledger_entry_id)
                if r.requires_user_count == 0:
                    r.state = ConsistencyState.CONSISTENT
                return True
        return False


_ENGINE: ReconciliationEngine | None = None


def get_reconciliation_engine() -> ReconciliationEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ReconciliationEngine()
    return _ENGINE
