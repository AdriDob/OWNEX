"""OWNEX Payment Network — curated catalog of payment accounts.

The network is organized in layers (banking, processors, crypto,
self-custody, withdrawal) and each account has a functional role
(primary, us_account, global, payout, local, backup, specialized).

The catalog is the single source of truth for which accounts OWNEX
can actually use to receive, hold and withdraw money. Accounts that
already exist in ``ARGENTINA_PAYOUT_METHODS`` reference that catalog
(``payout_ref``) instead of duplicating fee/kyc details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PaymentLayer(Enum):
    """Architectural layers of the payment network."""

    BANKING = "banking"
    PROCESSORS = "processors"
    CRYPTO = "crypto"
    SELF_CUSTODY = "self_custody"
    WITHDRAWAL = "withdrawal"


class PaymentFunction(Enum):
    """Functional role of an account within the network."""

    PRIMARY = "primary"
    US_ACCOUNT = "us_account"
    GLOBAL = "global"
    PAYOUT = "payout"
    LOCAL = "local"
    BACKUP = "backup"
    SPECIALIZED = "specialized"


class Region(Enum):
    """Jurisdictions OWNEX operates in."""

    USA = "usa"
    ARGENTINA = "argentina"
    EU = "eu"
    GLOBAL = "global"


class Network(Enum):
    """Blockchain networks for crypto settlements."""

    BASE = "base"
    POLYGON = "polygon"
    ETHEREUM = "ethereum"
    SOLANA = "solana"
    BSC = "bsc"
    TRON = "tron"
    ARBITRUM = "arbitrum"


@dataclass
class OwnAccount:
    """An account OWNEX can use to receive, hold or withdraw funds."""

    id: str
    name: str
    layer: PaymentLayer
    function: PaymentFunction
    regions: list[Region]
    currencies: list[str]
    methods: list[str] = field(default_factory=list)
    networks: list[Network] = field(default_factory=list)
    kyc_required: bool = True
    withdrawal_available: bool = True
    notes: str = ""
    payout_ref: str = ""  # id in ARGENTINA_PAYOUT_METHODS when available

    def matches_method(self, method: str) -> bool:
        return method.lower() in {m.lower() for m in self.methods}

    def matches_region(self, region: str) -> bool:
        region_l = region.lower()
        if region_l == "global":
            return True
        return region_l in {r.value for r in self.regions}


def _ac(
    id: str,
    name: str,
    layer: PaymentLayer,
    function: PaymentFunction,
    regions: list[Region],
    currencies: list[str],
    methods: list[str],
    networks: list[Network] | None = None,
    kyc: bool = True,
    withdrawal: bool = True,
    notes: str = "",
    payout_ref: str = "",
) -> OwnAccount:
    """Compact constructor for the curated catalog."""
    return OwnAccount(
        id=id,
        name=name,
        layer=layer,
        function=function,
        regions=regions,
        currencies=currencies,
        methods=methods,
        networks=networks or [],
        kyc_required=kyc,
        withdrawal_available=withdrawal,
        notes=notes,
        payout_ref=payout_ref,
    )


# =====================================================================
# Core settlement nucleus (the 10 accounts the owner prioritizes)
# =====================================================================
PAYMENT_NETWORK: list[OwnAccount] = [
    # ---- BANKING: US receiving ----
    _ac(
        "grabrfi",
        "GrabrFi",
        PaymentLayer.BANKING,
        PaymentFunction.US_ACCOUNT,
        [Region.USA],
        ["USD"],
        ["ach", "wire"],
        notes="Datos bancarios USA (ABA/routing) solo con KYC personal.",
    ),
    _ac(
        "payoneer",
        "Payoneer",
        PaymentLayer.BANKING,
        PaymentFunction.PAYOUT,
        [Region.GLOBAL, Region.USA],
        ["USD", "EUR", "GBP"],
        ["ach", "wire", "marketplace"],
        notes="Receiving accounts por región; fuerte en marketplaces/freelance.",
        payout_ref="payoneer",
    ),
    _ac(
        "wise",
        "Wise",
        PaymentLayer.BANKING,
        PaymentFunction.GLOBAL,
        [Region.GLOBAL],
        ["USD", "EUR", "GBP", "ARS"],
        ["ach", "wire", "sepa", "local_transfer"],
        notes="Multidivisa; excelente alternativa, pero depende de que habilite la cuenta.",
        payout_ref="wise",
    ),
    # ---- BANKING: global multi-currency ----
    _ac(
        "global66",
        "Global66",
        PaymentLayer.BANKING,
        PaymentFunction.GLOBAL,
        [Region.ARGENTINA, Region.GLOBAL],
        ["USD", "ARS", "PEN", "CLP", "MXN", "COP"],
        ["wire", "local_transfer"],
        notes="Capa multidivisa desde Argentina; transferencias internacionales.",
    ),
    _ac(
        "revolut",
        "Revolut",
        PaymentLayer.BANKING,
        PaymentFunction.GLOBAL,
        [Region.EU, Region.GLOBAL],
        ["USD", "EUR", "GBP"],
        ["ach", "wire", "sepa", "local_transfer"],
        notes="Cuenta EU + datos locales; verificar elegibilidad desde AR.",
        payout_ref="revolut",
    ),
    _ac(
        "n26",
        "N26",
        PaymentLayer.BANKING,
        PaymentFunction.GLOBAL,
        [Region.EU],
        ["EUR"],
        ["sepa", "local_transfer"],
        notes="Neobanco EU; requiere residencia EU para apertura.",
        payout_ref="n26",
    ),
    _ac(
        "wallbit",
        "Wallbit (cuenta digital global)",
        PaymentLayer.BANKING,
        PaymentFunction.GLOBAL,
        [Region.USA, Region.EU],
        ["USD"],
        ["wallet", "local_transfer"],
        notes="KYC remoto con documento; sin residencia. Reci USD, tarjeta virtual, P2P directo a ARS. 1-2 días, 1-2% costo.",
        payout_ref="wallbit",
    ),
    # ---- BANKING: Argentina local ----
    _ac(
        "mercadopago",
        "Mercado Pago",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cvu", "cbu", "local_transfer"],
        notes="CVU para recibir ARS y retirar a banco.",
        payout_ref="mercadopago",
    ),
    _ac(
        "uala",
        "Ualá",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS", "USD"],
        ["cvu", "cbu", "local_transfer"],
        notes="Cuenta CVU + caja USD (cautiva).",
        payout_ref="uala",
    ),
    _ac(
        "brubank",
        "Brubank",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS", "USD"],
        ["cvu", "cbu", "local_transfer"],
        notes="Cuenta digital con CVU/CBU.",
        payout_ref="brubank",
    ),
    _ac(
        "naranjax",
        "Naranja X",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cvu", "cbu", "local_transfer"],
        notes="Cuenta digital + tarjeta.",
    ),
    _ac(
        "prex",
        "Prex Argentina",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA, Region.GLOBAL],
        ["ARS", "USD"],
        ["cvu", "local_transfer"],
        notes="Prex internacional + cuenta USD.",
        payout_ref="prex",
    ),
    _ac(
        "modo",
        "MODO",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cvu", "cbu", "local_transfer"],
        notes="Agregador de CVU/CBU.",
        payout_ref="modo",
    ),
    _ac(
        "personal_pay",
        "Personal Pay",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cvu", "cbu"],
        notes="Cuenta digital del Banco Personal.",
    ),
    _ac(
        "claro_pay",
        "Claro Pay",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cvu", "cbu"],
        notes="Billetera Claro.",
    ),
    _ac(
        "cuenta_dni",
        "Cuenta DNI",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cvu", "cbu"],
        notes="Billetera del Banco Provincia.",
    ),
    # ---- BANKING: Argentina traditional (formal exit) ----
    _ac(
        "galicia",
        "Banco Galicia",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS", "USD"],
        ["cbu", "wire"],
        notes="Salida formal de fondos y documentación.",
        payout_ref="banco_galicia_internacional",
    ),
    _ac(
        "santander",
        "Santander Argentina",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS", "USD"],
        ["cbu", "wire"],
        notes="Cuenta tradicional con caja USD.",
        payout_ref="santander_internacional",
    ),
    _ac(
        "bbva",
        "BBVA Argentina",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS", "USD"],
        ["cbu", "wire"],
        notes="Cuenta tradicional con caja USD.",
        payout_ref="bbva_frances_internacional",
    ),
    _ac(
        "banco_nacion",
        "Banco Nación",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cbu"],
        notes="Banco público; CBU para cobros formales.",
    ),
    _ac(
        "banco_provincia",
        "Banco Provincia",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cbu"],
        notes="Banco público provincial.",
    ),
    _ac(
        "banco_ciudad",
        "Banco Ciudad",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cbu"],
        notes="Banco de CABA.",
    ),
    _ac(
        "hsbc",
        "HSBC Argentina",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS", "USD"],
        ["cbu", "wire"],
        notes="Cuenta tradicional con caja USD.",
    ),
    _ac(
        "icbc",
        "ICBC Argentina",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS", "USD"],
        ["cbu", "wire"],
        notes="Cuenta tradicional con caja USD.",
    ),
    _ac(
        "macro",
        "Banco Macro",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cbu"],
        notes="Banco tradicional.",
    ),
    _ac(
        "supervielle",
        "Banco Supervielle",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cbu"],
        notes="Banco tradicional.",
    ),
    _ac(
        "comafi",
        "Banco Comafi",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cbu"],
        notes="Banco tradicional.",
    ),
    _ac(
        "credicoop",
        "Banco Credicoop",
        PaymentLayer.BANKING,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cbu"],
        notes="Banco cooperativo.",
    ),
    # ---- PROCESSORS: marketplaces / freelance payouts ----
    _ac(
        "paypal",
        "PayPal",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.GLOBAL],
        ["USD", "EUR"],
        ["paypal", "local_transfer"],
        notes="Recepción de marketplaces; retiro a banco AR limitado.",
        payout_ref="paypal_argentina",
    ),
    _ac(
        "astro_pay",
        "AstroPay",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.GLOBAL],
        ["USD", "EUR", "ARS"],
        ["card", "local_transfer"],
        notes="Tarjeta virtual + retiros; frecuente en marketplaces.",
    ),
    _ac(
        "airwallex",
        "Airwallex",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.GLOBAL],
        ["USD", "EUR", "GBP"],
        ["ach", "wire", "sepa", "local_transfer"],
        notes="Cuentas locales en múltiples países para empresas.",
    ),
    _ac(
        "deel",
        "Deel",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.GLOBAL],
        ["USD", "EUR"],
        ["ach", "wire", "paypal"],
        notes="Pagos de nómina freelance; requiere entidad/cuenta según país.",
    ),
    _ac(
        "remote",
        "Remote",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.GLOBAL],
        ["USD", "EUR"],
        ["ach", "wire"],
        notes="Pagos de nómina freelance internacional.",
    ),
    _ac(
        "worldfirst",
        "WorldFirst",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.GLOBAL],
        ["USD", "EUR", "GBP"],
        ["ach", "wire", "sepa"],
        notes="Cuentas locales para e-commerce y marketplaces.",
    ),
    _ac(
        "paysera",
        "Paysera",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.EU, Region.GLOBAL],
        ["EUR", "USD"],
        ["sepa", "wire", "local_transfer"],
        notes="Cuenta IBAN EU + tarjeta.",
    ),
    _ac(
        "zen",
        "ZEN.COM",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.EU, Region.GLOBAL],
        ["EUR", "USD"],
        ["sepa", "card"],
        notes="Cuenta EU + tarjeta virtual.",
    ),
    _ac(
        "icard",
        "iCard",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.EU],
        ["EUR", "USD"],
        ["sepa", "card"],
        notes="Cuenta EU + tarjeta.",
    ),
    _ac(
        "blackcatcard",
        "Blackcatcard",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.EU],
        ["EUR", "USD"],
        ["sepa", "card"],
        notes="Cuenta EU + tarjeta.",
    ),
    _ac(
        "monese",
        "Monese",
        PaymentLayer.PROCESSORS,
        PaymentFunction.PAYOUT,
        [Region.EU, Region.GLOBAL],
        ["EUR", "GBP"],
        ["sepa", "local_transfer"],
        notes="Cuenta UK/EU sin residencia en algunos mercados.",
    ),
    # ---- PROCESSORS: remittances / backup ----
    _ac(
        "western_union",
        "Western Union",
        PaymentLayer.PROCESSORS,
        PaymentFunction.BACKUP,
        [Region.GLOBAL],
        ["USD", "ARS"],
        ["cash", "local_transfer"],
        notes="Retiro en efectivo; costos altos.",
        payout_ref="western_union",
    ),
    _ac(
        "moneygram",
        "MoneyGram",
        PaymentLayer.PROCESSORS,
        PaymentFunction.BACKUP,
        [Region.GLOBAL],
        ["USD", "ARS"],
        ["cash", "local_transfer"],
        notes="Remesas en efectivo.",
        payout_ref="moneygram",
    ),
    _ac(
        "remitly",
        "Remitly",
        PaymentLayer.PROCESSORS,
        PaymentFunction.BACKUP,
        [Region.GLOBAL],
        ["USD", "ARS"],
        ["local_transfer"],
        notes="Remesas a CVU/CBU.",
        payout_ref="remitly",
    ),
    _ac(
        "xoom",
        "Xoom",
        PaymentLayer.PROCESSORS,
        PaymentFunction.BACKUP,
        [Region.GLOBAL],
        ["USD", "ARS"],
        ["local_transfer", "cash"],
        notes="Remesas de PayPal.",
        payout_ref="xoom",
    ),
    _ac(
        "skrill",
        "Skrill",
        PaymentLayer.PROCESSORS,
        PaymentFunction.BACKUP,
        [Region.GLOBAL],
        ["USD", "EUR"],
        ["paypal", "local_transfer", "card"],
        notes="Alternativa de billetera internacional.",
    ),
    _ac(
        "neteller",
        "Neteller",
        PaymentLayer.PROCESSORS,
        PaymentFunction.BACKUP,
        [Region.GLOBAL],
        ["USD", "EUR"],
        ["local_transfer", "card"],
        notes="Alternativa de billetera internacional.",
    ),
    _ac(
        "ofx",
        "OFX",
        PaymentLayer.PROCESSORS,
        PaymentFunction.BACKUP,
        [Region.GLOBAL],
        ["USD", "ARS", "EUR"],
        ["wire", "local_transfer"],
        notes="Transferencias FX grandes con buen tipo de cambio.",
    ),
    # ---- CRYPTO: exchanges ----
    _ac(
        "binance",
        "Binance",
        PaymentLayer.CRYPTO,
        PaymentFunction.PRIMARY,
        [Region.GLOBAL],
        ["USDC", "USDT", "BTC", "ARS"],
        ["crypto", "p2p", "cvu"],
        networks=[Network.BASE, Network.POLYGON, Network.ETHEREUM, Network.BSC, Network.TRON],
        notes="Cobro crypto + P2P a ARS con buen spread.",
        payout_ref="binance_ar",
    ),
    _ac(
        "kraken",
        "Kraken",
        PaymentLayer.CRYPTO,
        PaymentFunction.PRIMARY,
        [Region.GLOBAL],
        ["USDC", "USDT", "BTC", "EUR"],
        ["crypto", "wire", "sepa"],
        networks=[Network.BASE, Network.POLYGON, Network.ETHEREUM],
        notes="Exchange regulado, fuerte en EUR/USD.",
    ),
    _ac(
        "coinbase",
        "Coinbase",
        PaymentLayer.CRYPTO,
        PaymentFunction.PRIMARY,
        [Region.GLOBAL],
        ["USDC", "BTC", "ETH"],
        ["crypto", "ach"],
        networks=[Network.BASE, Network.ETHEREUM],
        notes="USDC nativo en Base; rampa USD.",
    ),
    _ac(
        "okx",
        "OKX",
        PaymentLayer.CRYPTO,
        PaymentFunction.PRIMARY,
        [Region.GLOBAL],
        ["USDC", "USDT", "BTC"],
        ["crypto", "p2p"],
        networks=[Network.BASE, Network.POLYGON, Network.ETHEREUM, Network.TRON],
        notes="Exchange global con P2P.",
    ),
    _ac(
        "bybit",
        "Bybit",
        PaymentLayer.CRYPTO,
        PaymentFunction.PRIMARY,
        [Region.GLOBAL],
        ["USDC", "USDT"],
        ["crypto", "p2p"],
        networks=[Network.BASE, Network.ETHEREUM, Network.TRON],
        notes="Exchange global con P2P.",
    ),
    _ac(
        "bitget",
        "Bitget",
        PaymentLayer.CRYPTO,
        PaymentFunction.PRIMARY,
        [Region.GLOBAL],
        ["USDC", "USDT"],
        ["crypto", "p2p"],
        networks=[Network.BASE, Network.ETHEREUM, Network.TRON],
        notes="Exchange global con P2P.",
    ),
    _ac(
        "crypto_dot_com",
        "Crypto.com",
        PaymentLayer.CRYPTO,
        PaymentFunction.PRIMARY,
        [Region.GLOBAL],
        ["USDC", "CRO", "BTC"],
        ["crypto", "card"],
        networks=[Network.ETHEREUM, Network.BASE],
        notes="Exchange + tarjeta.",
    ),
    # ---- CRYPTO: Argentina conversion ----
    _ac(
        "bitso",
        "Bitso",
        PaymentLayer.CRYPTO,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA, Region.GLOBAL],
        ["USDC", "ARS"],
        ["crypto", "cvu", "p2p"],
        networks=[Network.POLYGON, Network.ETHEREUM, Network.BASE],
        notes="Rampa AR con USDC.",
        payout_ref="bitso",
    ),
    _ac(
        "lemon",
        "Lemon Cash",
        PaymentLayer.CRYPTO,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["USDC", "USDT", "ARS"],
        ["crypto", "cvu"],
        networks=[Network.POLYGON, Network.ETHEREUM, Network.BASE],
        notes="CVU integrado, buen tipo de cambio.",
        payout_ref="lemon_cash",
    ),
    _ac(
        "belo",
        "Belo",
        PaymentLayer.CRYPTO,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["USDC", "USDT", "ARS"],
        ["crypto", "cvu"],
        networks=[Network.POLYGON, Network.ETHEREUM, Network.BASE],
        notes="Capa argentina de recepción/uso de fondos.",
        payout_ref="belo",
    ),
    _ac(
        "buenbit",
        "Buenbit",
        PaymentLayer.CRYPTO,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["USDC", "ARS"],
        ["crypto", "cvu"],
        networks=[Network.POLYGON, Network.ETHEREUM],
        notes="Exchange AR histórico.",
        payout_ref="buenbit",
    ),
    _ac(
        "ripio",
        "Ripio",
        PaymentLayer.CRYPTO,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["USDC", "ARS"],
        ["crypto", "cvu"],
        networks=[Network.ETHEREUM],
        notes="Exchange AR.",
        payout_ref="ripio",
    ),
    _ac(
        "satoshi_tango",
        "SatoshiTango",
        PaymentLayer.CRYPTO,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["BTC", "ARS"],
        ["crypto", "cvu"],
        networks=[Network.ETHEREUM],
        notes="Exchange AR con P2P.",
    ),
    _ac(
        "fiwind",
        "Fiwind",
        PaymentLayer.CRYPTO,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["USDC", "USDT", "ARS"],
        ["crypto", "cvu"],
        networks=[Network.POLYGON, Network.BASE],
        notes="Exchange AR sin comisiones de trading.",
        payout_ref="fiwind",
    ),
    _ac(
        "decrypto",
        "Decrypto",
        PaymentLayer.CRYPTO,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["USDC", "ARS"],
        ["crypto", "cvu"],
        networks=[Network.POLYGON],
        notes="Exchange AR.",
    ),
    # ---- CRYPTO: stablecoin / on-off ramps ----
    _ac(
        "airtm",
        "Airtm",
        PaymentLayer.CRYPTO,
        PaymentFunction.BACKUP,
        [Region.GLOBAL],
        ["USD", "USDC"],
        ["wallet", "local_transfer"],
        networks=[Network.POLYGON],
        notes="Dólar digital + P2P; alternativa internacional y respaldo.",
        payout_ref="airtm",
    ),
    _ac(
        "takenos",
        "Takenos",
        PaymentLayer.CRYPTO,
        PaymentFunction.GLOBAL,
        [Region.ARGENTINA, Region.GLOBAL],
        ["USD", "USDC"],
        ["wallet", "cvu", "local_transfer"],
        networks=[Network.POLYGON],
        notes="Alternativa para cobros internacionales + retiro CVU.",
        payout_ref="tikeknos",
    ),
    _ac(
        "dolarapp",
        "DolarApp",
        PaymentLayer.CRYPTO,
        PaymentFunction.GLOBAL,
        [Region.ARGENTINA, Region.GLOBAL],
        ["USD", "USDC"],
        ["wallet", "cvu", "local_transfer"],
        networks=[Network.POLYGON],
        notes="Gestión de dólares digitales; stablecoins.",
        payout_ref="arq",
    ),
    # ---- SELF CUSTODY: EVM ----
    _ac(
        "metamask",
        "MetaMask",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["USDC", "USDT", "ETH"],
        ["crypto"],
        networks=[Network.BASE, Network.POLYGON, Network.ETHEREUM, Network.BSC, Network.ARBITRUM],
        kyc=False,
        notes="Wallet autocustodia EVM. No es una cuenta bancaria.",
    ),
    _ac(
        "rabby",
        "Rabby Wallet",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["USDC", "USDT", "ETH"],
        ["crypto"],
        networks=[Network.BASE, Network.POLYGON, Network.ETHEREUM, Network.ARBITRUM],
        kyc=False,
        notes="Wallet EVM multi-chain.",
    ),
    _ac(
        "trust_wallet",
        "Trust Wallet",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["USDC", "USDT", "BNB"],
        ["crypto"],
        networks=[Network.BASE, Network.BSC, Network.ETHEREUM, Network.POLYGON],
        kyc=False,
        notes="Wallet móvil multi-chain.",
    ),
    _ac(
        "safe",
        "Safe",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["USDC", "USDT", "ETH"],
        ["crypto"],
        networks=[Network.ETHEREUM, Network.BASE, Network.ARBITRUM],
        kyc=False,
        notes="Multisig EVM para montos altos.",
    ),
    _ac(
        "coinbase_wallet",
        "Coinbase Wallet",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["USDC", "ETH"],
        ["crypto"],
        networks=[Network.BASE, Network.ETHEREUM, Network.POLYGON],
        kyc=False,
        notes="Wallet autocustodia + rampa.",
    ),
    _ac(
        "okx_wallet",
        "OKX Wallet",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["USDC", "USDT"],
        ["crypto"],
        networks=[Network.BASE, Network.POLYGON, Network.ETHEREUM, Network.SOLANA],
        kyc=False,
        notes="Wallet multi-chain.",
    ),
    # ---- SELF CUSTODY: Solana ----
    _ac(
        "phantom",
        "Phantom",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["USDC", "SOL"],
        ["crypto"],
        networks=[Network.SOLANA],
        kyc=False,
        notes="Wallet Solana.",
    ),
    # ---- SELF CUSTODY: hardware ----
    _ac(
        "ledger",
        "Ledger Live",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["BTC", "ETH", "USDC", "USDT", "SOL"],
        ["crypto"],
        networks=[Network.ETHEREUM, Network.BASE, Network.POLYGON, Network.SOLANA],
        kyc=False,
        notes="Hardware wallet para autocustodia de montos grandes.",
    ),
    _ac(
        "trezor",
        "Trezor Suite",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["BTC", "ETH", "USDC", "USDT"],
        ["crypto"],
        networks=[Network.ETHEREUM, Network.BASE],
        kyc=False,
        notes="Hardware wallet.",
    ),
    _ac(
        "exodus",
        "Exodus",
        PaymentLayer.SELF_CUSTODY,
        PaymentFunction.SPECIALIZED,
        [Region.GLOBAL],
        ["BTC", "ETH", "SOL"],
        ["crypto"],
        networks=[Network.ETHEREUM, Network.SOLANA],
        kyc=False,
        notes="Wallet software multi-asset.",
    ),
    # ---- WITHDRAWAL: USD ----
    _ac(
        "withdrawal_usd",
        "Retiro USD",
        PaymentLayer.WITHDRAWAL,
        PaymentFunction.PRIMARY,
        [Region.USA, Region.GLOBAL],
        ["USD"],
        ["ach", "wire"],
        notes="Salida USD: GrabrFi/Wise/Payoneer a cuenta bancaria.",
    ),
    # ---- WITHDRAWAL: ARS ----
    _ac(
        "withdrawal_ars",
        "Retiro ARS",
        PaymentLayer.WITHDRAWAL,
        PaymentFunction.LOCAL,
        [Region.ARGENTINA],
        ["ARS"],
        ["cvu", "cbu"],
        notes="Salida ARS: CVU/CBU de bancos y billeteras locales.",
    ),
]


ACCOUNT_INDEX: dict[str, OwnAccount] = {a.id: a for a in PAYMENT_NETWORK}


def get_account(account_id: str) -> OwnAccount | None:
    """Get an account by id."""
    return ACCOUNT_INDEX.get(account_id)


def accounts_by_layer(layer: PaymentLayer) -> list[OwnAccount]:
    """Get all accounts in a layer."""
    return [a for a in PAYMENT_NETWORK if a.layer == layer]


def accounts_by_function(function: PaymentFunction) -> list[OwnAccount]:
    """Get all accounts with a functional role."""
    return [a for a in PAYMENT_NETWORK if a.function == function]
