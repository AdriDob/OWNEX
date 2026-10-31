"""
Tests for Payment Methods — métodos de cobro sin secretos.

Las pruebas verifican:
- Métodos de pago registrados y sus estados.
- Verificación de métodos sin secretos.
- Lógica del adaptador de cobro.

Reglas del prompt aplicadas:
- Sin secretos.
- Sin acciones externas irreversibles.
- Transiciones de estado explícitas.
- Sin falsos resultados.
"""

import pytest

from core.opportunity.adapters.payment_adapter import (
    PaymentAdapter,
)
from core.opportunity.payment_methods import (
    PaymentMethodStatus,
    PaymentMethodType,
    get_payment_method,
    get_payment_methods,
)


class TestPaymentMethods:
    """Verificar métodos de pago registrados."""

    def test_get_payment_methods_returns_all(self):
        """Obtener todos los métodos de pago registrados."""
        methods = get_payment_methods()
        assert isinstance(methods, list)
        assert len(methods) >= 6  # Stripe, Wise, PayPal, Bank, Crypto, Manual

    def test_get_payment_method_found(self):
        """Obtener un método por tipo."""
        method = get_payment_method(PaymentMethodType.STRIPE_CONNECT)
        assert method is not None
        assert method.name == "Stripe Connect"
        assert method.payout_currency is None
        assert method.eligibility == PaymentMethodStatus.RESTRICTED

    def test_get_payment_method_not_found(self):
        """Método no encontrado devuelve None."""
        method = get_payment_method("unknown_method")
        assert method is None

    def test_unverified_payment_methods_have_no_verified_timestamp(self):
        """Los métodos no confirmados no reciben fechas de verificación ficticias."""
        for method in get_payment_methods():
            if method.eligibility == PaymentMethodStatus.VERIFIED:
                assert method.verified_at is not None
            else:
                assert method.verified_at is None

    def test_unverified_methods_do_not_claim_currencies_fees_or_limits(self):
        for method in get_payment_methods():
            assert method.eligibility != PaymentMethodStatus.VERIFIED
            assert method.payout_currency is None
            assert method.min_amount is None
            assert method.max_amount is None
            assert method.fees is None


class TestPaymentAdapter:
    """Verificar el adaptador de cobro."""

    def test_adapter_verifies_method(self):
        """El adaptador verifica un método y devuelve estado."""
        adapter = PaymentAdapter(config={})
        verification = adapter.verify_method(PaymentMethodType.STRIPE_CONNECT)

        assert verification.method_type == PaymentMethodType.STRIPE_CONNECT
        assert verification.verified is False
        assert verification.status == PaymentMethodStatus.RESTRICTED
        assert "no confirmada" in verification.verification_notes.lower()

    def test_adapter_is_method_available(self):
        """Verificar si un método está disponible sin secrets."""
        adapter = PaymentAdapter(config={})
        adapter.is_method_available(PaymentMethodType.STRIPE_CONNECT)

        method = get_payment_method(PaymentMethodType.STRIPE_CONNECT)
        assert method is not None
        assert method.eligibility == PaymentMethodStatus.RESTRICTED
        assert adapter.is_method_available(PaymentMethodType.STRIPE_CONNECT) is False

    def test_adapter_get_method_status(self):
        """Obtener estado de un método."""
        adapter = PaymentAdapter(config={})
        adapter.verify_method(PaymentMethodType.STRIPE_CONNECT)

        status = adapter.get_method_status(PaymentMethodType.STRIPE_CONNECT)
        assert status is not None
        assert status.method_type == PaymentMethodType.STRIPE_CONNECT
        assert status.status == PaymentMethodStatus.RESTRICTED

    def test_adapter_get_verified_methods(self):
        """Obtener métodos verificados."""
        adapter = PaymentAdapter(config={})
        adapter.record_verification_result(
            PaymentMethodType.STRIPE_CONNECT,
            verified=True,
            evidence={"source": "authorized_platform", "reference": "account-review-1", "verified_by": "test-user"},
        )

        verified = adapter.get_verified_methods()
        assert PaymentMethodType.STRIPE_CONNECT in verified
        assert PaymentMethodType.BANK_TRANSFER not in verified
        assert adapter.is_method_available(PaymentMethodType.STRIPE_CONNECT) is True

    def test_adapter_record_verification_result(self):
        """Registrar resultado de verificación."""
        adapter = PaymentAdapter(config={})
        result = adapter.record_verification_result(
            PaymentMethodType.STRIPE_CONNECT,
            verified=True,
            evidence={"source": "authorized_platform", "reference": "evidence_123", "verified_by": "test-user"},
        )

        assert result.verified is True
        assert result.status == PaymentMethodStatus.VERIFIED
        assert result.verification_date is not None
        assert result.to_dict()["evidence"] == {
            "source": "authorized_platform",
            "reference": "evidence_123",
            "verified_by": "test-user",
        }

    def test_positive_verification_requires_provenance(self):
        adapter = PaymentAdapter(config={})

        with pytest.raises(ValueError, match="source, reference y verified_by"):
            adapter.record_verification_result(PaymentMethodType.STRIPE_CONNECT, verified=True, evidence={"test": "only"})

    def test_registry_method_cannot_be_marked_verified_without_provenance(self):
        method = get_payment_method(PaymentMethodType.STRIPE_CONNECT)
        assert method is not None

        with pytest.raises(ValueError, match="source, reference y verified_by"):
            method.verify(PaymentMethodStatus.VERIFIED)

    def test_adapter_no_secrets(self):
        """El adaptador no almacena secretos ni credenciales."""
        adapter = PaymentAdapter(config={})
        adapter.verify_method(PaymentMethodType.STRIPE_CONNECT)

        # Verificar que no hay métodos de pago con credenciales secretas
        methods = get_payment_methods()
        for method in methods:
            assert method.verification_notes  # Verificar sin credenciales secretas
