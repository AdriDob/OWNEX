#!/usr/bin/env python3
"""
OWNEX Revenue Tracker - Payment Management and Multi-Currency Support
Continuous revenue tracking and payment processing with 24/7 monitoring
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

from cores.events.event_bus import get_event_bus

logger = logging.getLogger("ownex.revenue_tracker")


class PaymentStatus(Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    ACCEPTED = "accepted"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RevenueState(Enum):
    """Revenue lifecycle states - strict separation per Economic Rule §39.

    EXPECTED: Pipeline projection, not yet committed
    COMMITTED: Contracted/signed, delivery expected
    EARNED: Work completed, invoice sent, awaiting payment
    PENDING: Payment processing (in transit/verification)
    PAID: Funds received, before fees/taxes
    NET: After fees/taxes/FX - actual cash in hand
    """

    EXPECTED = "expected"
    COMMITTED = "committed"
    EARNED = "earned"
    PENDING = "pending"
    PAID = "paid"
    NET = "net"


class OpportunityStage(Enum):
    """Full pipeline state machine (Income Multiplier Fase A, spec §10).

    Money is only counted at REWARDED/PAID — earlier stages are pipeline,
    never earnings (regla de seguridad económica §39).
    """

    DISCOVERED = "discovered"
    QUALIFIED = "qualified"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REWARDED = "rewarded"
    PAID = "paid"


# WorkBank item status → pipeline stage (Fase A mapping).
# WorkBank states are PRE-submission: 'ready_to_deliver' means prepared,
# not sent; 'delivered' means the human submitted it.
_WORKBANK_STAGE_MAP = {
    "discovered": OpportunityStage.DISCOVERED,
    "needs_access": OpportunityStage.QUALIFIED,
    "ready_to_deliver": OpportunityStage.IN_PROGRESS,
    "delivered": OpportunityStage.SUBMITTED,
}


def stage_from_workbank_status(status: str) -> OpportunityStage:
    """Map a Work Bank item status to its pipeline stage.

    Unknown statuses map to DISCOVERED (least-committal honest default).
    """
    return _WORKBANK_STAGE_MAP.get(str(status).strip().lower(), OpportunityStage.DISCOVERED)


def stage_from_payment_status(status: PaymentStatus | str) -> OpportunityStage:
    """Map a RevenueTracker PaymentStatus to the post-submission stages."""
    value = getattr(status, "value", status)
    stage_map = {
        PaymentStatus.PENDING.value: OpportunityStage.SUBMITTED,
        PaymentStatus.REVIEWING.value: OpportunityStage.SUBMITTED,
        PaymentStatus.ACCEPTED.value: OpportunityStage.ACCEPTED,
        PaymentStatus.PAID.value: OpportunityStage.PAID,
        PaymentStatus.FAILED.value: OpportunityStage.REJECTED,
        PaymentStatus.CANCELLED.value: OpportunityStage.REJECTED,
    }
    return stage_map.get(str(value).strip().lower(), OpportunityStage.DISCOVERED)


# ── Convergencia SSOT (audit P0-2, 2026-08-25) ──────────────────────────────
# ExecState (core/execution_queue.py) es el ciclo de EJECUCIÓN canónico
# (transiciones validadas + dead-letter); OpportunityStage es la proyección
# económica. La ÚNICA tabla de conversión vive aquí, junto a los mappers legacy.

_STAGE_FROM_EXEC_MAP_CACHE: dict[str, "OpportunityStage"] | None = None


def _stage_from_exec_map() -> dict[str, "OpportunityStage"]:
    global _STAGE_FROM_EXEC_MAP_CACHE
    if _STAGE_FROM_EXEC_MAP_CACHE is None:
        from core.execution_queue import ExecState

        _STAGE_FROM_EXEC_MAP_CACHE = {
            ExecState.DISCOVERED.value: OpportunityStage.DISCOVERED,
            ExecState.QUALIFIED.value: OpportunityStage.QUALIFIED,
            # Pre-submission work (prepared/queued/executing/human gate):
            # pipeline view, nunca dinero.
            ExecState.READY.value: OpportunityStage.IN_PROGRESS,
            ExecState.QUEUED.value: OpportunityStage.IN_PROGRESS,
            ExecState.EXECUTING.value: OpportunityStage.IN_PROGRESS,
            ExecState.WAITING_HUMAN.value: OpportunityStage.IN_PROGRESS,
            ExecState.SUBMITTED.value: OpportunityStage.SUBMITTED,
            ExecState.VERIFICATION.value: OpportunityStage.SUBMITTED,
            ExecState.PAID.value: OpportunityStage.PAID,
            ExecState.REJECTED.value: OpportunityStage.REJECTED,
            # Pérdidas honestas documentadas: ExecState distingue bloqueo/fallo/
            # dead-letter; la proyección económica solo conoce REJECTED ($0).
            ExecState.BLOCKED.value: OpportunityStage.REJECTED,
            ExecState.FAILED.value: OpportunityStage.REJECTED,
            ExecState.DEAD_LETTER.value: OpportunityStage.REJECTED,
        }
    return _STAGE_FROM_EXEC_MAP_CACHE


def stage_from_exec_state(state: "str | object") -> OpportunityStage:
    """Map a canonical ExecState to its economic projection stage.

    Unknown states map to DISCOVERED (least-committal honest default).
    """
    value = getattr(state, "value", state)
    return _stage_from_exec_map().get(str(value).strip().lower(), OpportunityStage.DISCOVERED)


def exec_state_for_stage(stage: OpportunityStage | str) -> str:
    """Reverse projection: economic stage → representative canonical ExecState.

    Lossy by design (IN_PROGRESS collapses to EXECUTING; ACCEPTED/REWARDED map
    to VERIFICATION because the cash has not landed yet). Returns the raw
    string value — the caller validates via can_transition() if mutating.
    """
    from core.execution_queue import ExecState

    value = getattr(stage, "value", stage)
    reverse = {
        OpportunityStage.DISCOVERED.value: ExecState.DISCOVERED.value,
        OpportunityStage.QUALIFIED.value: ExecState.QUALIFIED.value,
        OpportunityStage.IN_PROGRESS.value: ExecState.EXECUTING.value,
        OpportunityStage.SUBMITTED.value: ExecState.SUBMITTED.value,
        OpportunityStage.ACCEPTED.value: ExecState.VERIFICATION.value,
        OpportunityStage.REWARDED.value: ExecState.VERIFICATION.value,
        OpportunityStage.REJECTED.value: ExecState.REJECTED.value,
        OpportunityStage.PAID.value: ExecState.PAID.value,
    }
    return reverse.get(str(value).strip().lower(), ExecState.DISCOVERED.value)


class PaymentPlatform(Enum):
    PAYPAL = "paypal"
    PAYONEE = "payoneer"
    WISE = "wise"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"
    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    DATA_ANNOTATION = "data_annotation"


class BarrierType(Enum):
    """Barrier types for revenue opportunities"""

    INTERVIEW = "interview"
    PORTFOLIO = "portfolio"
    EXPERIENCE = "experience"
    DEGREE = "degree"
    CERTIFICATION = "certification"
    LOCATION = "location"
    VISA = "visa"
    LANGUAGE = "language"
    NONE = "none"


@dataclass
class PaymentMethod:
    platform: PaymentPlatform
    account_id: str
    name: str
    currency: str
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RevenueOpportunity:
    """Revenue opportunity from any platform"""

    id: str
    platform: str
    title: str
    description: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    deadline: datetime | None = None
    provider_info: dict[str, Any] = field(default_factory=dict)
    tracking_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    # Zero-barrier fields
    barriers: list[BarrierType] = field(default_factory=list)
    difficulty: str = "beginner"  # beginner, intermediate, advanced, expert
    success_rate: float = 0.0
    time_estimate: str = ""
    tags: list[str] = field(default_factory=list)
    skills_required: list[str] = field(default_factory=list)
    url: str = ""

    # Revenue State Tracking (Economic Rule §39)
    # Expected → Committed → Earned → Pending → Paid → Net
    revenue_state: str = "expected"  # expected, committed, earned, pending, paid, net
    revenue_state_history: list[dict] = field(default_factory=list)

    def is_zero_barrier(self) -> bool:
        """Check if this opportunity has zero barriers (no interview, portfolio, experience required)"""
        return all(barrier == BarrierType.NONE for barrier in self.barriers)

    def get_potential_earnings(self) -> Decimal:
        """Get potential earnings (amount * success_rate)"""
        return self.amount * Decimal(str(self.success_rate))

    def transition_revenue_state(self, new_state: str) -> bool:
        """Transition revenue state with validation.

        Valid transitions:
        expected → committed → earned → pending → paid → net
        Any state can go to: cancelled, failed
        """
        valid_states = {"expected", "committed", "earned", "pending", "paid", "net", "cancelled", "failed"}
        if new_state not in valid_states:
            return False

        # Define valid transitions
        valid_transitions = {
            "expected": {"committed", "cancelled", "failed"},
            "committed": {"earned", "paid", "cancelled", "failed"},
            "earned": {"pending", "cancelled", "failed"},
            "pending": {"paid", "failed"},
            "paid": {"net", "failed"},  # net after fees/taxes
            "net": {"failed"},  # chargeback/refund
            "cancelled": set(),  # terminal
            "failed": set(),  # terminal
        }

        if self.revenue_state in valid_transitions and new_state not in valid_transitions[self.revenue_state]:
            return False

        old_state = self.revenue_state
        self.revenue_state = new_state
        self.updated_at = datetime.now(UTC)
        self.revenue_state_history.append(
            {
                "from": old_state,
                "to": new_state,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        return True

    def get_expected_amount(self) -> Decimal:
        """Get amount in EXPECTED state (pipeline projection)"""
        return self.amount if self.revenue_state == "expected" else Decimal("0")

    def get_committed_amount(self) -> Decimal:
        """Get amount in COMMITTED state (contracted)"""
        return self.amount if self.revenue_state == "committed" else Decimal("0")

    def get_earned_amount(self) -> Decimal:
        """Get amount in EARNED state (work completed)"""
        return self.amount if self.revenue_state == "earned" else Decimal("0")

    def get_pending_amount(self) -> Decimal:
        """Get amount in PENDING state (payment processing)"""
        return self.amount if self.revenue_state == "pending" else Decimal("0")

    def get_paid_amount(self) -> Decimal:
        """Get amount in PAID state (received, before fees)"""
        return self.amount if self.revenue_state == "paid" else Decimal("0")

    def get_net_amount(self) -> Decimal:
        """Get amount in NET state (after fees/taxes)"""
        return self.amount if self.revenue_state == "net" else Decimal("0")


@dataclass
class PaymentTransaction:
    """Payment transaction for a revenue opportunity"""

    transaction_id: str
    opportunity_id: str
    platform: PaymentPlatform
    method_id: str
    amount: Decimal
    currency: str
    exchange_rate: Decimal = Decimal("1.0")
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None
    transaction_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RevenueMetrics:
    """Revenue tracking metrics for platform"""

    platform: str
    currency: str
    total_amount: Decimal
    pending_amount: Decimal
    completed_amount: Decimal
    failed_amount: Decimal
    average_processing_time: float  # hours
    success_rate: float  # 0-1
    last_updated: datetime
    daily_targets: dict[str, Decimal] = field(default_factory=dict)
    # Revenue state tracking (Economic Rule §39)
    expected_amount: Decimal = Decimal("0")
    committed_amount: Decimal = Decimal("0")
    earned_amount: Decimal = Decimal("0")
    paid_amount: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")


@dataclass
class PaymentThreshold:
    """Payment threshold configuration for different platforms"""

    platform: PaymentPlatform
    min_amount: Decimal
    currency: str
    approval_required: bool = False
    auto_approve: bool = True
    processing_fee: Decimal = Decimal("0.0")
    metadata: dict[str, Any] = field(default_factory=dict)


class RevenueTracker:
    """Core revenue tracking and payment management"""

    def __init__(self):
        self.opportunities: dict[str, RevenueOpportunity] = {}
        self.transactions: list[PaymentTransaction] = []
        self.payment_methods: dict[str, PaymentMethod] = {}
        self.metrics: dict[str, RevenueMetrics] = {}
        self.thresholds: dict[PaymentPlatform, PaymentThreshold] = {}
        self.event_bus = get_event_bus()
        self.daily_revenue: dict[str, Decimal] = defaultdict(Decimal)

    def add_payment_method(self, method: PaymentMethod):
        """Add a new payment method"""
        self.payment_methods[method.account_id] = method
        logger.info(f"Added payment method: {method.name} for {method.platform.value}")

    def create_opportunity(self, opportunity: RevenueOpportunity):
        """Create a new revenue opportunity"""
        self.opportunities[opportunity.id] = opportunity
        logger.info(f"Created revenue opportunity: {opportunity.title} - {opportunity.amount} {opportunity.currency}")

        # Emit event for new opportunity
        self.event_bus.publish(
            "opportunity.created",
            **{
                "opportunity_id": opportunity.id,
                "title": opportunity.title,
                "amount": opportunity.amount,
                "currency": opportunity.currency,
                "platform": opportunity.platform,
                "created_at": opportunity.created_at.isoformat(),
            },
        )

    def update_opportunity_status(
        self, opportunity_id: str, new_status: PaymentStatus | str, transaction_data: dict[str, Any] | None = None
    ):
        """Update status of a revenue opportunity"""
        if opportunity_id not in self.opportunities:
            logger.error(f"Opportunity {opportunity_id} not found")
            return False

        # Convert string to PaymentStatus enum if needed
        if isinstance(new_status, str):
            try:
                new_status = PaymentStatus(new_status.lower())
            except ValueError:
                logger.error(f"Invalid status: {new_status}")
                return False

        opportunity = self.opportunities[opportunity_id]
        old_status = opportunity.status
        opportunity.status = new_status
        opportunity.updated_at = datetime.now(UTC)

        if transaction_data:
            opportunity.tracking_data.update(transaction_data)

        logger.info(f"Updated opportunity {opportunity_id} status: {old_status} -> {new_status}")

        # Transition revenue state based on payment status
        if new_status == PaymentStatus.PAID and opportunity.revenue_state != "paid":
            opportunity.transition_revenue_state("paid")
        elif new_status == PaymentStatus.REVIEWING and opportunity.revenue_state == "expected":
            opportunity.transition_revenue_state("committed")
        elif new_status == PaymentStatus.ACCEPTED and opportunity.revenue_state == "committed":
            opportunity.transition_revenue_state("earned")
        elif new_status in (PaymentStatus.FAILED, PaymentStatus.CANCELLED):
            opportunity.transition_revenue_state(getattr(new_status, "value", new_status).lower())
        # Allow committed -> paid transition (direct payment after review)
        elif new_status == PaymentStatus.PAID and opportunity.revenue_state == "committed":
            opportunity.transition_revenue_state("paid")

        # Record metrics change
        self._update_metrics(opportunity)

        # Emit status change event
        self.event_bus.publish(
            "opportunity.status_changed",
            **{
                "opportunity_id": opportunity_id,
                "old_status": getattr(old_status, "value", old_status),
                "new_status": getattr(new_status, "value", new_status),
                "updated_at": opportunity.updated_at.isoformat(),
                "amount": opportunity.amount,
                "currency": opportunity.currency,
            },
        )

        return True

    def process_payment(
        self,
        opportunity_id: str,
        platform: PaymentPlatform,
        method_id: str,
        amount: Decimal,
        currency: str,
        exchange_rate: Decimal = Decimal("1.0"),
    ):
        """Process payment for a revenue opportunity"""
        if opportunity_id not in self.opportunities:
            logger.error(f"Opportunity {opportunity_id} not found for payment")
            return None

        opportunity = self.opportunities[opportunity_id]

        # Validate payment
        if not self._validate_payment(opportunity, platform, method_id, amount, currency):
            logger.error(f"Payment validation failed for opportunity {opportunity_id}")
            return None

        # Create transaction
        transaction_id = f"tx_{datetime.now().timestamp()}_{platform.value}"
        transaction = PaymentTransaction(
            transaction_id=transaction_id,
            opportunity_id=opportunity_id,
            platform=platform,
            method_id=method_id,
            amount=amount,
            currency=currency,
            exchange_rate=exchange_rate,
            status=PaymentStatus.PENDING,
        )

        self.transactions.append(transaction)

        # Update opportunity status to review
        self.update_opportunity_status(
            opportunity_id,
            PaymentStatus.REVIEWING,
            {
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": currency,
                "platform": platform.value,
            },
        )

        logger.info(f"Created payment transaction {transaction_id} for opportunity {opportunity_id}")

        # Emit payment created event
        self.event_bus.publish(
            "payment.created",
            **{
                "transaction_id": transaction_id,
                "opportunity_id": opportunity_id,
                "amount": amount,
                "currency": currency,
                "platform": platform.value,
                "created_at": transaction.created_at.isoformat(),
            },
        )

        return transaction

    def _validate_payment(
        self, opportunity: RevenueOpportunity, platform: PaymentPlatform, method_id: str, amount: Decimal, currency: str
    ):
        """Validate payment processing requirements"""
        # Check if payment method exists
        if method_id not in self.payment_methods:
            return False

        method = self.payment_methods[method_id]
        if method.status != "active":
            return False

        # Check if opportunity is in correct status
        if opportunity.status != PaymentStatus.REVIEWING:
            return False

        # Check currency compatibility
        if method.currency != currency and method.currency != "USD":
            return False

        # Check amount thresholds
        if platform not in self.thresholds:
            return True

        threshold = self.thresholds[platform]
        return not amount < threshold.min_amount

    def _update_metrics(self, opportunity: RevenueOpportunity):
        """Recompute platform metrics as a PROJECTION of current state.

        Fix de integridad económica (E2E 2026-08-25): el algoritmo anterior
        acumulaba deltas por cada cambio de status, así que una oportunidad
        PENDING→REVIEWING→PAID dejaba "dinero fantasma" en pending_amount
        (la misma plata contada como pendiente Y cobrada). Ahora las métricas
        siempre reflejan el estado ACTUAL de las oportunidades.

        Regla §39: el dinero solo se cuenta en PAID. ACCEPTED es pipeline
        (coincide con stage_from_payment_status: ACCEPTED → Stage.ACCEPTED,
        no REWARDED/PAID). CANCELLED es pérdida documentada, no cash.
        """
        platform_key = opportunity.platform.lower()
        currency = opportunity.currency

        pending = Decimal("0")
        completed = Decimal("0")
        failed = Decimal("0")
        total_opps = 0
        paid_opps = 0
        for opp in self.opportunities.values():
            if opp.platform.lower() != platform_key:
                continue
            total_opps += 1
            if opp.status == PaymentStatus.PENDING or opp.status == PaymentStatus.REVIEWING:
                pending += opp.amount
            elif opp.status == PaymentStatus.PAID:
                completed += opp.amount
                paid_opps += 1
            elif opp.status == PaymentStatus.FAILED:
                failed += opp.amount

        metrics = self.metrics.get(platform_key)
        if metrics is None:
            metrics = RevenueMetrics(
                platform=platform_key,
                currency=currency,
                total_amount=Decimal("0"),
                pending_amount=Decimal("0"),
                completed_amount=Decimal("0"),
                failed_amount=Decimal("0"),
                average_processing_time=0.0,
                success_rate=0.0,
                last_updated=datetime.now(UTC),
            )
            self.metrics[platform_key] = metrics

        metrics.pending_amount = pending
        metrics.completed_amount = completed
        metrics.failed_amount = failed
        metrics.total_amount = pending + completed + failed
        metrics.success_rate = (paid_opps / total_opps) if total_opps else 0.0
        metrics.last_updated = datetime.now(UTC)

        # Add revenue state tracking
        self._update_revenue_state_metrics(platform_key, currency)

    def get_platform_metrics(self, platform: str) -> RevenueMetrics | None:
        """Get revenue metrics for a specific platform"""
        return self.metrics.get(platform.lower())

    def _update_revenue_state_metrics(self, platform_key: str, currency: str):
        """Update revenue state metrics for a platform."""
        # Get or create metrics
        if platform_key not in self.metrics:
            self.metrics[platform_key] = RevenueMetrics(
                platform=platform_key,
                currency=currency,
                total_amount=Decimal("0"),
                pending_amount=Decimal("0"),
                completed_amount=Decimal("0"),
                failed_amount=Decimal("0"),
                average_processing_time=0.0,
                success_rate=0.0,
                last_updated=datetime.now(UTC),
            )
        metrics = self.metrics[platform_key]

        # Reset state counters
        expected_amount = Decimal("0")
        committed_amount = Decimal("0")
        earned_amount = Decimal("0")
        pending_amount = Decimal("0")
        paid_amount = Decimal("0")
        net_amount = Decimal("0")

        for opp in self.opportunities.values():
            if opp.platform.lower() != platform_key:
                continue
            if opp.revenue_state == "expected":
                expected_amount += opp.amount
            elif opp.revenue_state == "committed":
                committed_amount += opp.amount
            elif opp.revenue_state == "earned":
                earned_amount += opp.amount
            elif opp.revenue_state == "pending":
                pending_amount += opp.amount
            elif opp.revenue_state == "paid":
                paid_amount += opp.amount
            elif opp.revenue_state == "net":
                net_amount += opp.amount

        # Update legacy fields for backward compatibility
        metrics.pending_amount = expected_amount + committed_amount + earned_amount
        metrics.completed_amount = paid_amount + net_amount
        metrics.failed_amount = sum(
            opp.amount
            for opp in self.opportunities.values()
            if opp.platform.lower() == platform_key and opp.revenue_state in {"cancelled", "failed"}
        ) or Decimal("0")
        metrics.total_amount = (
            expected_amount + committed_amount + earned_amount + pending_amount + paid_amount + net_amount
        )

        # Store new revenue state metrics
        metrics.expected_amount = getattr(metrics, "expected_amount", Decimal("0"))
        metrics.committed_amount = getattr(metrics, "committed_amount", Decimal("0"))
        metrics.earned_amount = getattr(metrics, "earned_amount", Decimal("0"))
        metrics.pending_amount = pending_amount
        metrics.paid_amount = getattr(metrics, "paid_amount", Decimal("0"))
        metrics.net_amount = getattr(metrics, "net_amount", Decimal("0"))

        metrics.last_updated = datetime.now(UTC)

    def get_revenue_state_breakdown(self, platform: str | None = None) -> dict[str, Any]:
        """Get revenue breakdown by state for a platform or all platforms."""
        result: dict[str, Any] = {
            "expected": Decimal("0"),
            "committed": Decimal("0"),
            "earned": Decimal("0"),
            "pending": Decimal("0"),
            "paid": Decimal("0"),
            "net": Decimal("0"),
            "cancelled": Decimal("0"),
            "failed": Decimal("0"),
        }

        platforms = (
            [platform]
            if platform
            else [p.lower() for p in set(opp.platform.lower() for opp in self.opportunities.values())]
        )

        for platform_key in platforms:
            for opp in self.opportunities.values():
                if opp.platform.lower() != platform_key:
                    continue
                state = opp.revenue_state
                if state in result:
                    result[state] += opp.amount

        return result

    def get_revenue_projection(self, platform: str | None = None) -> dict[str, Decimal]:
        """Get revenue projection by state (expected + committed = pipeline)."""
        breakdown = self.get_revenue_state_breakdown(platform)
        pipeline = breakdown["expected"] + breakdown["committed"]
        earned_not_paid = breakdown["earned"] + breakdown["pending"]
        realized = breakdown["paid"] + breakdown["net"]

        return {
            "pipeline": pipeline,  # expected + committed
            "earned_not_paid": earned_not_paid,  # earned + pending
            "realized": realized,  # paid + net
            "total_potential": pipeline + earned_not_paid + realized,
            "breakdown": breakdown,
        }

    def get_daily_summary(self, date: datetime | None = None) -> dict[str, Decimal]:
        """Get daily revenue summary"""
        if date is None:
            date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        date.strftime("%Y-%m-%d")
        return {platform: self.daily_revenue[platform] for platform in self.daily_revenue}

    def add_daily_revenue(self, platform: str, amount: Decimal, currency: str):
        """Add daily revenue data"""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        self.daily_revenue[today] += amount

        # Emit daily metrics event
        self.event_bus.publish(
            "daily.revenue",
            **{
                "date": today,
                "platform": platform,
                "amount": amount,
                "currency": currency,
                "total_daily": self.daily_revenue[today],
            },
        )

    def get_zero_barrier_opportunities(
        self,
        platform: str | None = None,
        min_amount: Decimal = Decimal("0"),
        difficulty: str | None = None,
    ) -> list[RevenueOpportunity]:
        """Get zero-barrier opportunities (no interview, portfolio, experience required)"""
        opportunities = list(self.opportunities.values())

        # Filter by zero-barrier
        opportunities = [op for op in opportunities if op.is_zero_barrier()]

        # Filter by platform
        if platform:
            opportunities = [op for op in opportunities if op.platform == platform]

        # Filter by minimum amount
        if min_amount > Decimal("0"):
            opportunities = [op for op in opportunities if op.amount >= min_amount]

        # Filter by difficulty
        if difficulty:
            opportunities = [op for op in opportunities if op.difficulty == difficulty]

        # Sort by potential earnings (amount * success_rate)
        opportunities.sort(key=lambda op: op.get_potential_earnings(), reverse=True)

        return opportunities

    def get_opportunities_by_platform(self, platform: str) -> list[RevenueOpportunity]:
        """Get all opportunities for a specific platform"""
        return [op for op in self.opportunities.values() if op.platform == platform]

    def get_total_potential_earnings(self) -> Decimal:
        """Get total potential earnings from all opportunities"""
        total = Decimal("0")
        for op in self.opportunities.values():
            total += op.get_potential_earnings()
        return total

    # ========== Missing methods for tests ==========

    def health(self) -> dict[str, Any]:
        """Health check for RevenueTracker"""
        return {
            "status": "healthy",
            "opportunities_count": len(self.opportunities),
            "transactions_count": len(self.transactions),
            "payment_methods": len(self.payment_methods),
            "platforms": list(self.metrics.keys()),
        }

    def available_methods(self) -> list[str]:
        """Return list of available payment method IDs"""
        return list(self.payment_methods.keys())

    def discover(self, scored_opportunities: list, top_n: int = 5) -> list:
        """Discover top revenue opportunities from scored list"""
        sorted_opps = sorted(scored_opportunities, key=lambda x: x.get_potential_earnings(), reverse=True)
        return sorted_opps[:top_n]

    def process_payment_alias(
        self,
        opportunity_id: str,
        platform: "PaymentPlatform",
        method_id: str,
        amount: Decimal,
        currency: str,
        exchange_rate: Decimal = Decimal("1.0"),
    ) -> "PaymentTransaction | None":
        """Process payment for a revenue opportunity - alias for process_payment with different signature"""
        return self.process_payment(
            opportunity_id=opportunity_id,
            platform=platform,
            method_id=method_id,
            amount=amount,
            currency=currency,
            exchange_rate=exchange_rate,
        )


class RevenueAnalytics:
    """Revenue analytics and visualization"""

    def __init__(self, tracker: RevenueTracker):
        self.tracker = tracker

    def get_revenue_by_platform(self) -> dict[str, dict[str, Any]]:
        """Get revenue breakdown by platform"""
        result = {}
        for platform_key, metrics in self.tracker.metrics.items():
            result[platform_key] = {
                "platform": platform_key,
                "currency": metrics.currency,
                "total_amount": float(metrics.total_amount),
                "pending_amount": float(metrics.pending_amount),
                "completed_amount": float(metrics.completed_amount),
                "failed_amount": float(metrics.failed_amount),
                "success_rate": metrics.success_rate,
                "average_processing_time": metrics.average_processing_time,
            }
        return result

    def get_currency_conversion_summary(self) -> dict[str, Decimal]:
        """Get summary of all currencies being tracked"""
        conversion_summary = defaultdict(Decimal)
        for metrics in self.tracker.metrics.values():
            conversion_summary[metrics.currency] += metrics.total_amount
        return conversion_summary

    def get_revenue_growth_trend(self, days: int = 30) -> list[dict[str, Any]]:
        """Get revenue growth trend for last N days"""
        # This would typically use historical data, for now returns current status
        trend = []
        for metrics in self.tracker.metrics.values():
            trend.append(
                {
                    "platform": metrics.platform,
                    "currency": metrics.currency,
                    "current_amount": float(metrics.total_amount),
                    "growth_rate": 0.0,  # Would calculate based on historical data
                }
            )
        return trend

    def get_payment_processing_efficiency(self) -> dict[str, Any]:
        """Get payment processing efficiency metrics"""
        if not self.tracker.transactions:
            return {"total_transactions": 0, "efficiency_score": 0.0}

        total_transactions = len(self.tracker.transactions)
        completed_transactions = len([t for t in self.tracker.transactions if t.status == PaymentStatus.PAID])
        efficiency_score = completed_transactions / total_transactions if total_transactions > 0 else 0.0

        return {
            "total_transactions": total_transactions,
            "completed_transactions": completed_transactions,
            "failed_transactions": len([t for t in self.tracker.transactions if t.status == PaymentStatus.FAILED]),
            "processing_percentage": efficiency_score * 100,
        }


async def main_revenue_tracker():
    """Main function for standalone execution"""
    logger.info("Starting OWNEX Revenue Tracker")

    # Initialize EventBus
    event_bus = get_event_bus()

    # Create tracker
    tracker = RevenueTracker()

    # Setup payment methods
    paypal_method = PaymentMethod(
        platform=PaymentPlatform.PAYPAL, account_id="paypal_123", name="Primary PayPal Account", currency="USD"
    )
    tracker.add_payment_method(paypal_method)

    wise_method = PaymentMethod(
        platform=PaymentPlatform.WISE, account_id="wise_456", name="Wise International", currency="ARS"
    )
    tracker.add_payment_method(wise_method)

    # Setup payment thresholds
    bug_bounty_threshold = PaymentThreshold(
        platform=PaymentPlatform.BUG_BOUNTY, min_amount=Decimal("50"), currency="USD", auto_approve=True
    )
    tracker.thresholds[PaymentPlatform.BUG_BOUNTY] = bug_bounty_threshold

    dev_bounty_threshold = PaymentThreshold(
        platform=PaymentPlatform.DEV_BOUNTY, min_amount=Decimal("100"), currency="USD", auto_approve=True
    )
    tracker.thresholds[PaymentPlatform.DEV_BOUNTY] = dev_bounty_threshold

    # Create some sample opportunities
    bug_bounty_opp = RevenueOpportunity(
        id="opp_1",
        platform="bug_bounty",
        title="SQL Injection Discovery",
        description="Critical SQL injection vulnerability found",
        amount=Decimal("2500.00"),
        currency="USD",
        status=PaymentStatus.ACCEPTED,
        deadline=datetime.now(UTC) + timedelta(days=7),
        provider_info={"platform": "hackerone", "severity": "critical"},
    )
    tracker.create_opportunity(bug_bounty_opp)

    dev_bounty_opp = RevenueOpportunity(
        id="opp_2",
        platform="dev_bounty",
        title="OAuth2 Implementation",
        description="Implement OAuth2 authentication for API",
        amount=Decimal("800.00"),
        currency="USD",
        status=PaymentStatus.PENDING,
        deadline=datetime.now(UTC) + timedelta(days=14),
        provider_info={"platform": "bountysource", "type": "feature"},
    )
    tracker.create_opportunity(dev_bounty_opp)

    data_annotation_opp = RevenueOpportunity(
        id="opp_3",
        platform="data_annotation",
        title="Image Classification Dataset",
        description="Classify 5k images into 3 categories",
        amount=Decimal("300.00"),
        currency="USD",
        status=PaymentStatus.ACCEPTED,
        deadline=datetime.now(UTC) + timedelta(days=30),
        provider_info={"platform": "scale_ai", "type": "computer_vision"},
    )
    tracker.create_opportunity(data_annotation_opp)

    # Process some payments
    tracker.process_payment("opp_1", PaymentPlatform.PAYPAL, "paypal_123", Decimal("2500.00"), "USD")

    # Update opportunity statuses
    tracker.update_opportunity_status(
        "opp_1",
        PaymentStatus.PAID,
        {"transaction_id": "tx_123", "processed_at": datetime.now(UTC).isoformat(), "platform_fee": 50.00},
    )

    tracker.update_opportunity_status(
        "opp_2", PaymentStatus.ACCEPTED, {"review_completed_at": datetime.now(UTC).isoformat(), "approver": "john_doe"}
    )

    # Add some daily revenue data
    tracker.add_daily_revenue("bug_bounty", Decimal("5250.00"), "USD")  # Total paid to user
    tracker.add_daily_revenue("dev_bounty", Decimal("800.00"), "USD")  # Pending review
    tracker.add_daily_revenue("data_annotation", Decimal("300.00"), "USD")  # Pending review

    # Setup analytics
    analytics = RevenueAnalytics(tracker)

    # Get analytics
    platform_revenue = analytics.get_revenue_by_platform()
    currency_summary = analytics.get_currency_conversion_summary()
    processing_efficiency = analytics.get_payment_processing_efficiency()

    # Log summary
    logger.info("=== Revenue Tracker Summary ===")
    logger.info(f"Total opportunities: {len(tracker.opportunities)}")
    logger.info(f"Total transactions: {len(tracker.transactions)}")
    logger.info(f"Platform revenue: {platform_revenue}")
    logger.info(f"Currency breakdown: {currency_summary}")
    logger.info(f"Processing efficiency: {processing_efficiency}")

    # Publish revenue summary event
    revenue_summary = {
        "total_opportunities": len(tracker.opportunities),
        "total_transactions": len(tracker.transactions),
        "platform_revenue": platform_revenue,
        "currency_summary": currency_summary,
        "processing_efficiency": processing_efficiency,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    event_bus.publish("revenue.summary", **revenue_summary)

    # Run continuously for 60 seconds (for demo)
    await asyncio.sleep(60)
    logger.info("Revenue tracker demo completed")

    # Stop monitoring
    for task in asyncio.all_tasks():
        task.cancel()


if __name__ == "__main__":
    # Run the revenue tracker
    asyncio.run(main_revenue_tracker())


# Module-level singleton getter
_revenue_tracker_instance: RevenueTracker | None = None


def get_revenue_tracker() -> RevenueTracker:
    """Get or create the global revenue tracker instance."""
    global _revenue_tracker_instance
    if _revenue_tracker_instance is None:
        _revenue_tracker_instance = RevenueTracker()
    return _revenue_tracker_instance
