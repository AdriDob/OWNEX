"""
Tests for Payment Trail — registro de verdad financiera.

Las pruebas verifican:
- Transiciones explícitas válidas.
- Transiciones ilegales denegadas.
- Registro de pago con evidencia.
- Verificación en red.
- Retiro confirmado.
- No se marca PAID sin evidencia verificable.
"""

from datetime import UTC, datetime

import pytest

from core.opportunity.payment_trail import (
    EligibilityState,
    OpportunityTrail,
    PaymentState,
    PaymentTransitionRule,
    calculate_net_income,
    serialize,
)


class TestPaymentTrailStates:
    """Verificar estados canónicos."""

    def test_states_exist(self):
        """Los estados del enum están definidos."""
        assert PaymentState.PENDING == "pending"
        assert PaymentState.DISCOVERED == "discovered"
        assert PaymentState.ELIGIBILITY_VERIFIED == "eligibility_verified"
        assert PaymentState.WORK_ELIGIBLE == "work_eligible"
        assert PaymentState.IN_PROGRESS == "in_progress"
        assert PaymentState.SUBMITTED == "submitted"
        assert PaymentState.ACCEPTED == "accepted"
        assert PaymentState.OWED == "owed"
        assert PaymentState.PAID == "paid"
        assert PaymentState.WITHDRAWN == "withdrawn"
        assert PaymentState.FAILED == "failed"
        assert PaymentState.REJECTED == "rejected"
        assert PaymentState.BLOCKED == "blocked"
        assert PaymentState.DEAD_LETTER == "dead_letter"
        assert PaymentState.QUEUED == "queued"

    def test_eligibility_states_exist(self):
        """Los estados de elegibilidad están definidos."""
        assert EligibilityState.DISCOVERY_AVAILABLE == "discovery_available"
        assert EligibilityState.WORK_ELIGIBLE == "work_eligible"
        assert EligibilityState.PAYOUT_ELIGIBLE == "payout_eligible"
        assert EligibilityState.PAYOUT_ELIGIBILITY_VERIFIED == "payout_eligibility_verified"
        assert EligibilityState.PAYOUT_COUNTRY_UNSUPPORTED == "payout_country_unsupported"
        assert EligibilityState.PAID == "paid"
        assert EligibilityState.BLOCKED == "blocked"
        assert EligibilityState.UNKNOWN == "unknown"


class TestPaymentTrailTransitionRules:
    """Verificar transiciones explícitas."""

    def test_can_transition_discovered_to_eligibility_verified(self):
        """Transición descubrimiento → elegibilidad verificada permitida."""
        assert PaymentTransitionRule.can_transition(PaymentState.DISCOVERED, PaymentState.ELIGIBILITY_VERIFIED) is True

    def test_can_transition_eligibility_verified_to_work_eligible(self):
        """Transición elegibilidad verificada → trabajo elegible permitida."""
        assert PaymentTransitionRule.can_transition(PaymentState.ELIGIBILITY_VERIFIED, PaymentState.WORK_ELIGIBLE) is True

    def test_can_transition_work_eligible_to_in_progress(self):
        """Transición trabajo elegible → en progreso permitida."""
        assert PaymentTransitionRule.can_transition(PaymentState.WORK_ELIGIBLE, PaymentState.IN_PROGRESS) is True

    def test_can_transition_in_progress_to_submitted(self):
        """Transición en progreso → enviado permitida."""
        assert PaymentTransitionRule.can_transition(PaymentState.IN_PROGRESS, PaymentState.SUBMITTED) is True

    def test_can_transition_submitted_to_accepted(self):
        """Transición enviado → aceptado permitida."""
        assert PaymentTransitionRule.can_transition(PaymentState.SUBMITTED, PaymentState.ACCEPTED) is True

    def test_can_transition_accepted_to_owed(self):
        """Transición aceptado → por pagar permitida."""
        assert PaymentTransitionRule.can_transition(PaymentState.ACCEPTED, PaymentState.OWED) is True

    def test_can_transition_owed_to_paid(self):
        """La recompensa por pagar debe verificarse antes de marcarse pagada."""
        assert PaymentTransitionRule.can_transition(PaymentState.OWED, PaymentState.VERIFICATION) is True
        assert PaymentTransitionRule.can_transition(PaymentState.VERIFICATION, PaymentState.PAID) is True
        assert PaymentTransitionRule.can_transition(PaymentState.OWED, PaymentState.PAID) is False

    def test_cannot_transition_discovered_to_paid(self):
        """Transición descubrimiento → pagado denegada."""
        assert PaymentTransitionRule.can_transition(PaymentState.DISCOVERED, PaymentState.PAID) is False

    def test_illegal_transition_raises(self):
        """Transición ilegal lanza AssertionError."""
        with pytest.raises(AssertionError):
            PaymentTransitionRule.enforce(PaymentState.DISCOVERED, PaymentState.PAID)


class TestOpportunityTrail:
    """Verificar el registro de la traza de pago."""

    def test_register_and_get_trail(self):
        """Registrar y obtener la traza."""
        from core.opportunity.payment_trail import get_trail, register_trail

        trail = OpportunityTrail(
            opportunity_id="ab_1",
            name="Test",
            platform="agent_bounties",
            reward_announced=100.0,
        )
        register_trail(trail.opportunity_id, trail)

        retrieved = get_trail("ab_1")
        assert retrieved is not None
        assert retrieved.name == "Test"
        assert retrieved.reward_announced == 100.0

    def test_agent_bounties_initial_trail_uses_defined_pending_state(self):
        from api.routers.agent_bounties_dashboard import _get_initial_trail

        trail = _get_initial_trail()

        assert trail.status == PaymentState.PENDING

    @pytest.mark.asyncio
    async def test_daily_brief_does_not_claim_unverified_market_results(self):
        from api.routers.agent_bounties_dashboard import get_daily_brief, list_sources

        brief = await get_daily_brief()
        sources = await list_sources()

        assert brief["daily_brief_confirmed"] == []
        assert brief["protocols"] == []
        assert brief["overview"]["sources_unverified"] == brief["overview"]["total_sources"]
        assert all(source["status"] == EligibilityState.UNKNOWN for source in brief["sources"])
        assert all(source["payout_country_supported"] is None for source in brief["sources"])
        assert sources["sources_unverified"] == sources["total_sources"]

    def test_mark_preserves_evidence(self):
        """El mark preserva la evidencia."""
        trail = OpportunityTrail(opportunity_id="ab_1", name="Test")
        trail.mark(PaymentState.DISCOVERED, {"source": "test"})

        assert trail.status == PaymentState.DISCOVERED
        assert trail.evidence["source"] == "test"

    def test_record_payment_registers_hash(self):
        """El registro de pago guarda el hash y pasa a VERIFICATION."""
        trail = OpportunityTrail(opportunity_id="ab_1", name="Test", status=PaymentState.OWED)
        trail.record_payment(amount=50.0, payment_hash="0xabc")

        assert trail.status == PaymentState.VERIFICATION
        assert trail.payment_hash == "0xabc"
        assert trail.reward_confirmed == 50.0

    def test_verify_payment_on_chain_verified_marks_paid(self):
        """Verificar pago en red confirmado marca PAID."""
        trail = OpportunityTrail(opportunity_id="ab_1", name="Test", status=PaymentState.OWED)
        trail.record_payment(amount=50.0, payment_hash="0xabc")
        trail.verify_payment_on_chain(payment_hash="0xabc", verified=True)

        assert trail.status == PaymentState.PAID
        assert trail.payment_verified is True

    def test_verify_payment_on_chain_unverified_marks_failed(self):
        """Verificar pago en red no confirmado marca FAILED."""
        trail = OpportunityTrail(opportunity_id="ab_1", name="Test", status=PaymentState.OWED)
        trail.record_payment(amount=50.0, payment_hash="0xabc")
        trail.verify_payment_on_chain(payment_hash="0xabc", verified=False)

        assert trail.status == PaymentState.FAILED
        assert trail.payment_verified is False

    def test_record_withdrawal_confirmed_marks_withdrawn(self):
        """Registrar retiro confirmado marca WITHDRAWN."""
        trail = OpportunityTrail(
            opportunity_id="ab_1",
            name="Test",
            status=PaymentState.PAID,
            payment_hash="0xabc",
            payment_verified=True,
            payment_verified_at=datetime.now(UTC),
        )
        trail.record_withdrawal(wallet_tx_hash="0xdef", confirmed=True)

        assert trail.status == PaymentState.WITHDRAWN
        assert trail.withdrawal_confirmed is True

    def test_paid_cannot_be_marked_without_verification(self):
        trail = OpportunityTrail(opportunity_id="ab_1", name="Test")

        with pytest.raises(ValueError, match="PAID requiere"):
            trail.mark(PaymentState.PAID)

    def test_verification_requires_matching_recorded_hash(self):
        trail = OpportunityTrail(opportunity_id="ab_1", name="Test", status=PaymentState.OWED)
        trail.record_payment(amount=50.0, payment_hash="0xabc")

        with pytest.raises(ValueError, match="coincidir"):
            trail.verify_payment_on_chain(payment_hash="0xother", verified=True)

    def test_withdrawal_requires_paid_state(self):
        trail = OpportunityTrail(opportunity_id="ab_1", name="Test")

        with pytest.raises(ValueError, match="después de confirmar"):
            trail.record_withdrawal(wallet_tx_hash="0xdef", confirmed=True)

    def test_calculate_net_income_returns_confirmed(self):
        """Calcular ingreso neto devuelve la cantidad confirmada."""
        trail = OpportunityTrail(
            opportunity_id="ab_1",
            name="Test",
            reward_announced=100.0,
            reward_confirmed=80.0,
        )
        result = calculate_net_income(trail)

        assert result["gross_amount"] == 100.0
        assert result["net_amount"] == 80.0
        assert result["status"] is None


class TestPaymentTrailSerialization:
    """Verificar serialización."""

    def test_serialize_contains_evidence(self):
        """Serializar incluye evidencia."""
        trail = OpportunityTrail(opportunity_id="ab_1", name="Test")
        trail.mark(PaymentState.DISCOVERED, {"source": "verified"})

        data = serialize(trail)

        assert data["opportunity_id"] == "ab_1"
        assert data["status"] == "discovered"
        assert data["evidence"]["source"] == "verified"
        assert "created_at" in data
        assert "updated_at" in data

    def test_serialize_preserves_ids(self):
        """La serialización preserva los IDs."""
        trail = OpportunityTrail(opportunity_id="ab_1", name="Test")
        data = serialize(trail)

        assert data["opportunity_id"] == "ab_1"
        assert data["name"] == "Test"
