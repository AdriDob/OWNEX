"""OpportunityStage pipeline tests — Income Multiplier Fase A slice 3."""

from __future__ import annotations

from cores.revenue_tracker.revenue_tracker import (
    OpportunityStage,
    PaymentStatus,
    stage_from_payment_status,
    stage_from_workbank_status,
)


class TestWorkBankMapping:
    def test_ready_to_deliver_is_in_progress_not_submitted(self) -> None:
        """Prepared ≠ sent: money language stays honest."""
        assert stage_from_workbank_status("ready_to_deliver") is OpportunityStage.IN_PROGRESS

    def test_delivered_maps_to_submitted(self) -> None:
        assert stage_from_workbank_status("delivered") is OpportunityStage.SUBMITTED

    def test_needs_access_is_qualified(self) -> None:
        assert stage_from_workbank_status("needs_access") is OpportunityStage.QUALIFIED

    def test_unknown_defaults_to_least_committal(self) -> None:
        assert stage_from_workbank_status("whatever") is OpportunityStage.DISCOVERED

    def test_case_insensitive(self) -> None:
        assert stage_from_workbank_status("Delivered") is OpportunityStage.SUBMITTED


class TestPaymentStatusMapping:
    def test_paid_is_paid(self) -> None:
        assert stage_from_payment_status(PaymentStatus.PAID) is OpportunityStage.PAID

    def test_accepted_is_accepted(self) -> None:
        assert stage_from_payment_status(PaymentStatus.ACCEPTED) is OpportunityStage.ACCEPTED

    def test_failed_and_cancelled_are_rejected(self) -> None:
        assert stage_from_payment_status(PaymentStatus.FAILED) is OpportunityStage.REJECTED
        assert stage_from_payment_status(PaymentStatus.CANCELLED) is OpportunityStage.REJECTED

    def test_pending_reviewing_are_submitted(self) -> None:
        assert stage_from_payment_status(PaymentStatus.PENDING) is OpportunityStage.SUBMITTED
        assert stage_from_payment_status(PaymentStatus.REVIEWING) is OpportunityStage.SUBMITTED
