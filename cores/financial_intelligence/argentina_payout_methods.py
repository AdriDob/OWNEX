"""Argentina Payout Methods Database — Complete payout solution for OWNEX.

Comprehensive database of 50+ payout methods for Argentina that work with only KYC.
OWNEX uses this to recommend the best payout method for each platform.

Features:
- 50+ payout methods (crypto, fintech, traditional banks, remittances)
- Platform compatibility matrix
- KYC requirements (only personal KYC, no offshore/corporate)
- Fee structure and timing
- Automatic recommendation engine
- Persistent configuration
"""

import json
import os
from dataclasses import dataclass
from enum import Enum


class PayoutMethodType(Enum):
    """Types of payout methods."""

    CRYPTO = "crypto"  # Cryptocurrency wallets and exchanges
    FINTECH = "fintech"  # Digital wallets and neobanks
    TRADITIONAL = "traditional"  # Traditional banks
    REMITTANCE = "remittance"  # International remittance services
    MARKETPLACE = "marketplace"  # Crypto marketplaces (P2P)
    GIFT_CARD = "gift_card"  # Gift cards and vouchers
    PREPAID = "prepaid"  # Prepaid cards


class KYCLevel(Enum):
    """KYC requirements levels."""

    NONE = "none"  # No KYC required
    BASIC = "basic"  # Basic ID verification
    STANDARD = "standard"  # Standard KYC (ID + proof of address)
    ADVANCED = "advanced"  # Advanced KYC (income verification, etc)


@dataclass
class PayoutMethod:
    """Complete payout method specification."""

    id: str
    name: str
    type: PayoutMethodType
    kyc_level: KYCLevel
    platforms: list[str]  # Compatible platforms
    fees: dict[str, float]  # Fee structure (fixed, percentage, withdrawal)
    timing: dict[str, int]  # Timing in days (setup, transfer, arrival)
    routes: list[str]  # Possible routes to ARS
    pros: list[str]
    cons: list[str]
    minimum_withdrawal: float
    maximum_withdrawal: float | None
    notes: str
    reliability_score: float  # 0-100 based on user experience
    argentina_compatible: bool = True
    requires_vpn: bool = False
    setup_difficulty: str = "easy"  # easy, medium, hard


# Complete database of 50+ payout methods for Argentina
ARGENTINA_PAYOUT_METHODS: list[PayoutMethod] = [
    # ===== CRYPTO METHODS =====
    PayoutMethod(
        id="binance_ar",
        name="Binance Argentina",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam", "Gitcoin", "Code4rena", "Immunefi"],
        fees={"fixed": 1.0, "percentage": 0.1, "withdrawal": 0.5},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["USDC(Polygon) → Binance → ARS", "USDT → Binance → ARS"],
        pros=["Mejor tipo de cambio AR", "Soporte 24/7", "Bajas comisiones", "Confiable"],
        cons=["Requiere KYC completo", "Limites diarios sin verificar"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=100000.0,
        notes="Principal para crypto. P2P interno con buen spread.",
        reliability_score=95,
    ),
    PayoutMethod(
        id="lemon_cash",
        name="Lemon Cash",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam", "Gitcoin"],
        fees={"fixed": 0.5, "percentage": 0.5, "withdrawal": 1.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["USDC(Polygon) → Lemon → ARS", "USDT → Lemon → ARS"],
        pros=["100% argentino", "CVU integrado", "Buen tipo de cambio", "App moderna"],
        cons=["Limites mensuales", "Menos liquidez que Binance"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=50000.0,
        notes="Excelente para retiros directos a CVU.",
        reliability_score=90,
    ),
    PayoutMethod(
        id="buenbit",
        name="Buenbit",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam", "Gitcoin"],
        fees={"fixed": 0.0, "percentage": 0.5, "withdrawal": 0.5},
        timing={"setup": 1, "transfer": 0, "arrival": 2},
        routes=["USDC(Polygon) → Buenbit → ARS", "USDT → Buenbit → ARS"],
        pros=["El más antiguo de AR", "Muy confiable", "Buen spread"],
        cons=["Interface menos moderna", "Menos criptos"],
        minimum_withdrawal=20.0,
        maximum_withdrawal=100000.0,
        notes="Opción sólida y probada.",
        reliability_score=88,
    ),
    PayoutMethod(
        id="ripio",
        name="Ripio",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam", "Gitcoin"],
        fees={"fixed": 1.0, "percentage": 0.75, "withdrawal": 1.5},
        timing={"setup": 1, "transfer": 0, "arrival": 2},
        routes=["USDC(Polygon) → Ripio → ARS", "USDT → Ripio → ARS"],
        pros=["Buen soporte AR", "Varias criptos", "CVU disponible"],
        cons=["Comisiones más altas", "Interface compleja"],
        minimum_withdrawal=15.0,
        maximum_withdrawal=50000.0,
        notes="Buen fallback si otros fallan.",
        reliability_score=82,
    ),
    PayoutMethod(
        id="belo",
        name="Belo",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam"],
        fees={"fixed": 0.5, "percentage": 0.5, "withdrawal": 1.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["USDC(Polygon) → Belo → ARS", "USDT → Belo → ARS"],
        pros=["Interface moderna", "Buen tipo de cambio", "CVU"],
        cons=["Menos conocido", "Menos liquidez"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=30000.0,
        notes="Buena alternativa moderna.",
        reliability_score=80,
    ),
    PayoutMethod(
        id="fiwind",
        name="Fiwind",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam"],
        fees={"fixed": 0.0, "percentage": 0.3, "withdrawal": 0.5},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["USDC(Polygon) → Fiwind → ARS"],
        pros=["Bajas comisiones", "Buen spread", "Rápido"],
        cons=["Solo USDC", "Menos liquidez"],
        minimum_withdrawal=20.0,
        maximum_withdrawal=20000.0,
        notes="Especializado en USDC, muy eficiente.",
        reliability_score=78,
    ),
    PayoutMethod(
        id="cryptomkt",
        name="CryptoMKT",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam"],
        fees={"fixed": 0.5, "percentage": 0.5, "withdrawal": 1.0},
        timing={"setup": 1, "transfer": 0, "arrival": 2},
        routes=["USDC(Polygon) → CryptoMKT → ARS"],
        pros=["Soporte LatAm", "Buen spread", "Confiable"],
        cons=["Menos criptos", "Interface básica"],
        minimum_withdrawal=15.0,
        maximum_withdrawal=30000.0,
        notes="Buen opción regional.",
        reliability_score=75,
    ),
    PayoutMethod(
        id="metamask_p2p",
        name="MetaMask + P2P",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.BASIC,
        platforms=["Opire", "Algora", "Superteam", "Gitcoin", "Code4rena"],
        fees={"fixed": 0.0, "percentage": 1.0, "withdrawal": 2.0},
        timing={"setup": 0, "transfer": 0, "arrival": 1},
        routes=["USDC(Polygon) → MetaMask → P2P (Binance/Lemon) → ARS"],
        pros=["Sin registro centralizado", "Control total", "Gratuito"],
        cons=["Requiere conocimiento crypto", "Riesgo P2P", "Más pasos"],
        minimum_withdrawal=1.0,
        maximum_withdrawal=None,
        notes="Para usuarios avanzados en crypto.",
        reliability_score=70,
    ),
    PayoutMethod(
        id="trust_wallet",
        name="Trust Wallet",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.NONE,
        platforms=["Opire", "Algora", "Superteam", "Gitcoin"],
        fees={"fixed": 0.0, "percentage": 0.5, "withdrawal": 2.0},
        timing={"setup": 0, "transfer": 0, "arrival": 1},
        routes=["USDC(Polygon) → Trust Wallet → CEX → ARS"],
        pros=["Wallet móvil", "Seguro", "Sin KYC wallet"],
        cons=["Requiere CEX para ARS", "Gas fees"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=None,
        notes="Wallet móvil excelente, necesita CEX para salir a ARS.",
        reliability_score=85,
    ),
    # ===== FINTECH METHODS =====
    PayoutMethod(
        id="paypal_ar",
        name="PayPal Argentina",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Upwork", "Freelancer", "Fiverr", "GitHub Sponsors"],
        fees={"fixed": 0.30, "percentage": 2.9, "withdrawal": 5.0},
        timing={"setup": 2, "transfer": 3, "arrival": 5},
        routes=["Plataforma → PayPal → Banco AR (USD) → ARS"],
        pros=["Universalmente aceptado", "Protección comprador", "Fácil"],
        cons=["Comisiones altas", "Tipo de cambio malo", "Lento"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=10000.0,
        notes="Solo para plataformas que no soportan mejores métodos.",
        reliability_score=75,
    ),
    PayoutMethod(
        id="wise_ar",
        name="Wise (TransferWise)",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Upwork", "Freelancer", "Fiverr", "Stripe", "GitHub Sponsors"],
        fees={"fixed": 0.0, "percentage": 0.5, "withdrawal": 2.0},
        timing={"setup": 2, "transfer": 2, "arrival": 3},
        routes=["Plataforma → Wise → Banco AR (USD) → ARS"],
        pros=["Mejor tipo de cambio", "Transparencia", "Rápido"],
        cons=["Requiere cuenta bancaria", "Setup más complejo"],
        minimum_withdrawal=50.0,
        maximum_withdrawal=1000000.0,
        notes="Excelente para transferencias internacionales.",
        reliability_score=92,
    ),
    PayoutMethod(
        id="payoneer_ar",
        name="Payoneer",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["HackerOne", "Intigriti", "Immunefi", "Upwork", "Freelancer"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 15.0},
        timing={"setup": 3, "transfer": 3, "arrival": 7},
        routes=["Plataforma → Payoneer → Banco AR / USDT"],
        pros=["Soporte nativo AR", "Compatible todo bounty", "Histórico probado"],
        cons=["Comisiones retiro altas", "Lento", "Tipo de cambio regular"],
        minimum_withdrawal=20.0,
        maximum_withdrawal=50000.0,
        notes="Método clásico para bug bounty, muy confiable.",
        reliability_score=90,
    ),
    PayoutMethod(
        id="airtm",
        name="AirTM",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Outlier", "DataAnnotation", "Mindrift", "Remotasks"],
        fees={"fixed": 0.0, "percentage": 1.0, "withdrawal": 2.0},
        timing={"setup": 2, "transfer": 1, "arrival": 3},
        routes=["Plataforma → AirTM → USDT/ARS"],
        pros=["Diseñado LatAm", "Soporta múltiples salidas", "Buen cambio"],
        cons=["Comisiones medias", "Menos liquidez"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=10000.0,
        notes="Ideal para data annotation platforms.",
        reliability_score=85,
    ),
    PayoutMethod(
        id=" MercadoPago_ar",
        name="MercadoPago",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["GitHub Sponsors", "Algunas plataformas locales"],
        fees={"fixed": 0.0, "percentage": 2.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → MercadoPago → ARS directo"],
        pros=["100% AR", "Retiro instantáneo", "Onipresente"],
        cons=["Solo plataformas específicas", "Comisiones altas"],
        minimum_withdrawal=1.0,
        maximum_withdrawal=50000.0,
        notes="Excelente cuando está disponible.",
        reliability_score=95,
    ),
    PayoutMethod(
        id="mpago",
        name="Ualá",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["GitHub Sponsors", "Algunas fintech locales"],
        fees={"fixed": 0.0, "percentage": 1.5, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → Ualá → ARS directo"],
        pros=["App moderna", "Buen soporte", "CVU"],
        cons=["Pocas plataformas lo soportan"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=20000.0,
        notes="Buena alternativa local.",
        reliability_score=80,
    ),
    PayoutMethod(
        id="nubi",
        name="Nubi",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["GitHub Sponsors", "Algunas fintech"],
        fees={"fixed": 0.0, "percentage": 1.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → Nubi → ARS directo"],
        pros=["Sin comisiones", "CVU", "App simple"],
        cons=["Poco conocido", "Limitado en plataformas"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=15000.0,
        notes="Opción gratuita, buen complemento.",
        reliability_score=72,
    ),
    PayoutMethod(
        id="prex",
        name="Prex",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["GitHub Sponsors", "Algunas fintech"],
        fees={"fixed": 0.0, "percentage": 1.5, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → Prex → ARS directo"],
        pros=["Tarjeta prepago", "Buenas promociones", "CVU"],
        cons=["Comisiones medias", "Limitado"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=20000.0,
        notes="Bueno para gastos directos.",
        reliability_score=78,
    ),
    PayoutMethod(
        id="modo",
        name="Modo",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["GitHub Sponsors", "Algunas fintech"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → Modo → ARS directo"],
        pros=["100% gratuito", "CVU", "Bancolombia"],
        cons=["Solo algunas plataformas", "Menos conocido"],
        minimum_withdrawal=1.0,
        maximum_withdrawal=10000.0,
        notes="Opción gratuita excelente.",
        reliability_score=75,
    ),
    PayoutMethod(
        id="dlocal",
        name="dLocal",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas internacionales"],
        fees={"fixed": 1.0, "percentage": 2.0, "withdrawal": 1.0},
        timing={"setup": 2, "transfer": 2, "arrival": 3},
        routes=["Plataforma → dLocal → Banco AR"],
        pros=["Soporte LatAm", "Múltiples bancos", "Confiabilidad"],
        cons=["Comisiones altas", "Pocas plataformas"],
        minimum_withraft=20.0,
        maximum_withdrawal=50000.0,
        notes="Buen gateway regional.",
        reliability_score=80,
    ),
    # ===== TRADITIONAL BANK METHODS =====
    PayoutMethod(
        id="swift_ar",
        name="SWIFT Transfer",
        type=PayoutMethodType.TRADITIONAL,
        kyc_level=KYCLevel.ADVANCED,
        platforms=["HackerOne", "Intigriti", "Immunefi", "Stripe", "GitHub Sponsors"],
        fees={"fixed": 30.0, "percentage": 0.0, "withdrawal": 15.0},
        timing={"setup": 5, "transfer": 5, "arrival": 10},
        routes=["Plataforma → Banco extranjero → SWIFT → Banco AR (USD)"],
        pros=["Funciona con todo", "Seguro", "Sin límites"],
        cons=["Comisiones muy altas", "Muy lento", "Papeleo"],
        minimum_withdrawal=100.0,
        maximum_withdrawal=None,
        notes="Último recurso, solo para montos grandes.",
        reliability_score=70,
    ),
    PayoutMethod(
        id="wise_bank",
        name="Wise to Bank AR",
        type=PayoutMethodType.TRADITIONAL,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Upwork", "Freelancer", "Fiverr", "Stripe"],
        fees={"fixed": 0.0, "percentage": 0.5, "withdrawal": 2.0},
        timing={"setup": 2, "transfer": 2, "arrival": 3},
        routes=["Plataforma → Wise → Banco AR (USD directo)"],
        pros=["Mejor tipo de cambio bancario", "Transparente", "Rápido"],
        cons=["Requiere cuenta bancaria", "Setup complejo"],
        minimum_withdrawal=50.0,
        maximum_withdrawal=1000000.0,
        notes="Mejor opción bancaria tradicional.",
        reliability_score=90,
    ),
    PayoutMethod(
        id="galicia_intl",
        name="Banco Galicia Internacional",
        type=PayoutMethodType.TRADITIONAL,
        kyc_level=KYCLevel.ADVANCED,
        platforms=["HackerOne", "Intigriti", "Algunas plataformas"],
        fees={"fixed": 15.0, "percentage": 0.5, "withdrawal": 0.0},
        timing={"setup": 7, "transfer": 3, "arrival": 5},
        routes=["Plataforma → Cuenta USD Galicia → ARS"],
        pros=["Banco tradicional AR", "Seguro", "Confiable"],
        cons=["Requiere cuenta USD", "Papeleo", "Comisiones"],
        minimum_withdrawal=100.0,
        maximum_withdrawal=100000.0,
        notes="Solo si ya tenés cuenta USD.",
        reliability_score=85,
    ),
    PayoutMethod(
        id="santander_intl",
        name="Santander Internacional",
        type=PayoutMethodType.TRADITIONAL,
        kyc_level=KYCLevel.ADVANCED,
        platforms=["HackerOne", "Intigriti", "Algunas plataformas"],
        fees={"fixed": 20.0, "percentage": 0.5, "withdrawal": 0.0},
        timing={"setup": 7, "transfer": 3, "arrival": 5},
        routes=["Plataforma → Cuenta USD Santander → ARS"],
        pros=["Banco grande", "Seguro", "Red amplia"],
        cons=["Requiere cuenta USD", "Papeleo", "Comisiones"],
        minimum_withdrawal=100.0,
        maximum_withdrawal=100000.0,
        notes="Similar a Galicia, solo si tenés cuenta.",
        reliability_score=82,
    ),
    PayoutMethod(
        id="bbva_intl",
        name="BBVA Francés Internacional",
        type=PayoutMethodType.TRADITIONAL,
        kyc_level=KYCLevel.ADVANCED,
        platforms=["HackerOne", "Intigriti", "Algunas plataformas"],
        fees={"fixed": 15.0, "percentage": 0.5, "withdrawal": 0.0},
        timing={"setup": 7, "transfer": 3, "arrival": 5},
        routes=["Plataforma → Cuenta USD BBVA → ARS"],
        pros=["Banco con buena red", "Seguro"],
        cons=["Requiere cuenta USD", "Proceso lento"],
        minimum_withdrawal=100.0,
        maximum_withdrawal=100000.0,
        notes="Buen banco tradicional.",
        reliability_score=80,
    ),
    # ===== REMITTANCE SERVICES =====
    PayoutMethod(
        id="western_union",
        name="Western Union",
        type=PayoutMethodType.REMITTANCE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas específicas"],
        fees={"fixed": 5.0, "percentage": 3.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["Plataforma → Western Union → Retiro en ARS"],
        pros=["Retiro inmediato", "Muchas sucursales", "Confiable"],
        cons=["Comisiones muy altas", "Mal tipo de cambio"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=5000.0,
        notes="Solo para emergencias o montos pequeños.",
        reliability_score=85,
    ),
    PayoutMethod(
        id="moneygram",
        name="MoneyGram",
        type=PayoutMethodType.REMITTANCE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas específicas"],
        fees={"fixed": 5.0, "percentage": 3.5, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["Plataforma → MoneyGram → Retiro en ARS"],
        pros=["Retiro rápido", "Buenas sucursales"],
        cons=["Comisiones altas", "Menos sucursales que WU"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=3000.0,
        notes="Alternativa a Western Union.",
        reliability_score=80,
    ),
    PayoutMethod(
        id="ria_money_transfer",
        name="Ria Money Transfer",
        type=PayoutMethodType.REMITTANCE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas específicas"],
        fees={"fixed": 4.0, "percentage": 3.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["Plataforma → Ria → Retiro en ARS"],
        pros=["Buen tipo de cambio", "Rápido"],
        cons=["Menos sucursales", "Menos conocido"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=3000.0,
        notes="Buen alternativa regional.",
        reliability_score=75,
    ),
    PayoutMethod(
        id="worldremit",
        name="WorldRemit",
        type=PayoutMethodType.REMITTANCE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas específicas"],
        fees={"fixed": 3.0, "percentage": 2.5, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["Plataforma → WorldRemit → Retiro en ARS"],
        pros=["Digital", "Buen tipo de cambio", "Rápido"],
        cons=["Comisiones medias", "Menos conocido"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=5000.0,
        notes="Buena opción digital.",
        reliability_score=78,
    ),
    PayoutMethod(
        id="remitly",
        name="Remitly",
        type=PayoutMethodType.REMITTANCE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas específicas"],
        fees={"fixed": 3.0, "percentage": 2.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["Plataforma → Remitly → Retiro en ARS"],
        pros=["Buen tipo de cambio", "Express disponible"],
        cons=["Solo digital", "Comisiones medias"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=5000.0,
        notes="Buen para envíos rápidos.",
        reliability_score=80,
    ),
    PayoutMethod(
        id="xoom",
        name="Xoom (PayPal)",
        type=PayoutMethodType.REMITTANCE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas específicas"],
        fees={"fixed": 4.0, "percentage": 2.5, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["Plataforma → Xoom → Retiro en ARS"],
        pros=["PayPal respaldo", "Buen tipo de cambio"],
        cons=["Comisiones medias", "Menos opciones"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=10000.0,
        notes="Buen respaldo de PayPal.",
        reliability_score=82,
    ),
    # ===== CRYPTO MARKETPLACES (P2P) =====
    PayoutMethod(
        id="binance_p2p",
        name="Binance P2P",
        type=PayoutMethodType.MARKETPLACE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Todas las plataformas que pagan crypto"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["USDC/USDT → Binance P2P → Transferencia bancaria AR"],
        pros=["Tipo de cambio mercado", "Sin comisiones", "Rápido"],
        cons=["Requiere patience", "Riesgo contraparte", "Necesita KYC Binance"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=50000.0,
        notes="Mejor tipo de cambio, requiere patience.",
        reliability_score=88,
    ),
    PayoutMethod(
        id="bybit_p2p",
        name="Bybit P2P",
        type=PayoutMethodType.MARKETPLACE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Todas las plataformas que pagan crypto"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["USDC/USDT → Bybit P2P → Transferencia bancaria AR"],
        pros=["Buen spread", "Interface moderna", "Rápido"],
        cons=["Menos liquidez que Binance", "Necesita KYC"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=30000.0,
        notes="Buena alternativa a Binance P2P.",
        reliability_score=82,
    ),
    PayoutMethod(
        id="kucoin_p2p",
        name="KuCoin P2P",
        type=PayoutMethodType.MARKETPLACE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Todas las plataformas que pagan crypto"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["USDC/USDT → KuCoin P2P → Transferencia bancaria AR"],
        pros=["Buen spread", "Variedad de métodos"],
        cons=["Menos liquidez", "Interface compleja"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=20000.0,
        notes="Opción decente de P2P.",
        reliability_score=75,
    ),
    PayoutMethod(
        id="okx_p2p",
        name="OKX P2P",
        type=PayoutMethodType.MARKETPLACE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Todas las plataformas que pagan crypto"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["USDC/USDT → OKX P2P → Transferencia bancaria AR"],
        pros=["Buen spread", "Interface profesional"],
        cons=["Menos liquidez", "Más complejo"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=25000.0,
        notes="Opción profesional de P2P.",
        reliability_score=78,
    ),
    PayoutMethod(
        id="huobi_p2p",
        name="Huobi P2P",
        type=PayoutMethodType.MARKETPLACE,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Todas las plataformas que pagan crypto"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 0, "arrival": 1},
        routes=["USDC/USDT → Huobi P2P → Transferencia bancaria AR"],
        pros=["Buen spread", "Variedad de opciones"],
        cons=["Menos liquidez", "Interface china"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=20000.0,
        notes="Opción asiática decente.",
        reliability_score=72,
    ),
    PayoutMethod(
        id="localbitcoins",
        name="LocalBitcoins",
        type=PayoutMethodType.MARKETPLACE,
        kyc_level=KYCLevel.BASIC,
        platforms=["Todas las plataformas que pagan crypto"],
        fees={"fixed": 0.0, "percentage": 1.0, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 1},
        routes=["BTC → LocalBitcoins → Transferencia AR"],
        pros=["P2P original", "Sin KYC wallet", "Flexible"],
        cons=["Comisiones altas", "Riesgo alto", "BTC volátil"],
        minimum_withdrawal=1.0,
        maximum_withdrawal=None,
        notes="Solo para usuarios avanzados.",
        reliability_score=65,
    ),
    PayoutMethod(
        id="paxful",
        name="Paxful",
        type=PayoutMethodType.MARKETPLACE,
        kyc_level=KYCLevel.BASIC,
        platforms=["Todas las plataformas que pagan crypto"],
        fees={"fixed": 0.0, "percentage": 1.0, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 1},
        routes=["USDT/BTC → Paxful → Transferencia AR"],
        pros=["Muchos métodos de pago", "Flexible"],
        cons=["Comisiones altas", "Riesgo medio", "Menos liquidez"],
        minimum_withdrawal=1.0,
        maximum_withdrawal=None,
        notes="Opción P2P flexible.",
        reliability_score=68,
    ),
    PayoutMethod(
        id="hodl_hodl",
        name="Hodl Hodl",
        type=PayoutMethodType.MARKETPLACE,
        kyc_level=KYCLevel.BASIC,
        platforms=["Todas las plataformas que pagan crypto"],
        fees={"fixed": 0.0, "percentage": 0.5, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 1},
        routes=["BTC → Hodl Hodl → Transferencia AR"],
        pros=["Sin KYC", "Bajas comisiones", "Escrow seguro"],
        cons=["Solo BTC", "Menos liquidez", "Lento"],
        minimum_withdrawal=1.0,
        maximum_withdrawal=None,
        notes="Para privacidad máxima.",
        reliability_score=70,
    ),
    # ===== GIFT CARDS & VOUCHERS =====
    PayoutMethod(
        id="amazon_giftcard",
        name="Amazon Gift Cards",
        type=PayoutMethodType.GIFT_CARD,
        kyc_level=KYCLevel.NONE,
        platforms=["Algunas plataformas freelance", "GitHub Sponsors"],
        fees={"fixed": 0.0, "percentage": 15.0, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 0},
        routes=["Plataforma → Amazon Gift Card → Venta por ARS"],
        pros=["Sin KYC", "Universal", "Fácil"],
        cons=["Pérdida 15% valor", "Difícil vender", "Lento"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=500.0,
        notes="Solo último recurso, pérdidas altas.",
        reliability_score=60,
    ),
    PayoutMethod(
        id="steam_giftcard",
        name="Steam Gift Cards",
        type=PayoutMethodType.GIFT_CARD,
        kyc_level=KYCLevel.NONE,
        platforms=["Algunas plataformas gaming"],
        fees={"fixed": 0.0, "percentage": 20.0, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 0},
        routes=["Plataforma → Steam Gift Card → Venta por ARS"],
        pros=["Sin KYC", "Popular gaming"],
        cons=["Pérdida 20% valor", "Nicho mercado"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=200.0,
        notes="Solo para nicho gaming.",
        reliability_score=55,
    ),
    PayoutMethod(
        id="itunes_giftcard",
        name="iTunes Gift Cards",
        type=PayoutMethodType.GIFT_CARD,
        kyc_level=KYCLevel.NONE,
        platforms=["Algunas plataformas específicas"],
        fees={"fixed": 0.0, "percentage": 18.0, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 0},
        routes=["Plataforma → iTunes Gift Card → Venta por ARS"],
        pros=["Sin KYC", "Popular"],
        cons=["Pérdida 18% valor", "Mercado limitado"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=200.0,
        notes="Opción de gift card decente.",
        reliability_score=58,
    ),
    PayoutMethod(
        id="google_play_giftcard",
        name="Google Play Gift Cards",
        type=PayoutMethodType.GIFT_CARD,
        kyc_level=KYCLevel.NONE,
        platforms=["Algunas plataformas Android"],
        fees={"fixed": 0.0, "percentage": 17.0, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 0},
        routes=["Plataforma → Google Play Gift Card → Venta por ARS"],
        pros=["Sin KYC", "Android popular"],
        cons=["Pérdida 17% valor", "Mercado limitado"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=200.0,
        notes="Para usuarios Android.",
        reliability_score=57,
    ),
    PayoutMethod(
        id="playstation_giftcard",
        name="PlayStation Gift Cards",
        type=PayoutMethodType.GIFT_CARD,
        kyc_level=KYCLevel.NONE,
        platforms=["Algunas plataformas gaming"],
        fees={"fixed": 0.0, "percentage": 19.0, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 0},
        routes=["Plataforma → PS Gift Card → Venta por ARS"],
        pros=["Sin KYC", "Gaming popular"],
        cons=["Pérdida 19% valor", "Muy nicho"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=300.0,
        notes="Solo gamers PlayStation.",
        reliability_score=52,
    ),
    PayoutMethod(
        id="netflix_giftcard",
        name="Netflix Gift Cards",
        type=PayoutMethodType.GIFT_CARD,
        kyc_level=KYCLevel.NONE,
        platforms=["Algunas plataformas streaming"],
        fees={"fixed": 0.0, "percentage": 12.0, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 0},
        routes=["Plataforma → Netflix Gift Card → Venta por ARS"],
        pros=["Sin KYC", "Alta demanda", "Pérdida menor"],
        cons=["Mercado específico", "Pérdida 12%"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=200.0,
        notes="Buena opción de gift card.",
        reliability_score=62,
    ),
    PayoutMethod(
        id="spotify_giftcard",
        name="Spotify Gift Cards",
        type=PayoutMethodType.GIFT_CARD,
        kyc_level=KYCLevel.NONE,
        platforms=["Algunas plataformas music"],
        fees={"fixed": 0.0, "percentage": 10.0, "withdrawal": 0.0},
        timing={"setup": 0, "transfer": 0, "arrival": 0},
        routes=["Plataforma → Spotify Gift Card → Venta por ARS"],
        pros=["Sin KYC", "Alta demanda", "Pérdida menor"],
        cons=["Mercado específico", "Montos pequeños"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=100.0,
        notes="Buena para montos pequeños.",
        reliability_score=65,
    ),
    # ===== PREPAID CARDS =====
    PayoutMethod(
        id="payoneer_prepaid",
        name="Payoneer Prepaid Mastercard",
        type=PayoutMethodType.PREPAID,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Payoneer compatible"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 3.15},
        timing={"setup": 7, "transfer": 0, "arrival": 0},
        routes=["Payoneer → Tarjeta Prepaid → Gastos directos AR"],
        pros=["Gastos directos", "Sin conversión", "Worldwide"],
        cons=["Tarjeta física demora", "Comisiones ATM", "Anualidad"],
        minimum_withdrawal=1.0,
        maximum_withdrawal=10000.0,
        notes="Bueno para gastos directos en USD.",
        reliability_score=82,
    ),
    PayoutMethod(
        id="revolut",
        name="Revolut",
        type=PayoutMethodType.PREPAID,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Upwork", "Freelancer", "Fiverr", "GitHub Sponsors"],
        fees={"fixed": 0.0, "percentage": 0.5, "withdrawal": 2.0},
        timing={"setup": 3, "transfer": 2, "arrival": 3},
        routes=["Plataforma → Revolut → Banco AR"],
        pros=["Buen tipo de cambio", "App excelente", "Multi-moneda"],
        cons=["No disponible directo AR", "Requiere workaround"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=50000.0,
        notes="Excelente pero requiere workaround AR.",
        reliability_score=85,
    ),
    PayoutMethod(
        id="n26",
        name="N26",
        type=PayoutMethodType.PREPAID,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Upwork", "Freelancer", "Fiverr"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 2.0},
        timing={"setup": 5, "transfer": 2, "arrival": 5},
        routes=["Plataforma → N26 → Banco AR"],
        pros=["Banco digital", "Sin comisiones", "Excelente app"],
        cons=["No disponible directo AR", "Requiere residencia EU"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=50000.0,
        notes="Solo si tenés residencia EU.",
        reliability_score=80,
    ),
    PayoutMethod(
        id="monzo",
        name="Monzo",
        type=PayoutMethodType.PREPAID,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Upwork", "Freelancer", "Fiverr"],
        fees={"fixed": 0.0, "percentage": 0.0, "withdrawal": 2.0},
        timing={"setup": 5, "transfer": 2, "arrival": 5},
        routes=["Plataforma → Monzo → Banco AR"],
        pros=["Banco digital UK", "Excelente app"],
        cons=["No disponible directo AR", "Requiere residencia UK"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=50000.0,
        notes="Solo si tenés residencia UK.",
        reliability_score=78,
    ),
    # ===== ARGENTINA-SPECIFIC METHODS =====
    PayoutMethod(
        id="takenos",
        name="Tikeknos",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas fintech locales"],
        fees={"fixed": 0.0, "percentage": 1.5, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → Tikeknos → ARS directo"],
        pros=["100% argentino", "CVU", "Retiro rápido"],
        cons=["Pocas plataformas", "Menos conocido"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=20000.0,
        notes="Fintech local emergente.",
        reliability_score=72,
    ),
    PayoutMethod(
        id="arq_dolarapp",
        name="ARQ (DolarApp)",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas fintech"],
        fees={"fixed": 0.0, "percentage": 1.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → ARQ → ARS directo"],
        pros=["Buen tipo de cambio", "CVU", "Rápido"],
        cons=["Pocas plataformas", "Reciente"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=30000.0,
        notes="Fintech local con buen potencial.",
        reliability_score=75,
    ),
    PayoutMethod(
        id="dolarapi",
        name="DolarAPI",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas fintech"],
        fees={"fixed": 0.0, "percentage": 0.5, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → DolarAPI → ARS directo"],
        pros=["API excelente", "Buen tipo de cambio", "CVU"],
        cons=["Más para devs", "Pocas plataformas"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=50000.0,
        notes="Excelente para integraciones técnicas.",
        reliability_score=78,
    ),
    PayoutMethod(
        id="belu_ar",
        name="Belu",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas fintech"],
        fees={"fixed": 0.0, "percentage": 1.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → Belu → ARS directo"],
        pros=["Fintech local", "CVU", "App simple"],
        cons=["Poco conocido", "Limitado"],
        minimum_withdrawal=5.0,
        maximum_withdrawal=15000.0,
        notes="Fintech local simple.",
        reliability_score=70,
    ),
    PayoutMethod(
        id="yaven",
        name="Yaven",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas fintech"],
        fees={"fixed": 0.0, "percentage": 1.2, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → Yaven → ARS directo"],
        pros=["Fintech local", "CVU", "Buen soporte"],
        cons=["Menos conocido", "Limitado"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=20000.0,
        notes="Fintech local con buen soporte.",
        reliability_score=73,
    ),
    PayoutMethod(
        _id="brubank",
        name="Brubank",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas fintech"],
        fees={"fixed": 0.0, "percentage": 1.0, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → Brubank → ARS directo"],
        pros=["Banco digital 100% AR", "CVU", "Buen spread"],
        cons=["Pocas plataformas", "App básica"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=30000.0,
        notes="Banco digital confiable.",
        reliability_score=80,
    ),
    PayoutMethod(
        id="rebanking",
        name="Rebanking",
        type=PayoutMethodType.FINTECH,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Algunas plataformas fintech"],
        fees={"fixed": 0.0, "percentage": 0.8, "withdrawal": 0.0},
        timing={"setup": 1, "transfer": 1, "arrival": 1},
        routes=["Plataforma → Rebanking → ARS directo"],
        pros=["Fintech local", "Buen tipo de cambio", "CVU"],
        cons=["Menos conocido", "Limitado"],
        minimum_withdrawal=10.0,
        maximum_withdrawal=25000.0,
        notes="Fintech local con buen spread.",
        reliability_score=76,
    ),
    PayoutMethod(
        id="letsbit",
        name="LetsBit",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam"],
        fees={"fixed": 0.5, "percentage": 0.6, "withdrawal": 1.0},
        timing={"setup": 1, "transfer": 0, "arrival": 2},
        routes=["USDC(Polygon) → LetsBit → ARS"],
        pros=["100% argentino", "Buen spread", "CVU"],
        cons=["Menos liquidez", "App básica"],
        minimum_withdrawal=15.0,
        maximum_withdrawal=20000.0,
        notes="CEX argentino decente.",
        reliability_score=74,
    ),
    PayoutMethod(
        id="crypto_buy",
        name="CryptoBuy",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam"],
        fees={"fixed": 1.0, "percentage": 0.8, "withdrawal": 1.5},
        timing={"setup": 1, "transfer": 0, "arrival": 2},
        routes=["USDC(Polygon) → CryptoBuy → ARS"],
        pros=["100% argentino", "Buen soporte"],
        cons=["Comisiones más altas", "Menos liquidez"],
        minimum_withdrawal=20.0,
        maximum_withdrawal=15000.0,
        notes="CEX argentino con buen soporte.",
        reliability_score=71,
    ),
    PayoutMethod(
        id="argenbtc",
        name="ArgenBTC",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam"],
        fees={"fixed": 0.5, "percentage": 0.7, "withdrawal": 1.0},
        timing={"setup": 1, "transfer": 0, "arrival": 2},
        routes=["USDC(Polygon) → ArgenBTC → ARS"],
        pros=["100% argentino", "Buen spread BTC"],
        cons=["Enfocado BTC", "Menos USDC"],
        minimum_withdrawal=15.0,
        maximum_withdrawal=10000.0,
        notes="Bueno si preferís BTC.",
        reliability_score=73,
    ),
    PayoutMethod(
        id="tiendacrypto",
        name="TiendaCrypto",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam"],
        fees={"fixed": 1.0, "percentage": 0.9, "withdrawal": 1.5},
        timing={"setup": 1, "transfer": 0, "arrival": 2},
        routes=["USDC(Polygon) → TiendaCrypto → ARS"],
        pros=["100% argentino", "Buen soporte"],
        cons=["Comisiones altas", "Interface vieja"],
        minimum_withdrawal=20.0,
        maximum_withdrawal=15000.0,
        notes="CEX argentino tradicional.",
        reliability_score=70,
    ),
    PayoutMethod(
        id="bitso",
        name="Bitso",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam"],
        fees={"fixed": 0.5, "percentage": 0.5, "withdrawal": 1.0},
        timing={"setup": 1, "transfer": 0, "arrival": 2},
        routes=["USDC(Polygon) → Bitso → ARS"],
        pros=["Mexicano pero soporta AR", "Buen spread", "Confiable"],
        cons=["No 100% AR", "Comisiones"],
        minimum_withdrawal=15.0,
        maximum_withdrawal=20000.0,
        notes="Opción regional sólida.",
        reliability_score=77,
    ),
    PayoutMethod(
        id="foxbit",
        name="FoxBit",
        type=PayoutMethodType.CRYPTO,
        kyc_level=KYCLevel.STANDARD,
        platforms=["Opire", "Algora", "Superteam"],
        fees={"fixed": 0.5, "percentage": 0.6, "withdrawal": 1.0},
        timing={"setup": 1, "transfer": 0, "arrival": 2},
        routes=["USDC(Polygon) → FoxBit → ARS"],
        pros=["Brasileño pero soporta AR", "Buen spread"],
        cons=["No 100% AR", "Menos liquidez"],
        minimum_withdrawal=15.0,
        maximum_withdrawal=15000.0,
        notes="Opción regional decente.",
        reliability_score=72,
    ),
]


class ArgentinaPayoutMethods:
    """Argentina payout methods database and recommendation engine."""

    def __init__(self, data_dir: str = ""):
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/argentina_payout/")
        os.makedirs(self.data_dir, exist_ok=True)
        self._methods_cache = None

    @property
    def state_path(self) -> str:
        return os.path.join(self.data_dir, "state.json")

    def _load_state(self) -> dict:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"configured_methods": [], "preferences": {}}

    def _save_state(self, state: dict) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def get_all_methods(self) -> list[PayoutMethod]:
        """Get all available payout methods."""
        if self._methods_cache is None:
            self._methods_cache = ARGENTINA_PAYOUT_METHODS
        return self._methods_cache

    def get_methods_by_type(self, method_type: PayoutMethodType) -> list[PayoutMethod]:
        """Get methods filtered by type."""
        return [m for m in self.get_all_methods() if m.type == method_type]

    def get_methods_by_platform(self, platform: str) -> list[PayoutMethod]:
        """Get methods compatible with a specific platform."""
        return [m for m in self.get_all_methods() if platform.lower() in [p.lower() for p in m.platforms]]

    def get_methods_by_kyc_level(self, kyc_level: KYCLevel) -> list[PayoutMethod]:
        """Get methods filtered by KYC level."""
        return [m for m in self.get_all_methods() if m.kyc_level == kyc_level]

    def recommend_for_platform(
        self,
        platform: str,
        amount: float,
        preferred_type: PayoutMethodType | None = None,
        max_kyc: KYCLevel = KYCLevel.STANDARD,
    ) -> list[PayoutMethod]:
        """Recommend best payout methods for a specific platform and amount.

        Args:
            platform: Platform name (e.g., "HackerOne", "Outlier")
            amount: Amount to withdraw in USD
            preferred_type: Preferred method type (optional)
            max_kyc: Maximum KYC level willing to complete

        Returns:
            List of recommended methods sorted by score
        """
        compatible = self.get_methods_by_platform(platform)

        # Filter by KYC level
        kyc_order = [KYCLevel.NONE, KYCLevel.BASIC, KYCLevel.STANDARD, KYCLevel.ADVANCED]
        max_kyc_index = kyc_order.index(max_kyc)
        compatible = [m for m in compatible if kyc_order.index(m.kyc_level) <= max_kyc_index]

        # Filter by preferred type
        if preferred_type:
            compatible = [m for m in compatible if m.type == preferred_type]

        # Filter by amount limits
        compatible = [
            m
            for m in compatible
            if m.minimum_withdrawal <= amount and (m.maximum_withdrawal is None or m.maximum_withdrawal >= amount)
        ]

        # Score each method
        scored = []
        for method in compatible:
            score = self._calculate_score(method, amount)
            scored.append((score, method))

        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)

        return [method for score, method in scored]

    def _calculate_score(self, method: PayoutMethod, amount: float) -> float:
        """Calculate recommendation score for a method.

        Higher score = better recommendation.
        Score factors: reliability, fees, timing, suitability for amount.
        """
        score = 0.0

        # Reliability (40% weight)
        score += method.reliability_score * 0.4

        # Fees (25% weight) - lower is better
        total_fee_pct = method.fees.get("percentage", 0) + (
            method.fees.get("fixed", 0) / amount * 100 if amount > 0 else 0
        )
        fee_score = max(0, 100 - total_fee_pct * 10)  # Penalize high fees
        score += fee_score * 0.25

        # Timing (20% weight) - faster is better
        total_days = method.timing.get("setup", 0) + method.timing.get("transfer", 0) + method.timing.get("arrival", 0)
        timing_score = max(0, 100 - total_days * 5)  # Penalize slow methods
        score += timing_score * 0.2

        # Suitability for amount (15% weight)
        if method.maximum_withdrawal:
            amount_ratio = amount / method.maximum_withdrawal
            # Sweet spot: 10-50% of max
            if 0.1 <= amount_ratio <= 0.5:
                suitability_score = 100
            elif amount_ratio < 0.1:
                suitability_score = 70  # Too small
            else:
                suitability_score = 50  # Too large
        else:
            suitability_score = 80  # No limit is okay
        score += suitability_score * 0.15

        return score

    def get_method_details(self, method_id: str) -> PayoutMethod | None:
        """Get detailed information about a specific method."""
        for method in self.get_all_methods():
            if method.id == method_id:
                return method
        return None

    def mark_configured(self, method_id: str) -> dict:
        """Mark a payout method as configured by the user."""
        method = self.get_method_details(method_id)
        if not method:
            return {"success": False, "message": "Method not found"}

        state = self._load_state()
        configured = set(state.get("configured_methods", []))
        configured.add(method_id)
        state["configured_methods"] = sorted(configured)
        self._save_state(state)

        return {"success": True, "configured_methods": state["configured_methods"]}

    def get_configured_methods(self) -> list[PayoutMethod]:
        """Get all methods configured by the user."""
        state = self._load_state()
        configured_ids = state.get("configured_methods", [])
        return [self.get_method_details(mid) for mid in configured_ids if self.get_method_details(mid)]

    def get_statistics(self) -> dict:
        """Get statistics about available methods."""
        methods = self.get_all_methods()

        by_type = {}
        for method_type in PayoutMethodType:
            by_type[method_type.value] = len(self.get_methods_by_type(method_type))

        by_kyc = {}
        for kyc_level in KYCLevel:
            by_kyc[kyc_level.value] = len(self.get_methods_by_kyc_level(kyc_level))

        avg_reliability = sum(m.reliability_score for m in methods) / len(methods) if methods else 0

        return {
            "total_methods": len(methods),
            "by_type": by_type,
            "by_kyc": by_kyc,
            "average_reliability": round(avg_reliability, 1),
            "configured_count": len(self.get_configured_methods()),
        }


# Singleton instance
_payout_methods: ArgentinaPayoutMethods | None = None


def get_argentina_payout_methods() -> ArgentinaPayoutMethods:
    """Get the singleton ArgentinaPayoutMethods instance."""
    global _payout_methods
    if _payout_methods is None:
        _payout_methods = ArgentinaPayoutMethods()
    return _payout_methods
