"""Payout Recommender — suggests best withdrawal methods per platform for Argentina (DNI/KYC)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Data types ──────────────────────────────────────────────────────


@dataclass
class PayoutMethod:
    id: str
    name: str
    type: str  # crypto, bank, p2p, wallet
    kyc_level: str  # none, email, dni, passport
    currencies: list[str] = field(default_factory=list)
    fee_percent: float = 0.0
    arrival_days: str = "1-3"
    notes: str = ""
    supported_in_argentina: bool = True


@dataclass
class PlatformPayoutInfo:
    platform_id: str
    platform_name: str
    methods: list[PayoutMethod]
    recommended: list[str]  # method IDs, best first
    kyc_required: str  # what docs the platform itself needs
    notes: str = ""


# ── Available methods for Argentina ─────────────────────────────────

_METHODS: dict[str, PayoutMethod] = {
    "takenos": PayoutMethod(
        id="takenos", name="Takenos", type="wallet",
        kyc_level="dni", currencies=["USD", "ARS"],
        fee_percent=1.0, arrival_days="1-2",
        notes="Cuenta virtual USD. Transferís a tu banco argentino vía CBU. KYC: DNI + selfie. La mejor opción desde Argentina.",
    ),
    "binance_p2p": PayoutMethod(
        id="binance_p2p", name="Binance P2P", type="p2p",
        kyc_level="dni", currencies=["USDT", "USDC", "ARS"],
        fee_percent=0.0, arrival_days="instantáneo",
        notes="Comprá USDT/USDC en exchange, vendé por P2P a ARS. KYC: DNI. Retirá por transferencia bancaria local.",
    ),
    "usdc_crypto": PayoutMethod(
        id="usdc_crypto", name="USDC (Crypto)", type="crypto",
        kyc_level="none", currencies=["USDC"],
        fee_percent=0.0, arrival_days="instantáneo",
        notes="Stablecoin dólar. Aceptada por Immunefi, Code4rena. Retené en wallet o convertí vía P2P.",
    ),
    "usdt_crypto": PayoutMethod(
        id="usdt_crypto", name="USDT (Crypto)", type="crypto",
        kyc_level="none", currencies=["USDT"],
        fee_percent=0.0, arrival_days="instantáneo",
        notes="Stablecoin atada al dólar. Ampliamente aceptada. Convertí a ARS vía Binance P2P.",
    ),
    "eth_crypto": PayoutMethod(
        id="eth_crypto", name="ETH (Crypto)", type="crypto",
        kyc_level="none", currencies=["ETH"],
        fee_percent=0.0, arrival_days="instantáneo",
        notes="Ether. Usado principalmente en Immunefi para pagos en ETH nativo.",
    ),
    "payoneer": PayoutMethod(
        id="payoneer", name="Payoneer", type="wallet",
        kyc_level="passport", currencies=["USD"],
        fee_percent=2.0, arrival_days="2-5",
        notes="Cuenta virtual USD. Podés extraer a banco argentino. KYC requiere pasaporte (no solo DNI).",
    ),
    "paypal": PayoutMethod(
        id="paypal", name="PayPal", type="wallet",
        kyc_level="dni", currencies=["USD"],
        fee_percent=4.4, arrival_days="instantáneo",
        notes="Aceptado por algunas plataformas. Difícil de retirar a ARS sin costos altos. Usar sólo si no hay alternativa.",
    ),
    "bank_swift": PayoutMethod(
        id="bank_swift", name="Transferencia SWIFT", type="bank",
        kyc_level="dni", currencies=["USD"],
        fee_percent=3.0, arrival_days="5-15",
        notes="Transferencia bancaria internacional. Lenta y cara. Bancos argentinos complican la recepción de USD.",
    ),
    "lemon": PayoutMethod(
        id="lemon", name="Lemon Cash", type="crypto",
        kyc_level="dni", currencies=["USDC", "USDT", "BTC"],
        fee_percent=0.0, arrival_days="instantáneo",
        notes="Exchange argentino. Recibí crypto, vendé a ARS y retirá por transferencia. KYC: DNI.",
    ),
    "belo": PayoutMethod(
        id="belo", name="Belo", type="crypto",
        kyc_level="dni", currencies=["USDC", "USDT", "BTC"],
        fee_percent=0.0, arrival_days="instantáneo",
        notes="Exchange argentino. Similar a Lemon Cash. KYC: DNI. Transferencias a tu banco.",
    ),
}

# ── Platform mappings ───────────────────────────────────────────────

_PLATFORM_PAYOUTS: dict[str, PlatformPayoutInfo] = {
    "hackerone": PlatformPayoutInfo(
        platform_id="hackerone",
        platform_name="HackerOne",
        methods=[
            _METHODS["payoneer"],
            _METHODS["usdc_crypto"],
            _METHODS["bank_swift"],
        ],
        recommended=["payoneer", "usdc_crypto"],
        kyc_required="Documento de identidad + W-8BEN (para Argentina)",
        notes="HackerOne paga vía Payoneer o transferencia bancaria. No soporta crypto directo. Payoneer es la opción más práctica.",
    ),
    "bugcrowd": PlatformPayoutInfo(
        platform_id="bugcrowd",
        platform_name="Bugcrowd",
        methods=[
            _METHODS["payoneer"],
            _METHODS["usdc_crypto"],
            _METHODS["bank_swift"],
        ],
        recommended=["payoneer", "usdc_crypto"],
        kyc_required="Documento de identidad",
        notes="Bugcrowd paga por Payoneer o transferencia. Recomendamos Payoneer y luego convertir los USD a ARS.",
    ),
    "intigriti": PlatformPayoutInfo(
        platform_id="intigriti",
        platform_name="Intigriti",
        methods=[
            _METHODS["paypal"],
            _METHODS["usdc_crypto"],
            _METHODS["bank_swift"],
        ],
        recommended=["usdc_crypto", "paypal"],
        kyc_required="Documento + verificación bancaria",
        notes="Intigriti ofrece PayPal o transferencia bancaria. Crypto no es opción directa. Si tenés cuenta en Lemon/Belo, podés recibir por PayPal y operar.",
    ),
    "synack": PlatformPayoutInfo(
        platform_id="synack",
        platform_name="Synack",
        methods=[
            _METHODS["payoneer"],
            _METHODS["usdc_crypto"],
        ],
        recommended=["payoneer", "usdc_crypto"],
        kyc_required="W-8BEN (Argentina) + identificación",
        notes="Synack paga por Payoneer. Requieren W-8BEN. Misma estrategia: Payoneer → ARS.",
    ),
    "yeswehack": PlatformPayoutInfo(
        platform_id="yeswehack",
        platform_name="YesWeHack",
        methods=[
            _METHODS["paypal"],
            _METHODS["bank_swift"],
            _METHODS["usdc_crypto"],
        ],
        recommended=["paypal", "usdc_crypto"],
        kyc_required="DNI / Pasaporte",
        notes="YesWeHack paga por PayPal o SWIFT. Recomendamos PayPal y usar exchange argentino para convertir a ARS.",
    ),
    "immunefi": PlatformPayoutInfo(
        platform_id="immunefi",
        platform_name="Immunefi",
        methods=[
            _METHODS["usdc_crypto"],
            _METHODS["usdt_crypto"],
            _METHODS["eth_crypto"],
        ],
        recommended=["usdc_crypto", "usdt_crypto"],
        kyc_required="Solo wallet address (pagos en crypto)",
        notes="Immunefi paga en crypto nativo (USDC, USDT, ETH, DAI). Ideal: recibí USDC y vendé por P2P en Binance o Lemon/Belo a ARS.",
    ),
    "code4rena": PlatformPayoutInfo(
        platform_id="code4rena",
        platform_name="Code4rena",
        methods=[
            _METHODS["usdc_crypto"],
            _METHODS["usdt_crypto"],
            _METHODS["eth_crypto"],
        ],
        recommended=["usdc_crypto", "usdt_crypto"],
        kyc_required="Solo wallet address (pagos en crypto)",
        notes="Code4rena paga en crypto. Competitions pagan en USDC/USDT. Misma estrategia que Immunefi.",
    ),
    "huntr": PlatformPayoutInfo(
        platform_id="huntr",
        platform_name="Huntr",
        methods=[
            _METHODS["paypal"],
            _METHODS["usdc_crypto"],
        ],
        recommended=["usdc_crypto", "paypal"],
        kyc_required="Documento de identidad",
        notes="Huntr paga por PayPal. Podés usar Lemon Cash para convertir a ARS sin costo.",
    ),
}

# ── Public API ──────────────────────────────────────────────────────


def get_platform_payout(platform_id: str) -> PlatformPayoutInfo | None:
    """Get payout info for a specific platform."""
    return _PLATFORM_PAYOUTS.get(platform_id.lower())


def list_all_payout_infos() -> list[dict[str, Any]]:
    """List payout info for all platforms."""
    results = []
    for info in _PLATFORM_PAYOUTS.values():
        results.append(_info_to_dict(info))
    return results


def get_best_methods_for_argentina() -> list[dict[str, Any]]:
    """Get best overall payout methods for Argentina, ranked."""
    ranked = [
        _METHODS["takenos"],
        _METHODS["lemon"],
        _METHODS["belo"],
        _METHODS["binance_p2p"],
        _METHODS["usdc_crypto"],
        _METHODS["usdt_crypto"],
        _METHODS["payoneer"],
        _METHODS["paypal"],
    ]
    return [_method_to_dict(m) for m in ranked]


def _method_to_dict(m: PayoutMethod) -> dict[str, Any]:
    return {
        "id": m.id,
        "name": m.name,
        "type": m.type,
        "kyc_level": m.kyc_level,
        "currencies": m.currencies,
        "fee_percent": m.fee_percent,
        "arrival_days": m.arrival_days,
        "notes": m.notes,
    }


def _info_to_dict(info: PlatformPayoutInfo) -> dict[str, Any]:
    return {
        "platform_id": info.platform_id,
        "platform_name": info.platform_name,
        "methods": [_method_to_dict(m) for m in info.methods],
        "recommended": info.recommended,
        "kyc_required": info.kyc_required,
        "notes": info.notes,
    }
