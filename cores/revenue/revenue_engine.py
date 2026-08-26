#!/usr/bin/env python3
"""
Revenue Engine for OWNEX - EventBus-powered opportunity scoring and payment tracking
EventBus workflow: DISCOVERY -> EVALUATION -> SELECTION -> PREPARATION -> EXECUTION -> DELIVERY -> VALIDATION -> PAYMENT -> LEARNING
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from cores.events.event_bus import get_event_bus


class PlatformType(Enum):
    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    DATA_ANNOTATION = "data_annotation"


class OpportunityStatus(Enum):
    DISCOVERED = "discovered"
    EVALUATED = "evaluated"
    SELECTED = "selected"
    PREPARING = "preparing"
    EXECUTING = "executing"
    DELIVERED = "delivered"
    VALIDATED = "validated"
    PAID = "paid"
    REJECTED = "rejected"


class PaymentStatus(Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    ACCEPTED = "accepted"
    PAID = "paid"
    FAILED = "failed"


class RevenueOpportunity:
    """Represents a revenue opportunity from any platform - EventBus compatible."""

    def __init__(
        self,
        opportunity_id: str,
        platform: PlatformType,
        title: str,
        description: str,
        reward: Decimal,
        currency: str = "USD",
        estimated_time_hours: int = 0,
    ):
        self.id = opportunity_id
        self.platform = platform
        self.title = title
        self.description = description
        self.base_reward = reward
        self.currency = currency
        self.estimated_time_hours = estimated_time_hours
        self.status = OpportunityStatus.DISCOVERED
        self.metadata = {}

        self.created_at = datetime.now(UTC)
        self.updated_at = self.created_at
        self.selected_at = None
        self.completed_at: datetime | None = None

        # Calculated fields
        self.expected_value = self._calculate_expected_value()
        self.confidence_score = 0.5  # 0-1 scale

    def _calculate_expected_value(self) -> Decimal:
        """Calculate expected value: (Reward × Probability) / Time"""
        if self.estimated_time_hours <= 0:
            return self.base_reward

        probability = Decimal(str(self.confidence_score))
        return (self.base_reward * probability) / Decimal(str(self.estimated_time_hours))

    def update_confidence(self, confidence: float):
        """Update confidence score and recalculate EV"""
        self.confidence_score = max(0.0, min(1.0, confidence))
        self.expected_value = self._calculate_expected_value()
        self.updated_at = datetime.now(UTC)

    def select(self):
        """Mark opportunity as selected for execution."""
        if self.status == OpportunityStatus.DISCOVERED:
            self.status = OpportunityStatus.SELECTED
            self.selected_at = datetime.now(UTC)
            self.updated_at = self.selected_at
            return True
        return False


class RevenuePayment:
    """Represents a payment received from a platform."""

    def __init__(
        self,
        payment_id: str,
        opportunity_id: str,
        platform: PlatformType,
        amount: Decimal,
        currency: str = "USD",
        payment_method: str = "bank_transfer",
    ):
        self.id = payment_id
        self.opportunity_id = opportunity_id
        self.platform = platform
        self.amount = amount
        self.currency = currency
        self.payment_method = payment_method
        self.status = PaymentStatus.PENDING

        self.requested_at = datetime.now(UTC)
        self.approved_at = None
        self.paid_at = None
        self.failed_at = None

        # Platform-specific metadata
        self.metadata = {}

    def approve(self):
        """Mark payment as approved."""
        if self.status == PaymentStatus.PENDING:
            self.status = PaymentStatus.ACCEPTED
            self.approved_at = datetime.now(UTC)
            return True
        return False

    def mark_paid(self):
        """Mark payment as completed."""
        if self.status == PaymentStatus.ACCEPTED:
            self.status = PaymentStatus.PAID
            self.paid_at = datetime.now(UTC)
            return True
        return False

    def mark_failed(self, reason: str):
        """Mark payment as failed."""
        if self.status in [PaymentStatus.PENDING, PaymentStatus.ACCEPTED]:
            self.status = PaymentStatus.FAILED
            self.failed_at = datetime.now(UTC)
            self.metadata["failure_reason"] = reason
            return True
        return False


class RevenueEngine:
    """Main revenue engine using EventBus for opportunity tracking and payments."""

    def __init__(self):
        self.event_bus = get_event_bus()
        self.opportunities: dict[str, RevenueOpportunity] = {}
        self.payments: dict[str, RevenuePayment] = {}

        # Register event handlers for the 9-phase OWNEX workflow
        self._register_event_handlers()

    def _register_event_handlers(self):
        """Register EventBus event handlers for all 9 workflow phases."""
        # DISCOVERY: Listen for platform discovery events
        self.event_bus.subscribe("platform.discovered", self._handle_platform_discovery)

        # EVALUATION: Listen for opportunity evaluation events
        self.event_bus.subscribe("opportunity.evaluated", self._handle_opportunity_evaluation)

        # SELECTION: Listen for selection events
        self.event_bus.subscribe("opportunity.selected", self._handle_opportunity_selection)

        # PREPARATION: Listen for preparation events
        self.event_bus.subscribe("opportunity.preparing", self._handle_opportunity_preparation)

        # EXECUTION: Listen for execution events
        self.event_bus.subscribe("opportunity.executing", self._handle_opportunity_execution)

        # DELIVERY: Listen for delivery events
        self.event_bus.subscribe("opportunity.delivered", self._handle_opportunity_delivery)

        # VALIDATION: Listen for validation events
        self.event_bus.subscribe("opportunity.validated", self._handle_opportunity_validation)

        # PAYMENT: Listen for payment events
        self.event_bus.subscribe("payment.created", self._handle_payment_creation)
        self.event_bus.subscribe("payment.approved", self._handle_payment_approval)
        self.event_bus.subscribe("payment.paid", self._handle_payment_completion)

        # LEARNING: Listen for learning events
        self.event_bus.subscribe("opportunity.completed", self._handle_opportunity_learning)

    def _handle_platform_discovery(self, event_type: str, **kwargs):
        """Handle platform discovery events - Phase 1: DISCOVERY"""
        platform = kwargs.get("platform")
        data = kwargs.get("data", {})

        print(f"[RevenueEngine] 📡 DISCOVERY: Platform {platform} connecting")
        print(f"   → Found {len(data)} opportunities")

        # Create opportunities from discovered data
        if platform == PlatformType.BUG_BOUNTY:
            self._create_bug_bounty_opportunities(data)
        elif platform == PlatformType.DEV_BOUNTY:
            self._create_dev_bounty_opportunities(data)
        elif platform == PlatformType.DATA_ANNOTATION:
            self._create_data_annotation_opportunities(data)

    def _handle_opportunity_evaluation(self, event_type: str, **kwargs):
        """Handle opportunity evaluation events - Phase 2: EVALUATION"""
        opportunity_id = kwargs.get("opportunity_id")
        confidence = kwargs.get("confidence", 0.5)

        if opportunity_id in self.opportunities:
            opportunity = self.opportunities[opportunity_id]
            opportunity.update_confidence(confidence)

            ev = opportunity.expected_value
            print(f"[RevenueEngine] 📊 EVALUATION: Opportunity {opportunity_id}")
            print(f"   → Confidence: {confidence}, Expected Value: ${ev}")

    def _handle_opportunity_selection(self, event_type: str, **kwargs):
        """Handle opportunity selection events - Phase 3: SELECTION"""
        opportunity_id = kwargs.get("opportunity_id")

        if opportunity_id in self.opportunities:
            opportunity = self.opportunities[opportunity_id]
            if opportunity.select():
                print(f"[RevenueEngine] ✅ SELECTION: Selected opportunity {opportunity_id}")

                # Create payment record
                payment_id = f"pay_{uuid.uuid4().hex[:8]}"
                payment = RevenuePayment(
                    payment_id=payment_id,
                    opportunity_id=opportunity_id,
                    platform=opportunity.platform,
                    amount=opportunity.base_reward,
                    currency=opportunity.currency,
                    payment_method="auto_selected",
                )
                self.payments[payment_id] = payment

                # Emit payment created event
                self.event_bus.publish(
                    "payment.created",
                    {
                        "payment_id": payment_id,
                        "opportunity_id": opportunity_id,
                        "amount": opportunity.base_reward,
                        "currency": opportunity.currency,
                        "platform": opportunity.platform.value,
                    },
                )

    def _handle_opportunity_preparation(self, event_type: str, **kwargs):
        """Handle opportunity preparation events - Phase 4: PREPARATION"""
        opportunity_id = kwargs.get("opportunity_id")
        preparation_data = kwargs.get("data", {})

        if opportunity_id in self.opportunities:
            opportunity = self.opportunities[opportunity_id]
            opportunity.status = OpportunityStatus.PREPARING
            opportunity.metadata.update(preparation_data)

            print(f"[RevenueEngine] 🛠️ PREPARATION: Opportunity {opportunity_id}")
            print(f"   → Environment ready: {preparation_data.get('environment', 'standard')}")

    def _handle_opportunity_execution(self, event_type: str, **kwargs):
        """Handle opportunity execution events - Phase 5: EXECUTION"""
        opportunity_id = kwargs.get("opportunity_id")
        agent = kwargs.get("agent", "auto")

        if opportunity_id in self.opportunities:
            opportunity = self.opportunities[opportunity_id]
            opportunity.status = OpportunityStatus.EXECUTING
            opportunity.metadata["executed_by"] = agent

            print(f"[RevenueEngine] ⚡ EXECUTION: Opportunity {opportunity_id}")
            print(f"   → Executed by: {agent}")

    def _handle_opportunity_delivery(self, event_type: str, **kwargs):
        """Handle opportunity delivery events - Phase 6: DELIVERY"""
        opportunity_id = kwargs.get("opportunity_id")
        delivery_type = kwargs.get("delivery_type", "auto")

        if opportunity_id in self.opportunities:
            opportunity = self.opportunities[opportunity_id]
            opportunity.status = OpportunityStatus.DELIVERED
            opportunity.metadata["delivery_type"] = delivery_type

            print(f"[RevenueEngine] 📦 DELIVERY: Opportunity {opportunity_id}")
            print(f"   → Delivered via: {delivery_type}")

    def _handle_opportunity_validation(self, event_type: str, **kwargs):
        """Handle opportunity validation events - Phase 7: VALIDATION"""
        opportunity_id = kwargs.get("opportunity_id")
        validation_result = kwargs.get("valid", False)

        if opportunity_id in self.opportunities:
            opportunity = self.opportunities[opportunity_id]
            if validation_result:
                opportunity.status = OpportunityStatus.VALIDATED
                print(f"[RevenueEngine] ✅ VALIDATION: Opportunity {opportunity_id} ✓")
            else:
                opportunity.status = OpportunityStatus.REJECTED
                print(f"[RevenueEngine] ❌ VALIDATION: Opportunity {opportunity_id} ✗")

    def _handle_payment_creation(self, event_type: str, **kwargs):
        """Handle payment creation events - Phase 8: PAYMENT"""
        payment_id = kwargs.get("payment_id")
        kwargs.get("opportunity_id")

        if payment_id in self.payments:
            payment = self.payments[payment_id]
            payment.status = PaymentStatus.PENDING
            print(f"[RevenueEngine] 💰 PAYMENT: Created payment {payment_id}")
            print(f"   → Amount: ${payment.amount} {payment.currency}")

    def _handle_payment_approval(self, event_type: str, **kwargs):
        """Handle payment approval events - Phase 8: PAYMENT"""
        payment_id = kwargs.get("payment_id")

        if payment_id in self.payments:
            payment = self.payments[payment_id]
            if payment.approve():
                print(f"[RevenueEngine] 👍 PAYMENT: Approved payment {payment_id}")

    def _handle_payment_completion(self, event_type: str, **kwargs):
        """Handle payment completion events - Phase 8: PAYMENT"""
        payment_id = kwargs.get("payment_id")

        if payment_id in self.payments:
            payment = self.payments[payment_id]
            if payment.mark_paid():
                print(f"[RevenueEngine] ✅ PAYMENT: Paid payment {payment_id}")
                # Phase 9: LEARNING
                self.event_bus.publish(
                    "opportunity.completed",
                    {"opportunity_id": payment.opportunity_id, "status": "success", "payment_id": payment_id},
                )

    def _handle_opportunity_learning(self, event_type: str, **kwargs):
        """Handle opportunity completion events - Phase 9: LEARNING"""
        opportunity_id = kwargs.get("opportunity_id")
        status = kwargs.get("status")

        if opportunity_id in self.opportunities:
            opportunity = self.opportunities[opportunity_id]
            opportunity.status = OpportunityStatus.PAID if status == "success" else OpportunityStatus.REJECTED
            opportunity.completed_at = datetime.now(UTC)

            print(f"[RevenueEngine] 📚 LEARNING: Opportunity {opportunity_id} completed")
            print(f"   → Status: {status}, Learned at: {datetime.now(UTC).strftime('%Y-%m-%d')}")

    def _create_bug_bounty_opportunities(self, data: list[dict[str, Any]]):
        """Create Bug Bounty opportunities from discovered data."""
        for item in data:
            opportunity_id = f"opp_bug_{uuid.uuid4().hex[:8]}"

            opportunity = RevenueOpportunity(
                opportunity_id=opportunity_id,
                platform=PlatformType.BUG_BOUNTY,
                title=item.get("title", "Bug Bounty Opportunity"),
                description=item.get("description", ""),
                reward=Decimal(str(item.get("reward", 0))),
                currency=item.get("currency", "USD"),
                estimated_time_hours=item.get("estimated_time_hours", 4),
            )

            confidence = item.get("probability", 0.7)
            opportunity.update_confidence(confidence)
            self.opportunities[opportunity_id] = opportunity

            print(f"[RevenueEngine] 🐛 CREATED: Bug Bounty opportunity {opportunity_id} - ${opportunity.base_reward}")

    def _create_dev_bounty_opportunities(self, data: list[dict[str, Any]]):
        """Create Dev Bounty opportunities from discovered data."""
        for item in data:
            opportunity_id = f"opp_dev_{uuid.uuid4().hex[:8]}"

            opportunity = RevenueOpportunity(
                opportunity_id=opportunity_id,
                platform=PlatformType.DEV_BOUNTY,
                title=item.get("title", "Dev Bounty Opportunity"),
                description=item.get("description", ""),
                reward=Decimal(str(item.get("reward", 0))),
                currency=item.get("currency", "USD"),
                estimated_time_hours=item.get("estimated_time_hours", 8),
            )

            confidence = item.get("probability", 0.5)
            opportunity.update_confidence(confidence)
            self.opportunities[opportunity_id] = opportunity

            print(f"[RevenueEngine] 💻 CREATED: Dev Bounty opportunity {opportunity_id} - ${opportunity.base_reward}")

    def _create_data_annotation_opportunities(self, data: list[dict[str, Any]]):
        """Create Data Annotation opportunities from discovered data."""
        for item in data:
            opportunity_id = f"opp_data_{uuid.uuid4().hex[:8]}"

            opportunity = RevenueOpportunity(
                opportunity_id=opportunity_id,
                platform=PlatformType.DATA_ANNOTATION,
                title=item.get("title", "Data Annotation Task"),
                description=item.get("description", ""),
                reward=Decimal(str(item.get("reward", 0))),
                currency=item.get("currency", "USD"),
                estimated_time_hours=item.get("estimated_time_hours", 2),
            )

            confidence = item.get("probability", 0.6)
            opportunity.update_confidence(confidence)
            self.opportunities[opportunity_id] = opportunity

            print(
                f"[RevenueEngine] 📊 CREATED: Data Annotation opportunity {opportunity_id} - ${opportunity.base_reward}"
            )


# Global revenue engine instance
_revenue_engine = RevenueEngine()


def get_revenue_engine() -> RevenueEngine:
    """Get the global revenue engine instance."""
    return _revenue_engine


def publish_platform_discovery(platform: PlatformType, data: list[dict[str, Any]]):
    """Publish platform discovery event - Phase 1: DISCOVERY."""
    _revenue_engine.event_bus.publish("platform.discovered", {"platform": platform.value, "data": data})


def publish_opportunity_evaluation(opportunity_id: str, confidence: float):
    """Publish opportunity evaluation event - Phase 2: EVALUATION."""
    _revenue_engine.event_bus.publish(
        "opportunity.evaluated", {"opportunity_id": opportunity_id, "confidence": confidence}
    )


def publish_opportunity_selection(opportunity_id: str):
    """Publish opportunity selection event - Phase 3: SELECTION."""
    _revenue_engine.event_bus.publish("opportunity.selected", {"opportunity_id": opportunity_id})


def publish_opportunity_preparation(opportunity_id: str, data: dict[str, Any]):
    """Publish opportunity preparation event - Phase 4: PREPARATION."""
    _revenue_engine.event_bus.publish("opportunity.preparing", {"opportunity_id": opportunity_id, "data": data})


def publish_opportunity_execution(opportunity_id: str, agent: str = "auto"):
    """Publish opportunity execution event - Phase 5: EXECUTION."""
    _revenue_engine.event_bus.publish("opportunity.executing", {"opportunity_id": opportunity_id, "agent": agent})


def publish_opportunity_delivery(opportunity_id: str, delivery_type: str = "auto"):
    """Publish opportunity delivery event - Phase 6: DELIVERY."""
    _revenue_engine.event_bus.publish(
        "opportunity.delivered", {"opportunity_id": opportunity_id, "delivery_type": delivery_type}
    )


def publish_opportunity_validation(opportunity_id: str, valid: bool = True):
    """Publish opportunity validation event - Phase 7: VALIDATION."""
    _revenue_engine.event_bus.publish("opportunity.validated", {"opportunity_id": opportunity_id, "valid": valid})


def publish_payment_approval(payment_id: str):
    """Publish payment approval event - Phase 8: PAYMENT."""
    _revenue_engine.event_bus.publish("payment.approved", {"payment_id": payment_id})


def publish_payment_completion(payment_id: str):
    """Publish payment completion event - Phase 8: PAYMENT."""
    _revenue_engine.event_bus.publish("payment.paid", {"payment_id": payment_id})


def get_dashboard_data() -> dict[str, Any]:
    """Get dashboard data for revenue analytics."""
    total_opportunities = len(_revenue_engine.opportunities)
    evaluated_opportunities = sum(
        1
        for opp in _revenue_engine.opportunities.values()
        if opp.status in [OpportunityStatus.EVALUATED, OpportunityStatus.SELECTED, OpportunityStatus.VALIDATED]
    )

    total_payments = len(_revenue_engine.payments)
    paid_payments = sum(1 for pay in _revenue_engine.payments.values() if pay.status == PaymentStatus.PAID)

    by_platform = {}
    for opp in _revenue_engine.opportunities.values():
        platform = opp.platform.value
        if platform not in by_platform:
            by_platform[platform] = {"opportunities": 0, "revenue": Decimal("0")}
        by_platform[platform]["opportunities"] += 1
        by_platform[platform]["revenue"] += opp.base_reward

    by_status = {}
    for status in OpportunityStatus:
        count = sum(1 for opp in _revenue_engine.opportunities.values() if opp.status == status)
        if count > 0:
            by_status[status.value] = count

    return {
        "total_opportunities": total_opportunities,
        "evaluated_opportunities": evaluated_opportunities,
        "total_payments": total_payments,
        "paid_payments": paid_payments,
        "by_platform": by_platform,
        "by_status": by_status,
    }
