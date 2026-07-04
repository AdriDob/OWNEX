"""Financial Truth Layer — single source of truth for all monetary data.

Architecture:
  Ledger (append-only events) → TruthLayer (computes state) → Consumers

Every value exposed is classified into exactly one category:
  - VERIFIED_REAL: confirmed by external API
  - PENDING: externally reported but unpaid
  - ESTIMATED: system inference only
  - MANUAL: user-entered override
  - UNKNOWN: no data available

RULES:
  - State is ALWAYS derived from the ledger, never stored directly
  - No value can exist without a category
  - Synchronization order: API > Cache > Manual > Estimate
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from cores.ledger import (
    LedgerEvent,
    WalletState,
    _entries,
    compute_wallet,
)

logger = logging.getLogger("catseye.financial.truth_layer")


# ── Value Classification ─────────────────────────────────────────────


class ValueCategory(str, Enum):
    VERIFIED_REAL = "verified_real"
    PENDING = "pending"
    ESTIMATED = "estimated"
    MANUAL_INPUT = "manual_input"
    UNKNOWN = "unknown"


SOURCE_CATEGORY_MAP: dict[str, ValueCategory] = {
    "external_api": ValueCategory.VERIFIED_REAL,
    "synced_cache": ValueCategory.PENDING,
    "sync": ValueCategory.PENDING,
    "manual_input": ValueCategory.MANUAL_INPUT,
    "manual": ValueCategory.MANUAL_INPUT,
    "system": ValueCategory.ESTIMATED,
    "estimate": ValueCategory.ESTIMATED,
    "seed_data": ValueCategory.UNKNOWN,
    "unknown": ValueCategory.UNKNOWN,
}

EVENT_CATEGORY_MAP: dict[LedgerEvent, str] = {
    LedgerEvent.PAYOUT_RECEIVED: "verified_real",
    LedgerEvent.WITHDRAWAL_COMPLETED: "verified_real",
    LedgerEvent.BOUNTY_APPROVED: "pending",
    LedgerEvent.BOUNTY_PENDING: "pending",
    LedgerEvent.BOUNTY_CREATED: "estimated",
    LedgerEvent.WITHDRAWAL_REQUESTED: "pending",
    LedgerEvent.WITHDRAWAL_PROCESSING: "pending",
    LedgerEvent.WITHDRAWAL_FAILED: "unknown",
    LedgerEvent.BOUNTY_REJECTED: "unknown",
    LedgerEvent.ADJUSTMENT_MANUAL: "manual_input",
    LedgerEvent.FEE_DEDUCTED: "verified_real",
    LedgerEvent.CURRENCY_CONVERTED: "verified_real",
    LedgerEvent.CRYPTO_DEPOSIT: "verified_real",
    LedgerEvent.CRYPTO_WITHDRAWAL: "verified_real",
    LedgerEvent.CRYPTO_STAKING_REWARD: "verified_real",
    LedgerEvent.CRYPTO_DEFI_YIELD: "verified_real",
    LedgerEvent.CRYPTO_SWAP: "verified_real",
    LedgerEvent.CRYPTO_GAS_FEE: "verified_real",
    LedgerEvent.CRYPTO_AIRDROP: "verified_real",
    LedgerEvent.EXCHANGE_TRADE: "verified_real",
    LedgerEvent.EXCHANGE_FEE: "verified_real",
}


def classify_value(source: str, event: LedgerEvent | None = None) -> ValueCategory:
    """Determine the category of a financial value based on its source and event."""
    if event and event in EVENT_CATEGORY_MAP:
        cat = EVENT_CATEGORY_MAP[event]
        return ValueCategory(cat)
    for prefix, cat in SOURCE_CATEGORY_MAP.items():
        if source.startswith(prefix):
            return cat
    return ValueCategory.UNKNOWN


def confidence_from_source(source: str) -> float:
    confidence_map: dict[str, float] = {
        "external_api": 1.0,
        "verified": 1.0,
        "synced_cache": 0.85,
        "sync": 0.8,
        "manual_input": 0.6,
        "manual": 0.6,
        "system": 0.4,
        "estimate": 0.3,
        "seed_data": 0.05,
    }
    for prefix, conf in confidence_map.items():
        if source.startswith(prefix):
            return conf
    return 0.1


# ── Sync Health ──────────────────────────────────────────────────────


class SyncHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    FAILED = "failed"
    NEVER_SYNCED = "never_synced"


@dataclass
class PlatformSyncState:
    platform_id: str
    last_sync: float = 0.0
    last_success: float = 0.0
    last_error: str = ""
    consecutive_failures: int = 0
    total_syncs: int = 0
    successful_syncs: int = 0
    sync_health: SyncHealth = SyncHealth.NEVER_SYNCED
    rate_limit_remaining: int = 60
    rate_limit_reset: float = 0.0

    @property
    def is_stale(self) -> bool:
        return (time.time() - self.last_success) > 3600

    def record_success(self) -> None:
        now = time.time()
        self.last_sync = now
        self.last_success = now
        self.consecutive_failures = 0
        self.total_syncs += 1
        self.successful_syncs += 1
        self.sync_health = SyncHealth.HEALTHY

    def record_failure(self, error: str) -> None:
        self.last_sync = time.time()
        self.last_error = error[:200]
        self.consecutive_failures += 1
        self.total_syncs += 1
        if self.consecutive_failures >= 5:
            self.sync_health = SyncHealth.FAILED
        elif self.consecutive_failures >= 3:
            self.sync_health = SyncHealth.DEGRADED
        else:
            self.sync_health = SyncHealth.STALE

    def should_retry(self) -> bool:
        if self.sync_health == SyncHealth.FAILED:
            return False
        if self.consecutive_failures == 0:
            return True
        backoff = min(60 * (2 ** (self.consecutive_failures - 1)), 3600)
        return (time.time() - self.last_sync) > backoff


# ── Financial State (derived from ledger) ────────────────────────────


@dataclass
class SourceBreakdown:
    category: ValueCategory
    amount: float = 0.0
    currency: str = "USD"
    confidence: float = 0.0
    entry_count: int = 0
    last_updated: str = ""
    entries: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PlatformFinancialState:
    platform_id: str
    verified_balance: float = 0.0
    pending_balance: float = 0.0
    withdrawn_balance: float = 0.0
    estimated_balance: float = 0.0
    report_count: int = 0
    last_payout: str = ""
    sync_state: PlatformSyncState = field(default_factory=lambda: PlatformSyncState("unknown"))


@dataclass
class SummaryItem:
    label: str
    amount: float
    category: ValueCategory
    confidence: float
    detail: str = ""


@dataclass
class FinancialState:
    verified_balance: float = 0.0
    pending_balance: float = 0.0
    withdrawn_balance: float = 0.0
    estimated_balance: float = 0.0
    manual_balance: float = 0.0
    disputed_balance: float = 0.0

    by_platform: dict[str, PlatformFinancialState] = field(default_factory=dict)
    by_category: dict[str, SourceBreakdown] = field(default_factory=dict)
    sync_health: SyncHealth = SyncHealth.NEVER_SYNCED
    last_sync: str = ""
    last_reconciliation: str = ""
    entry_count: int = 0
    wallet: WalletState | None = None
    summary: list[SummaryItem] = field(default_factory=list)

    @property
    def total_balance(self) -> float:
        return (
            self.verified_balance
            + self.pending_balance
            + self.withdrawn_balance
            + self.estimated_balance
            + self.manual_balance
            + self.disputed_balance
        )

    @property
    def real_balance(self) -> float:
        """Only VERIFIED_REAL money."""
        return self.verified_balance

    @property
    def effective_balance(self) -> float:
        """High-confidence money: verified + pending."""
        return self.verified_balance + self.pending_balance

    @property
    def is_healthy(self) -> bool:
        return self.sync_health in (SyncHealth.HEALTHY, SyncHealth.DEGRADED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified_balance": round(self.verified_balance, 2),
            "pending_balance": round(self.pending_balance, 2),
            "withdrawn_balance": round(self.withdrawn_balance, 2),
            "estimated_balance": round(self.estimated_balance, 2),
            "manual_balance": round(self.manual_balance, 2),
            "disputed_balance": round(self.disputed_balance, 2),
            "total_balance": round(self.total_balance, 2),
            "real_balance": round(self.real_balance, 2),
            "effective_balance": round(self.effective_balance, 2),
            "sync_health": self.sync_health.value,
            "last_sync": self.last_sync,
            "last_reconciliation": self.last_reconciliation,
            "entry_count": self.entry_count,
            "by_platform": {
                pid: {
                    "verified": round(ps.verified_balance, 2),
                    "pending": round(ps.pending_balance, 2),
                    "synced": ps.sync_state.sync_health.value,
                    "last_sync": ps.sync_state.last_sync,
                }
                for pid, ps in self.by_platform.items()
            },
            "by_category": {
                cat: {
                    "amount": round(sb.amount, 2),
                    "confidence": sb.confidence,
                    "entry_count": sb.entry_count,
                }
                for cat, sb in self.by_category.items()
            },
            "summary": [
                {"label": s.label, "amount": round(s.amount, 2), "category": s.category.value, "confidence": s.confidence, "detail": s.detail}
                for s in self.summary
            ],
        }


# ── Truth Layer ──────────────────────────────────────────────────────


class TruthLayer:
    """Single source of truth for all financial data.

    Derives FinancialState by replaying the ledger and classifying every entry.
    """

    def __init__(self) -> None:
        self._platform_syncs: dict[str, PlatformSyncState] = {}
        self._last_reconciliation: str = ""
        self._disputed_entries: set[str] = set()

    def get_state(self) -> FinancialState:
        """Derive complete financial state from the ledger."""
        entries = _entries[:]
        state = FinancialState()
        platform_balances: dict[str, dict[str, float]] = {}
        category_breakdowns: dict[str, dict[str, Any]] = {}

        for e in entries:
            cat = classify_value(e.source, e.event)
            conf = confidence_from_source(e.source)
            amount = abs(e.amount)
            platform = e.platform

            if platform not in platform_balances:
                platform_balances[platform] = {"verified": 0.0, "pending": 0.0, "withdrawn": 0.0, "estimated": 0.0}

            cat_key = cat.value
            if cat_key not in category_breakdowns:
                category_breakdowns[cat_key] = {"amount": 0.0, "count": 0, "confidence": 0.0}

            category_breakdowns[cat_key]["amount"] += amount
            category_breakdowns[cat_key]["count"] += 1
            category_breakdowns[cat_key]["confidence"] = max(
                category_breakdowns[cat_key]["confidence"], conf
            )

            if e.entry_id in self._disputed_entries:
                state.disputed_balance += amount
                continue

            if cat == ValueCategory.VERIFIED_REAL:
                if e.event == LedgerEvent.WITHDRAWAL_COMPLETED:
                    state.withdrawn_balance += amount
                    platform_balances[platform]["withdrawn"] += amount
                else:
                    state.verified_balance += amount
                    platform_balances[platform]["verified"] += amount
            elif cat == ValueCategory.PENDING:
                state.pending_balance += amount
                platform_balances[platform]["pending"] += amount
            elif cat == ValueCategory.ESTIMATED:
                state.estimated_balance += amount
                platform_balances[platform]["estimated"] += amount
            elif cat == ValueCategory.MANUAL_INPUT:
                state.manual_balance += amount

        state.by_category = {}
        for cat_key, data in category_breakdowns.items():
            try:
                cat_enum = ValueCategory(cat_key)
            except ValueError:
                cat_enum = ValueCategory.UNKNOWN
            state.by_category[cat_key] = SourceBreakdown(
                category=cat_enum,
                amount=data["amount"],
                confidence=data["confidence"],
                entry_count=data["count"],
                last_updated=datetime.now(timezone.utc).isoformat(),
            )

        state.by_platform = {}
        for pid, balances in platform_balances.items():
            sync = self._platform_syncs.get(pid, PlatformSyncState(pid))
            state.by_platform[pid] = PlatformFinancialState(
                platform_id=pid,
                verified_balance=balances["verified"],
                pending_balance=balances["pending"],
                withdrawn_balance=balances["withdrawn"],
                estimated_balance=balances["estimated"],
                sync_state=sync,
            )

        state.entry_count = len(entries)
        state.wallet = compute_wallet()

        all_healthy = all(
            ps.sync_state.sync_health == SyncHealth.HEALTHY
            for ps in state.by_platform.values()
        )
        any_failed = any(
            ps.sync_state.sync_health == SyncHealth.FAILED
            for ps in state.by_platform.values()
        )
        all_never = all(
            ps.sync_state.sync_health == SyncHealth.NEVER_SYNCED
            for ps in state.by_platform.values()
        )
        if all_never:
            state.sync_health = SyncHealth.NEVER_SYNCED
        elif any_failed:
            state.sync_health = SyncHealth.FAILED
        elif all_healthy:
            state.sync_health = SyncHealth.HEALTHY
        else:
            state.sync_health = SyncHealth.DEGRADED

        state.last_sync = datetime.now(timezone.utc).isoformat()
        state.last_reconciliation = self._last_reconciliation

        state.summary = self._build_summary(state)
        return state

    def _build_summary(self, state: FinancialState) -> list[SummaryItem]:
        items = []
        if state.verified_balance > 0:
            items.append(SummaryItem(
                label="Dinero real confirmado",
                amount=state.verified_balance,
                category=ValueCategory.VERIFIED_REAL,
                confidence=1.0,
                detail="Sincronizado con plataformas de bug bounty",
            ))
        if state.pending_balance > 0:
            items.append(SummaryItem(
                label="Pagos pendientes",
                amount=state.pending_balance,
                category=ValueCategory.PENDING,
                confidence=0.85,
                detail="Reportados por plataformas, no pagados aún",
            ))
        if state.withdrawn_balance > 0:
            items.append(SummaryItem(
                label="Retirado",
                amount=state.withdrawn_balance,
                category=ValueCategory.VERIFIED_REAL,
                confidence=1.0,
                detail="Retiros completados verificados",
            ))
        if state.estimated_balance > 0:
            items.append(SummaryItem(
                label="Estimado (no verificado)",
                amount=state.estimated_balance,
                category=ValueCategory.ESTIMATED,
                confidence=0.3,
                detail="Inferencia del sistema — confirmar con fuente externa",
            ))
        if state.manual_balance > 0:
            items.append(SummaryItem(
                label="Ajuste manual",
                amount=state.manual_balance,
                category=ValueCategory.MANUAL_INPUT,
                confidence=0.6,
                detail="Ingresado por usuario — verificar contra plataforma",
            ))
        if state.disputed_balance > 0:
            items.append(SummaryItem(
                label="En disputa",
                amount=state.disputed_balance,
                category=ValueCategory.UNKNOWN,
                confidence=0.1,
                detail="Discrepancias detectadas — requiere revisión",
            ))
        return items

    def get_platform_sync(self, platform_id: str) -> PlatformSyncState:
        if platform_id not in self._platform_syncs:
            self._platform_syncs[platform_id] = PlatformSyncState(platform_id)
        return self._platform_syncs[platform_id]

    def record_sync_success(self, platform_id: str) -> None:
        sync = self.get_platform_sync(platform_id)
        sync.record_success()

    def record_sync_failure(self, platform_id: str, error: str) -> None:
        sync = self.get_platform_sync(platform_id)
        sync.record_failure(error)

    def flag_disputed(self, entry_id: str) -> None:
        self._disputed_entries.add(entry_id)

    def resolve_dispute(self, entry_id: str) -> None:
        self._disputed_entries.discard(entry_id)

    def mark_reconciled(self, timestamp: str = "") -> None:
        self._last_reconciliation = timestamp or datetime.now(timezone.utc).isoformat()


_TRUTH: TruthLayer | None = None


def get_truth_layer() -> TruthLayer:
    global _TRUTH
    if _TRUTH is None:
        _TRUTH = TruthLayer()
    return _TRUTH
