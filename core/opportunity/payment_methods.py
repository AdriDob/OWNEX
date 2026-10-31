"""
Payment methods — registry de métodos de cobro soportados para recibir pagos.

Este módulo define los métodos de pago disponibles para el sistema, con
elegibilidad verificable y sin secretos.

Métodos registrados:
- stripe_connect: estado argentino no confirmado; requiere verificar plataforma y beneficiario
- wise: Wise (UK), referencia de método
- paypal: PayPal (con restricciones de país)
- bank_transfer: Bancos argentinos (transferencia bancaria)
- crypto_usdc: USDC / crypto (solución no-KYC alternativa)
- manual_bank: Recibo bancario manual (verificar país)

Cada método tiene:
- ID único.
- Nombre legible.
- Cómo se paga (detalle de las flow).
- Estado de elegibilidad (si el usuario puede usarlo).
- Costo o tarifa estimada.
- Verificación requerida (documentación oficial, país admitido).

El registro no almacena secretos, tokens ni claves. Solo métodos verificados.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.payment_methods")


class PaymentMethodType(StrEnum):
    """Tipos de método de pago soportados."""

    STRIPE_CONNECT = "stripe_connect"
    WISE = "wise"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO_USDC = "crypto_usdc"
    MANUAL_BANK = "manual_bank"
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"


class PaymentMethodStatus(StrEnum):
    """Estado de elegibilidad de un método de pago."""

    VERIFIED = "verified"
    PLATFORM_DEPRECATED = "platform_deprecated"
    RESTRICTED = "restricted"
    COUNTRY_BLOCKED = "country_blocked"
    REQUIRES_HUMAN = "requires_human"
    CURRENCY_UNSUPPORTED = "currency_unsupported"
    ACCOUNT_PENDING = "account_pending"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


@dataclass
class PaymentMethod:
    """Un método de pago verificado, sin secretos."""

    method_type: PaymentMethodType
    name: str
    provider: str
    description: str
    payout_currency: str | None
    min_amount: float | None
    max_amount: float | None
    fees: str | None
    verification_notes: str
    eligibility: PaymentMethodStatus = PaymentMethodStatus.UNKNOWN
    requirements: list[str] = field(default_factory=list)
    verified_at: datetime | None = None
    verification_evidence: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def verify(self, status: PaymentMethodStatus, notes: str = "", evidence: dict[str, str] | None = None) -> None:
        """Marcar el método como verificado con estado explícito."""
        evidence = evidence or {}
        if status == PaymentMethodStatus.VERIFIED and not all(evidence.get(key) for key in ("source", "reference", "verified_by")):
            raise ValueError("Una verificación positiva requiere source, reference y verified_by")
        self.eligibility = status
        now = datetime.now(UTC)
        self.verified_at = now if status == PaymentMethodStatus.VERIFIED else None
        self.verification_evidence = {key: str(evidence[key]) for key in ("source", "reference", "verified_by") if evidence.get(key)}
        if notes:
            self.verification_notes = notes
        self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        """Serializar sin secretos."""
        return {
            "method_type": self.method_type.value,
            "name": self.name,
            "provider": self.provider,
            "description": self.description,
            "payout_currency": self.payout_currency,
            "min_amount": self.min_amount,
            "max_amount": self.max_amount,
            "fees": self.fees,
            "eligibility": self.eligibility.value,
            "requirements": self.requirements,
            "verification_notes": self.verification_notes,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verification_evidence": self.verification_evidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ── Registro canónico de métodos de pago ─────────────────────────────────────

_STANDARD_METHODS: list[PaymentMethod] = [
    PaymentMethod(
        method_type=PaymentMethodType.STRIPE_CONNECT,
        name="Stripe Connect",
        provider="Stripe",
        description=(
            "No confirmado para una cuenta o plataforma argentina. La disponibilidad "
            "de Stripe como país de negocio y la de sus productos de pagos globales "
            "son distintas; la plataforma pagadora debe confirmar elegibilidad."
        ),
        payout_currency=None,
        min_amount=None,
        max_amount=None,
        fees=None,
        verified_at=None,
        eligibility=PaymentMethodStatus.RESTRICTED,
        requirements=[
            "Confirmar si la plataforma ofrece Stripe Global Payouts a Argentina",
            "Confirmar aprobación del negocio/plataforma y elegibilidad del beneficiario",
            "Revisar tarifas, moneda y límites en la cuenta receptora",
        ],
        verification_notes=(
            "La lista oficial de países donde Stripe está disponible no incluye Argentina. "
            "Stripe documenta pagos globales a otros países, sujetos a aprobación y al producto; "
            "no equivale a una cuenta Stripe argentina ni confirma que una plataforma concreta pague aquí. "
            "Fuente consultada el 2026-10-29: https://stripe.com/global"
        ),
    ),
    PaymentMethod(
        method_type=PaymentMethodType.WISE,
        name="Wise",
        provider="Wise",
        description=(
            "Wise (antes TransferWise) es una opción internacional para transferencias "
            "y recibos. Formalmente,Wise ajusta los límites de cobro por país."
        ),
        payout_currency=None,
        min_amount=None,
        max_amount=None,
        fees=None,
        verified_at=None,
        eligibility=PaymentMethodStatus.RESTRICTED,
        requirements=[
            "Verificar país admitido",
            "Verificar límite de cobro",
            "¿Tienen cuenta empresarial en Argentina?",
        ],
        verification_notes=(
            "Wise: aprobar República Argentina. No almacenar credenciales, solo "
            "verificar si tienen cuenta adecuada."
        ),
    ),
    PaymentMethod(
        method_type=PaymentMethodType.PAYPAL,
        name="PayPal",
        provider="PayPal",
        description=(
            "PayPal es una opción común, pero tiene restricciones de país para recibir "
            "pagos. Verificar en la lista oficial de países admitidos."
        ),
        payout_currency=None,
        min_amount=None,
        max_amount=None,
        fees=None,
        verified_at=None,
        eligibility=PaymentMethodStatus.RESTRICTED,
        requirements=[
            "Verificar país admitido",
            "¿Cuenta verificada? ¿Pueden recibir pagos de Argentina?",
        ],
        verification_notes=(
            "PayPal: verificar país admitido. No almacenar credenciales, solo "
            "verificar si tienen cuenta adecuada."
        ),
    ),
    PaymentMethod(
        method_type=PaymentMethodType.BANK_TRANSFER,
        name="Transferencia bancaria (ARS)",
        provider="Bancos argentinos",
        description=(
            "Bancolombia/Banco Nación etc. Una de las formas más directas de recibir "
            "pagos en pesos argentinos, mediante transferencia internacional o entidad "
            "destinataria."
        ),
        payout_currency=None,
        min_amount=None,
        max_amount=None,
        fees=None,
        verified_at=None,
        eligibility=PaymentMethodStatus.REQUIRES_HUMAN,
        requirements=[
            "Cuenta bancaria en el banco"
        ],
        verification_notes=(
            "Bancolombia: transferencias de Argentinosa. No almacenar credenciales, "
            "verificar luego."
        ),
    ),
    PaymentMethod(
        method_type=PaymentMethodType.CRYPTO_USDC,
        name="USDC / Cripto",
        provider="Ethereum / Base / Solana",
        description=(
            "Solución de cobro no-KYC alternativa. USDC en Ethereum, Base o Solana, "
            "verificar que la plataforma admita cripto para pagos."
        ),
        payout_currency=None,
        min_amount=None,
        max_amount=None,
        fees=None,
        verified_at=None,
        eligibility=PaymentMethodStatus.REQUIRES_HUMAN,
        requirements=[
            "Carnet de identidad o documento fiscal",
            "Sentir de portafolio para cobrar",
        ],
        verification_notes=(
            "No-KYC: si el usuario tiene wallet con USDC y puede recibir. Verificar "
            "que la plataforma admite cripto."
        ),
    ),
    PaymentMethod(
        method_type=PaymentMethodType.MANUAL_BANK,
        name="Recibo bancario manual",
        provider="Usuario",
        description=(
            "Metodo no-KYC: generar un recibo bancario y enviarlo al usuario. "
            "El usuario transfiere y el usuario verifica el ingreso."
        ),
        payout_currency=None,
        min_amount=None,
        max_amount=None,
        fees=None,
        verified_at=None,
        eligibility=PaymentMethodStatus.REQUIRES_HUMAN,
        requirements=[
            "Usuario debe poder generar un recibo",
            "Usuario debe verificar el ingreso",
        ],
        verification_notes=(
            "Recibo manual: no requiere KYC. Verificar después."
        ),
    ),
    PaymentMethod(
        method_type=PaymentMethodType.BITCOIN,
        name="Bitcoin",
        provider="Bitcoin",
        description=(
            "Bitcoin: cobro descentralizado, no-KYC. Verificar luego."
        ),
        payout_currency=None,
        min_amount=None,
        max_amount=None,
        fees=None,
        verified_at=None,
        eligibility=PaymentMethodStatus.RESTRICTED,
        requirements=[
            "Verificar que la plataforma admita cripto",
            "¿El usuario puede recibir Bitcoin?",
        ],
        verification_notes=(
            "Bitcoin: no almacenar credenciales, solo verificar si el usuario tiene "
            "wallet y la plataforma admite cripto."
        ),
    ),
    PaymentMethod(
        method_type=PaymentMethodType.ETHEREUM,
        name="Ethereum",
        provider="Ethereum",
        description=(
            "Ethereum: cobro descentralizado, no-KYC. Verificar luego."
        ),
        payout_currency=None,
        min_amount=None,
        max_amount=None,
        fees=None,
        verified_at=None,
        eligibility=PaymentMethodStatus.RESTRICTED,
        requirements=[
            "Verificar que la plataforma admita cripto",
            "¿El usuario puede recibir Ethereum?",
        ],
        verification_notes=(
            "Ethereum: no almacenar credenciales, solo verificar si el usuario tiene "
            "wallet y la plataforma acepta cripto."
        ),
    ),
]


def get_payment_methods() -> list[PaymentMethod]:
    """Obtener todos los métodos de pago registrados."""
    return list(_STANDARD_METHODS)


def get_payment_method(method_type: str | PaymentMethodType) -> PaymentMethod | None:
    """Obtener un método de pago por tipo."""
    for method in _STANDARD_METHODS:
        if method.method_type == method_type:
            return method
    return None


def get_payment_methods_by_status(status: PaymentMethodStatus) -> list[PaymentMethod]:
    """Obtener métodos de pago con un estado de elegibilidad."""
    return [m for m in _STANDARD_METHODS if m.eligibility == status]
