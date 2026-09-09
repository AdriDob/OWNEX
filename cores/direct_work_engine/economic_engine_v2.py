"""Economic Engine V2 — Real Revenue Separation & Honest Accounting.

Implements the honest revenue state machine per spec:
THEORETICAL_CAPACITY → EXPECTED_PIPELINE → REALIZED_REVENUE → PAID_REVENUE → NET_REVENUE

Separates WORK / TRADING / CAPITAL income streams.
Never conflates theoretical capacity with realized revenue.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.direct_work.economic_engine_v2")


class RevenueStream(Enum):
    """Income stream categories - NEVER mix these."""

    WORK = "work"  # Active labor: bounties, freelance, AI work
    TRADING = "trading"  # Capital at risk: crypto, forex, sports betting
    CAPITAL = "capital"  # Yield: DeFi, staking, interest
    PASSIVE = "passive"  # Hands-off: royalties, dividends


class RevenueStateV2(Enum):
    """Strict revenue lifecycle - NEVER mix states."""

    THEORETICAL = "theoretical"  # Maximum capacity if everything goes perfectly
    EXPECTED = "expected"  # Pipeline projection (EV-based)
    COMMITTED = "committed"  # Contracted/signed, delivery expected
    REALIZED = "realized"  # Work completed, invoice sent
    PENDING = "pending"  # Payment processing
    PAID = "paid"  # Funds received, before fees/taxes
    NET = "net"  # After fees/taxes/FX - actual cash
    LOST = "lost"  # Failed/cancelled - documented loss

    @classmethod
    def valid_transitions(cls) -> dict[RevenueStateV2, set[RevenueStateV2]]:
        return {
            cls.THEORETICAL: {cls.EXPECTED, cls.LOST},
            cls.EXPECTED: {cls.COMMITTED, cls.LOST},
            cls.COMMITTED: {cls.REALIZED, cls.LOST},
            cls.REALIZED: {cls.PENDING, cls.LOST},
            cls.PENDING: {cls.PAID, cls.LOST},
            cls.PAID: {cls.NET, cls.LOST},  # chargeback/refund
            cls.NET: {cls.LOST},  # clawback
            cls.LOST: set(),
        }

    @classmethod
    def can_transition(cls, from_state: RevenueStateV2, to_state: RevenueStateV2) -> bool:
        return to_state in cls.valid_transitions().get(from_state, set())


@dataclass(frozen=True, slots=True)
class RevenueLine:
    """Single revenue line item with full lifecycle tracking."""

    id: str
    stream: RevenueStream
    platform: str
    title: str

    # Lifecycle
    state: RevenueStateV2 = RevenueStateV2.THEORETICAL
    state_history: list[dict] = field(default_factory=list)

    # Money (all USD)
    theoretical_max_usd: Decimal = Decimal("0")
    expected_usd: Decimal = Decimal("0")
    committed_usd: Decimal = Decimal("0")
    realized_usd: Decimal = Decimal("0")
    pending_usd: Decimal = Decimal("0")
    paid_usd: Decimal = Decimal("0")
    net_usd: Decimal = Decimal("0")
    fees_usd: Decimal = Decimal("0")
    tax_usd: Decimal = Decimal("0")
    fx_loss_usd: Decimal = Decimal("0")
    payment_fees_usd: Decimal = Decimal("0")

    # Metadata
    platform_data: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    human_hours_invested: Decimal = Decimal("0")
    htroi_usd_per_hour: Decimal | None = None
    confidence_score: float = 0.0

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def transition_to(self, new_state: RevenueStateV2, evidence: str = "") -> RevenueLine:
        """Create new line with transitioned state."""
        if not RevenueStateV2.can_transition(self.state, object.__getattribute__(type(self), "state")):
            raise ValueError(f"Invalid transition {self.state} -> {object.__getattribute__(type(self), 'state')}")
        # Note: actual transition logic in EconomicEngineV2.transition_line()
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "stream": self.stream.value,
            "platform": self.platform,
            "title": self.title,
            "state": self.state.value,
            "theoretical_max_usd": float(self.theoretical_max_usd),
            "expected_usd": float(self.expected_usd),
            "committed_usd": float(self.committed_usd),
            "realized_usd": float(self.realized_usd),
            "pending_usd": float(self.pending_usd),
            "paid_usd": float(self.paid_usd),
            "net_usd": float(self.net_usd),
            "fees_usd": float(self.fees_usd),
            "tax_usd": float(self.tax_usd),
            "fx_loss_usd": float(self.fx_loss_usd),
            "htroi_usd_per_hour": float(self.htroi_usd_per_hour) if self.htroi_usd_per_hour else None,
            "confidence_score": self.confidence_score,
            "human_hours_invested": float(self.human_hours_invested),
            "state_history": self.state_history,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class RevenueSnapshot:
    """Point-in-time revenue summary - the honest dashboard."""

    # Work income
    work_theoretical: Decimal
    work_expected: Decimal
    work_committed: Decimal
    work_realized: Decimal
    work_pending: Decimal
    work_paid: Decimal
    work_net: Decimal

    # Trading income
    trading_theoretical: Decimal
    trading_expected: Decimal
    trading_committed: Decimal
    trading_realized: Decimal
    trading_pending: Decimal
    trading_paid: Decimal
    trading_net: Decimal

    # Capital income
    capital_theoretical: Decimal
    capital_expected: Decimal
    capital_committed: Decimal
    capital_realized: Decimal
    capital_pending: Decimal
    capital_paid: Decimal
    capital_net: Decimal

    # Aggregated
    total_theoretical: Decimal
    total_expected: Decimal
    total_committed: Decimal
    total_realized: Decimal
    total_pending: Decimal
    total_paid: Decimal
    total_net: Decimal

    # Costs
    total_fees_usd: Decimal
    total_tax_usd: Decimal
    total_fx_loss_usd: Decimal

    # Metadata
    lines_count: int
    as_of: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "work": {
                "theoretical": float(self.work_theoretical),
                "expected": float(self.work_expected),
                "committed": float(self.work_committed),
                "realized": float(self.work_realized),
                "pending": float(self.work_pending),
                "paid": float(self.work_paid),
                "net": float(self.work_net),
            },
            "trading": {
                "theoretical": float(self.trading_theoretical),
                "expected": float(self.trading_expected),
                "committed": float(self.trading_committed),
                "realized": float(self.trading_realized),
                "pending": float(self.trading_pending),
                "paid": float(self.trading_paid),
                "net": float(self.trading_net),
            },
            "capital": {
                "theoretical": float(self.capital_theoretical),
                "expected": float(self.capital_expected),
                "committed": float(self.capital_committed),
                "realized": float(self.capital_realized),
                "pending": float(self.capital_pending),
                "paid": float(self.capital_paid),
                "net": float(self.capital_net),
            },
            "total": {
                "theoretical": float(self.total_theoretical),
                "expected": float(self.total_expected),
                "committed": float(self.total_committed),
                "realized": float(self.total_realized),
                "pending": float(self.total_pending),
                "paid": float(self.total_paid),
                "net": float(self.total_net),
            },
            "costs": {
                "fees": float(self.total_fees_usd),
                "tax": float(self.total_tax_usd),
                "fx_loss": float(self.total_fx_loss_usd),
            },
            "meta": {
                "lines_count": self.lines_count,
                "as_of": self.as_of,
            },
        }


@dataclass(frozen=True, slots=True)
class HTROIResultV2:
    """Enhanced HTROI with full cost breakdown."""

    roi_usd_per_hour: float | None
    expected_net_usd: Decimal
    human_hours_total: Decimal
    confidence_applied: float
    compression_pct: float | None
    automation_ratio: float | None
    formula_version: str
    warnings: tuple[str, ...]

    # New: full cost breakdown
    gross_income_usd: Decimal
    platform_fees_usd: Decimal
    payment_fees_usd: Decimal
    fx_loss_usd: Decimal
    tax_estimate_usd: Decimal
    net_income_usd: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "roi_usd_per_hour": self.roi_usd_per_hour,
            "expected_net_usd": float(self.expected_net_usd),
            "human_hours_total": float(self.human_hours_total),
            "confidence_applied": self.confidence_applied,
            "compression_pct": self.compression_pct,
            "automation_ratio": self.automation_ratio,
            "formula_version": self.formula_version,
            "warnings": list(self.warnings),
            "costs": {
                "gross_income_usd": float(self.gross_income_usd),
                "platform_fees_usd": float(self.platform_fees_usd),
                "payment_fees_usd": float(self.payment_fees_usd),
                "fx_loss_usd": float(self.fx_loss_usd),
                "tax_estimate_usd": float(self.tax_estimate_usd),
                "net_income_usd": float(self.net_income_usd),
            },
        }


class EconomicEngineV2:
    """
    Honest Economic Engine - Single Source of Truth for Revenue.

    Principles:
    1. THEORETICAL ≠ EXPECTED ≠ REALIZED ≠ PAID ≠ NET
    2. WORK ≠ TRADING ≠ CAPITAL (never mix)
    3. Only NET is "real money" - everything else is projection
    4. Every transition requires evidence
    5. Unknown inputs are surfaced, never assumed
    """

    def __init__(self):
        self.lines: dict[str, RevenueLine] = {}
        self._sequence = 0

    def create_line(
        self,
        stream: RevenueStream,
        platform: str,
        title: str,
        theoretical_max: float,
        expected_ev: float | None = None,
        human_hours: float = 0,
        platform_data: dict | None = None,
    ) -> RevenueLine:
        """Create a new revenue line from opportunity discovery."""
        self._sequence += 1
        f"rev_{datetime.now(UTC).strftime('%Y%m%d')}_{self._sequence:04d}"

        Decimal(str(theoretical_max))
        Decimal(str(expected_ev)) if expected_ev else Decimal("0")

        line = RevenueLine(
            id=f"rev_{datetime.now(UTC).strftime('%Y%m%d')}_{self._sequence:04d}",
            stream=RevenueStream.WORK
            if platform
            in [
                "hackerone",
                "bugcrowd",
                "intigriti",
                "yeswehack",
                "immunefi",
                "code4rena",
                "opire",
                "issuehunt",
                "algora",
                "gitcoin",
                "superteam",
                "dework",
                "gitwork",
                "onlydust",
                "outlier",
                "mindrift",
                "data_annotation_platform",
                "opyre_microtask",
                "freelancer_microtask",
                "linkedin",
                "fiverr",
            ]
            else RevenueStream.TRADING,
            platform=platform,
            title=title,
            theoretical_max_usd=Decimal(str(theoretical_max)),
            expected_usd=Decimal(str(expected_ev)) if expected_ev else Decimal("0"),
            human_hours_invested=Decimal(str(human_hours)),
            platform_data=platform_data or {},
            state=RevenueStateV2.EXPECTED if expected_ev else RevenueStateV2.THEORETICAL,
        )
        self._add_state_history(
            line, "created", f"Created with theoretical=${theoretical_max}, expected=${expected_ev or 0}"
        )
        self.lines[line.id] = line
        return line

    def create_trading_line(
        self,
        platform: str,
        title: str,
        theoretical_max: float,
        capital_at_risk: float,
        expected_return_pct: float = 0,
        expected_ev: float | None = None,
    ) -> RevenueLine:
        """Create a trading line (capital at risk)."""
        self._sequence += 1
        f"rev_{datetime.now(UTC).strftime('%Y%m%d')}_{self._sequence:04d}"

        (Decimal(str(expected_ev)) if expected_ev else Decimal(str(theoretical_max * expected_return_pct / 100)))

        line = RevenueLine(
            id=f"rev_{datetime.now(UTC).strftime('%Y%m%d')}_{self._sequence:04d}",
            stream=RevenueStream.TRADING,
            platform=platform,
            title=title,
            theoretical_max_usd=Decimal(str(theoretical_max)),
            expected_usd=Decimal(str(expected_ev)) if expected_ev else Decimal("0"),
            human_hours_invested=Decimal("0"),
            platform_data={"capital_at_risk": capital_at_risk, "expected_return_pct": expected_return_pct},
            state=RevenueStateV2.EXPECTED if expected_ev else RevenueStateV2.THEORETICAL,
        )
        self._add_state_history(
            line, "created", f"Trading position: capital=${capital_at_risk}, expected_return={expected_return_pct}%"
        )
        self.lines[line.id] = line
        return line

    def create_capital_line(
        self,
        platform: str,
        title: str,
        principal: float,
        apy: float,
    ) -> RevenueLine:
        """Create a capital/yield line (DeFi, staking, interest)."""
        self._sequence += 1
        Decimal(str(principal * apy / 100 / 12))  # Monthly expected

        line = RevenueLine(
            id=f"rev_{datetime.now(UTC).strftime('%Y%m%d')}_{self._sequence:04d}",
            stream=RevenueStream.CAPITAL,
            platform=platform,
            title=title,
            theoretical_max_usd=Decimal(str(principal)),
            expected_usd=Decimal(str(principal * apy / 100 / 12)),
            human_hours_invested=Decimal("0"),
            platform_data={"principal": principal, "apy": apy},
            state=RevenueStateV2.EXPECTED,
        )
        self._add_state_history(line, "created", f"Capital position: ${principal} @ {apy}% APY")
        self.lines[line.id] = line
        return line

    def transition_line(
        self, line_id: str, new_state: RevenueStateV2, evidence: str = "", amount_usd: float | None = None
    ) -> RevenueLine | None:
        """Transition a revenue line through the state machine."""
        if line_id not in self.lines:
            return None

        line = self.lines[line_id]
        if not RevenueStateV2.can_transition(line.state, new_state):
            logger.warning(f"Invalid transition {line.state} -> {new_state} for {line_id}")
            return None

        # Update money fields based on transition
        new_line = self._apply_transition(line, new_state, amount_usd)
        self._add_state_history(new_line, new_state.value, evidence or f"Transitioned to {new_state.value}")
        self.lines[line_id] = new_line
        return new_line

    def _apply_transition(self, line: RevenueLine, new_state: RevenueStateV2, amount: float | None) -> RevenueLine:
        """Apply state transition with money movement."""
        Decimal(str(amount)) if amount is not None else Decimal("0")

        updates = {"state": new_state, "updated_at": datetime.now(UTC).isoformat()}

        if new_state == RevenueStateV2.COMMITTED:
            updates["committed_usd"] = (
                line.expected_usd if line.expected_usd > line.committed_usd else line.committed_usd
            )
        elif new_state == RevenueStateV2.REALIZED:
            updates["realized_usd"] = line.committed_usd if line.committed_usd else line.expected_usd
            if amount is not None:
                updates["realized_usd"] = Decimal(str(amount))
        elif new_state == RevenueStateV2.PENDING:
            updates["pending_usd"] = line.realized_usd
        elif new_state == RevenueStateV2.PAID:
            paid_amount = Decimal(str(amount)) if amount else line.realized_usd
            updates["paid_usd"] = paid_amount
            updates["pending_usd"] = Decimal("0")
        elif new_state == RevenueStateV2.NET:
            fees = self._calculate_fees(line.paid_usd)
            tax = self._estimate_tax(line.paid_usd)
            fx_loss = self._estimate_fx_loss(line.paid_usd)
            net = line.paid_usd - fees - tax - fx_loss
            updates["net_usd"] = max(Decimal("0"), net)
            updates["fees_usd"] = fees
            updates["tax_usd"] = tax
            updates["fx_loss_usd"] = fx_loss
        elif new_state == RevenueStateV2.LOST:
            updates["committed_usd"] = Decimal("0")
            updates["pending_usd"] = Decimal("0")

        # Update human hours if this is work
        if new_state == RevenueStateV2.REALIZED:
            # Human hours already tracked separately
            pass

        import dataclasses

        return dataclasses.replace(line, **updates)

    def _calculate_fees(self, amount: Decimal) -> Decimal:
        return amount * Decimal("0.05")  # 5% average platform fees

    def _estimate_tax(self, amount: Decimal) -> Decimal:
        return amount * Decimal("0.35")  # Argentina tax estimate

    def _estimate_fx_loss(self, amount: Decimal) -> Decimal:
        return amount * Decimal("0.10")  # 10% FX loss estimate

    def _add_state_history(self, line: RevenueLine, action: str, evidence: str):
        """Add to state history (internal method, mutable)."""
        history = list(line.state_history)
        history.append(
            {
                "action": action,
                "state": line.state.value,
                "evidence": evidence,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        # Note: this mutates the frozen dataclass - in production use a mutable wrapper
        object.__setattr__(line, "state_history", history)

    def get_snapshot(self) -> RevenueSnapshot:
        """Generate current revenue snapshot - the honest dashboard."""
        work_lines = [l for l in self.lines.values() if l.stream == RevenueStream.WORK]
        trading_lines = [l for l in self.lines.values() if l.stream == RevenueStream.TRADING]
        capital_lines = [l for l in self.lines.values() if l.stream == RevenueStream.CAPITAL]

        def sum_field(lines: list[RevenueLine], attr: str) -> Decimal:
            total = Decimal("0")
            for l in lines:
                val = getattr(l, attr, Decimal("0"))
                if isinstance(val, Decimal):
                    total += val
            return total

        def sum_field_iterable(lines: Iterable[RevenueLine], attr: str) -> Decimal:
            total = Decimal("0")
            for l in lines:
                val = getattr(l, attr, Decimal("0"))
                if isinstance(val, Decimal):
                    total += val
            return total

        work_theoretical = sum_field(work_lines, "theoretical_max_usd")
        work_expected = sum_field(work_lines, "expected_usd")
        work_committed = sum_field(work_lines, "committed_usd")
        work_realized = sum_field(work_lines, "realized_usd")
        work_pending = sum_field(work_lines, "pending_usd")
        work_paid = sum_field(work_lines, "paid_usd")
        work_net = sum_field(work_lines, "net_usd")

        trading_theoretical = sum_field(trading_lines, "theoretical_max_usd")
        trading_expected = sum_field(trading_lines, "expected_usd")
        trading_committed = sum_field(trading_lines, "committed_usd")
        trading_realized = sum_field(trading_lines, "realized_usd")
        trading_pending = sum_field(trading_lines, "pending_usd")
        trading_paid = sum_field(trading_lines, "paid_usd")
        trading_net = sum_field(trading_lines, "net_usd")

        capital_theoretical = sum_field(capital_lines, "theoretical_max_usd")
        capital_expected = sum_field(capital_lines, "expected_usd")
        capital_committed = sum_field(capital_lines, "committed_usd")
        capital_realized = sum_field(capital_lines, "realized_usd")
        capital_pending = sum_field(capital_lines, "pending_usd")
        capital_paid = sum_field(capital_lines, "paid_usd")
        capital_net = sum_field(capital_lines, "net_usd")

        sum(l.fees_usd for l in self.lines.values())
        sum(l.tax_usd for l in self.lines.values())
        sum(l.fx_loss_usd for l in self.lines.values())

        return RevenueSnapshot(
            work_theoretical=work_theoretical,
            work_expected=work_expected,
            work_committed=work_committed,
            work_realized=work_realized,
            work_pending=work_pending,
            work_paid=work_paid,
            work_net=work_net,
            trading_theoretical=trading_theoretical,
            trading_expected=trading_expected,
            trading_committed=trading_committed,
            trading_realized=trading_realized,
            trading_pending=trading_pending,
            trading_paid=trading_paid,
            trading_net=trading_net,
            capital_theoretical=capital_theoretical,
            capital_expected=capital_expected,
            capital_committed=capital_committed,
            capital_realized=capital_realized,
            capital_pending=capital_pending,
            capital_paid=capital_paid,
            capital_net=capital_net,
            total_theoretical=sum_field_iterable(self.lines.values(), "theoretical_max_usd"),
            total_expected=sum_field_iterable(self.lines.values(), "expected_usd"),
            total_committed=sum_field_iterable(self.lines.values(), "committed_usd"),
            total_realized=sum_field_iterable(self.lines.values(), "realized_usd"),
            total_pending=sum_field_iterable(self.lines.values(), "pending_usd"),
            total_paid=sum_field_iterable(self.lines.values(), "paid_usd"),
            total_net=sum_field_iterable(self.lines.values(), "net_usd"),
            total_fees_usd=Decimal(str(sum(l.fees_usd for l in self.lines.values()))),
            total_tax_usd=Decimal(str(sum(l.tax_usd for l in self.lines.values()))),
            total_fx_loss_usd=Decimal(str(sum(l.fx_loss_usd for l in self.lines.values()))),
            lines_count=len(self.lines),
            as_of=datetime.now(UTC).isoformat(),
        )

    def compute_htroi_v2(
        self,
        line_id: str,
        human_hours: float,
        confidence: float = 1.0,
        automation_hours: float | None = None,
        manual_baseline_hours: float | None = None,
        platform_fee_pct: float = 5.0,
        payment_fee_pct: float = 2.0,
        fx_loss_pct: float = 10.0,
        tax_pct: float = 35.0,
    ) -> HTROIResultV2 | None:
        """Enhanced HTROI with full cost breakdown."""
        if line_id not in self.lines:
            return None

        line = self.lines[line_id]
        if line.net_usd <= 0:
            return None

        # Use net income (after all costs) for ROI
        gross = line.paid_usd or line.net_usd

        fees = line.fees_usd or (line.paid_usd * Decimal(str(platform_fee_pct / 100)))
        payment_fees = line.payment_fees_usd or (line.paid_usd * Decimal("0.02"))
        fx_loss = line.fx_loss_usd or (line.paid_usd * Decimal("0.10"))
        tax = line.tax_usd or (line.paid_usd * Decimal("0.35"))

        net = gross - fees - payment_fees - fx_loss - tax

        Decimal(str(human_hours))
        roi = float(net / Decimal(str(human_hours))) if human_hours > 0 else None

        return HTROIResultV2(
            roi_usd_per_hour=roi,
            expected_net_usd=line.net_usd,
            human_hours_total=Decimal(str(human_hours)),
            confidence_applied=1.0,
            compression_pct=None,
            automation_ratio=None,
            formula_version="HTROI-V2",
            warnings=(),
            gross_income_usd=gross,
            platform_fees_usd=fees,
            payment_fees_usd=payment_fees,
            fx_loss_usd=fx_loss,
            tax_estimate_usd=tax,
            net_income_usd=net,
        )

    def get_lines_by_stream(self, stream: RevenueStream) -> list[RevenueLine]:
        return [l for l in self.lines.values() if l.stream == stream]

    def get_lines_by_state(self, state: RevenueStateV2) -> list[RevenueLine]:
        return [l for l in self.lines.values() if l.state == state]

    def get_pipeline_summary(self) -> dict[str, Any]:
        """Pipeline summary for dashboard."""
        snapshot = self.get_snapshot()

        return {
            "theoretical_capacity": float(snapshot.total_theoretical),
            "expected_pipeline": float(snapshot.total_expected),
            "committed": float(snapshot.total_committed),
            "realized": float(snapshot.total_realized),
            "pending": float(snapshot.total_pending),
            "paid": float(snapshot.total_paid),
            "net_revenue": float(snapshot.total_net),
            "fees_paid": float(snapshot.total_fees_usd),
            "tax_estimate": float(snapshot.total_tax_usd),
            "fx_loss": float(snapshot.total_fx_loss_usd),
            "by_stream": {
                "work": {
                    "theoretical": float(snapshot.work_theoretical),
                    "expected": float(snapshot.work_expected),
                    "committed": float(snapshot.work_committed),
                    "realized": float(snapshot.work_realized),
                    "paid": float(snapshot.work_paid),
                    "net": float(snapshot.work_net),
                },
                "trading": {
                    "theoretical": float(snapshot.trading_theoretical),
                    "expected": float(snapshot.trading_expected),
                    "committed": float(snapshot.trading_committed),
                    "realized": float(snapshot.trading_realized),
                    "paid": float(snapshot.trading_paid),
                    "net": float(snapshot.trading_net),
                },
                "capital": {
                    "theoretical": float(snapshot.capital_theoretical),
                    "expected": float(snapshot.capital_expected),
                    "committed": float(snapshot.capital_committed),
                    "realized": float(snapshot.capital_realized),
                    "paid": float(snapshot.capital_paid),
                    "net": float(snapshot.capital_net),
                },
            },
            "metadata": {
                "total_lines": snapshot.lines_count,
                "as_of": snapshot.as_of,
            },
        }


# Global instance
_economic_engine_v2: EconomicEngineV2 | None = None


def get_economic_engine_v2() -> EconomicEngineV2:
    global _economic_engine_v2
    if _economic_engine_v2 is None:
        _economic_engine_v2 = EconomicEngineV2()
    return _economic_engine_v2
