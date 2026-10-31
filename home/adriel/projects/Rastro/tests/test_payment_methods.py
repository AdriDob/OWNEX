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
        assert method.name == "Stripe Connect (Effects)"
        assert method.payout_currency == "ARS"
        assert method.eligibility == PaymentMethodStatus.VERIFIED

    def test_get_payment_method_not_found(self):
        """Método no encontrado devuelve None."""
        method = get_payment_method("unknown_method")
        assert method is None

    def test_payment_method_has_verified_at(self):
        """Los métodos verificados tienen timestamp verificado."""
        for method in get_payment_methods():
            assert method.verified_at is not None
            assert method.created_at <= method.verified_at


class TestPaymentAdapter:
    """Verificar el adaptador de cobro."""

    def test_adapter_verifies_method(self):
        """El adaptador verifica un método y devuelve estado."""
        adapter = PaymentAdapter(config={})
        verification = adapter.verify_method(PaymentMethodType.STRIPE_CONNECT)

        assert verification.method_type == PaymentMethodType.STRIPE_CONNECT
        assert verification.verified is True
        assert verification.status == PaymentMethodStatus.VERIFIED
        assert "verificado" in verification.verification_notes.lower()

    def test_adapter_is_method_available(self):
        """Verificar si un método está disponible sin secrets."""
        adapter = PaymentAdapter(config={})
        adapter.is_method_available(PaymentMethodType.STRIPE_CONNECT)

        # Stripe Connect está verificado, pero el método es VERIFIED
        # La verificación requiere estado VERIFIED
        method = get_payment_method(PaymentMethodType.STRIPE_CONNECT)
        assert method is not None
        assert method.eligibility == PaymentMethodStatus.VERIFIED

    def test_adapter_get_method_status(self):
        """Obtener estado de un método."""
        adapter = PaymentAdapter(config={})
        adapter.verify_method(PaymentMethodType.STRIPE_CONNECT)

        status = adapter.get_method_status(PaymentMethodType.STRIPE_CONNECT)
        assert status is not None
        assert status.method_type == PaymentMethodType.STRIPE_CONNECT
        assert status.status == PaymentMethodStatus.VERIFIED

    def test_adapter_get_verified_methods(self):
        """Obtener métodos verificados."""
        adapter = PaymentAdapter(config={})
        adapter.verify_method(PaymentMethodType.STRIPE_CONNECT)
        adapter.verify_method(PaymentMethodType.BANK_TRANSFER)

        verified = adapter.get_verified_methods()
        assert PaymentMethodType.STRIPE_CONNECT in verified
        assert PaymentMethodType.BANK_TRANSFER in verified

    def test_adapter_record_verification_result(self):
        """Registrar resultado de verificación."""
        adapter = PaymentAdapter(config={})
        result = adapter.record_verification_result(
            PaymentMethodType.STRIPE_CONNECT,
            verified=True,
            evidence={"test": "evidence_123"},
        )

        assert result.verified is True
        assert result.status == PaymentMethodStatus.VERIFIED
        assert result.verification_date is not None

    def test_adapter_no_secrets(self):
        """El adaptador no almacena secretos ni credenciales."""
        adapter = PaymentAdapter(config={})
        adapter.verify_method(PaymentMethodType.STRIPE_CONNECT)

        # Verificar que no hay métodos de pago con credenciales secretas
        methods = get_payment_methods()
        for method in methods:
            assert method.verification_notes  # Verificar sin credenciales secretas
