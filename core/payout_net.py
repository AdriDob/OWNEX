"""Payout Net — red de cobro en Argentina SOLO CON KYC.

Catálogo de 100+ métodos que funcionan en AR con solo documento de identidad
(KYC): exchanges cripto, P2P, wallets, tarjetas digitales y gift cards.
Ninguno requiere residencia, banco local ni monotributo.

Cada método tiene fallbacks y el sistema resuelve problemas reportados:
resolución + recomendación de alternativas en orden.

Persistencia: ~/.config/ownex/payout_net/state.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.payout_net")

# (id, name, cat, kyc_nivel, usd_qual, dias, costo, fallbacks[])
#   cats: p2p | exchange | wallet | card | gift
METHODS: list[tuple] = [
    # ── P2P (USDT→ARS, mejor cotización) ──
    ("binance_p2p", "Binance P2P", "p2p", 1, "alta", 0.02, "1-2%", ["bybit_p2p", "lemon"]),
    ("bybit_p2p", "Bybit P2P", "p2p", 1, "alta", 0.02, "1-2%", ["binance_p2p", "okx_p2p"]),
    ("okx_p2p", "OKX P2P", "p2p", 1, "alta", 0.02, "1-2%", ["binance_p2p"]),
    ("bitget_p2p", "Bitget P2P", "p2p", 1, "alta", 0.02, "1-2%", ["binance_p2p"]),
    ("mexc_p2p", "MEXC P2P", "p2p", 2, "alta", 0.02, "1-2%", ["binance_p2p"]),
    ("gate_p2p", "Gate.io P2P", "p2p", 2, "alta", 0.03, "1-2%", ["binance_p2p"]),
    ("kraken_p2p", "Kraken (Coin-to-fiat)", "p2p", 2, "media", 1, "2-4%", ["binance_p2p"]),
    ("crypto_p2p", "OKX/Nexo (P2P UK)", "p2p", 2, "media", 0.05, "2%", ["binance_p2p"]),
    # ── Exchanges internacionales (KYC simple) ──
    ("coinbase", "Coinbase", "exchange", 2, "media", 1, "1.5%", ["kraken", "gemini"]),
    ("kraken", "Kraken", "exchange", 2, "media", 0.5, "1.5%", ["coinbase", "gemini"]),
    ("gemini", "Gemini", "exchange", 2, "media", 1, "2%", ["kraken"]),
    ("crypto", "Crypto.com", "exchange", 2, "media", 0.5, "2%", ["binance_direct"]),
    ("binance_direct", "Binance Convert", "exchange", 1, "media", 0.02, "0.6%", ["bybit_direct"]),
    ("kuCoin", "KuCoin", "exchange", 2, "media", 0.2, "1%", ["mexc"]),
    ("okx_direct", "OKX Convert", "exchange", 1, "media", 0.02, "0.8%", ["binance_direct"]),
    ("gateio", "Gate.io", "exchange", 2, "baja", 1, "2%", ["kraken"]),
    ("bitso", "Bitso (MX/AR)", "exchange", 2, "media", 0.1, "1%", ["bitso"]),
    ("buda", "Buda (CL/AR)", "exchange", 2, "media", 0.2, "1.5%", ["crypto"]),
    ("huobi", "HTX/HTX", "exchange", 2, "media", 0.5, "2%", ["gateio"]),
    ("bybit_direct", "Bybit Convert", "exchange", 1, "media", 0.03, "1%", ["binance_direct"]),
    # ── CEX locales AR (KYC+DNI) ──
    ("lemon", "Lemon", "exchange", 2, "media", 0.05, "1%", ["buenbit", "belo"]),
    ("buenbit", "Buenbit", "exchange", 2, "media", 0.1, "1%", ["lemon"]),
    ("belo", "Belo", "exchange", 2, "media", 0.1, "1%", ["lemon"]),
    ("riipio", "Ripio", "exchange", 2, "media", 0.1, "1.5%", ["lemon", "belo"]),
    ("satoshi", "SatoshiTango", "exchange", 2, "media", 0.3, "2%", ["lemon"]),
    ("neo_fia", "Naranja X/Más", "card", 2, "baja", 0.1, "2-4%", ["lemon"]),
    ("parallax", "Parallax", "exchange", 2, "alta", 0.05, "1%+", ["dolarapp"]),
    ("restaurant", "Registro AR", "exchange", 2, "baja", 0.5, "3%", ["lemon"]),
    # ── Wallets universales (receptor) ──
    ("trust", "Trust Wallet", "wallet", 1, "alta", 0, "gas", ["metamask"]),
    ("metamask", "MetaMask", "wallet", 1, "alta", 0, "gas", ["trust"]),
    ("rabby", "Rabby", "wallet", 1, "alta", 0, "gas", ["metamask"]),
    ("exodus", "Exodus", "wallet", 1, "media", 0, "gas", ["trust"]),
    ("phantom", "Phantom (Solana)", "wallet", 1, "media", 0, "gas", ["trust"]),
    ("safe", "Safe (multisig)", "wallet", 1, "media", 0, "gas", ["metamask"]),
    # ── Tarjetas digitales USD/crypto ──
    ("dolarapp", "DolarApp (USDC→ARS)", "card", 2, "alta", 0.05, "1%", ["wallbit"]),
    ("wallbit", "Wallbit", "card", 2, "media", 0.05, "1%+", ["payt"]),
    ("prex", "Prex", "card", 2, "media", 0.05, "1-2%", ["dolarapp"]),
    ("astropay", "AstroPay", "card", 2, "baja", 1, "2%", ["dolarapp"]),
    ("wirex", "Wirex (VISA)", "card", 2, "media", 1, "2%", ["dolarapp"]),
    ("uphold", "Uphold debt", "card", 2, "baja", 1, "2-3%", ["dolarapp"]),
    ("cryptobote", "CryptoBot VISA", "card", 2, "media", 1, "2%", ["dolarapp"]),
    ("bitrefill", "Bitrefill (gift cards)", "gift", 1, "media", 0, "2-5%", ["giftway"]),
    ("giftway", "PayPal gift", "gift", 1, "baja", 1, "3-5%", ["bitrefill"]),
    # ── Regalos / descargas seguras (sin historial local) ──
    ("presta", "Gift cards globales", "gift", 1, "media", 0.1, "3-6%", ["bitrefill"]),
    ("revolut", "Revolut (cuenta EUR/USD)", "card", 2, "media", 1, "2%", ["wise"]),
    ("wise", "Wise", "card", 2, "media", 1, "1%", ["revolut"]),
    # ── Expansión: P2P adicionales ──
    ("paxful", "Paxful (P2P multi-método)", "p2p", 2, "media", 0.05, "2-4%", ["binance_p2p", "localcoins"]),
    ("localcoins", "LocalCoins (P2P directo)", "p2p", 2, "media", 0.05, "2-5%", ["binance_p2p", "paxful"]),
    ("hodlhodl", "HodlHodl (P2P BTC)", "p2p", 2, "baja", 0.1, "2-5%", ["binance_p2p"]),
    ("aguascal", "P2P via Mercado Pago (P2P)", "p2p", 1, "alta", 0.01, "1-2%", ["binance_p2p"]),
    ("zen_crypto", "ZenGo / Zenon (P2P)", "p2p", 2, "baja", 0.5, "3%", ["binance_p2p"]),
    ("unitedx", "P2P USDT→ARS (UNI)", "p2p", 2, "media", 0.1, "2%", ["binance_p2p"]),
    # ── Expansión: Exchanges de bajo perfil ──
    ("mexc", "MEXC (sin KYC fuerte)", "exchange", 1, "media", 0.1, "0.8%", ["bybit_direct"]),
    ("bingx", "BingX", "exchange", 1, "media", 0.1, "0.8%", ["mexc"]),
    ("bitget_x", "Bitget", "exchange", 1, "media", 0.1, "0.8%", ["bybit_direct"]),
    ("kucoin_x", "KuCoin (amplio)", "exchange", 2, "media", 0.2, "1%", ["mexc"]),
    ("bitstamp", "Bitstamp (EUR/USD)", "exchange", 2, "baja", 1, "1.5%", ["kraken"]),
    ("coinbase_pay", "Coinbase Pay", "exchange", 2, "media", 1, "1.5%", ["coinbase"]),
    ("swissborg", "SwissBorg", "exchange", 2, "baja", 2, "2%", ["crypto"]),
    ("bitvavo", "Bitvavo (EU)", "exchange", 2, "baja", 2, "2%", ["bitstamp"]),
    ("gate_convert", "Gate Convert", "exchange", 1, "media", 0.1, "0.8%", ["gateio"]),
    ("exmo", "EXMO", "exchange", 2, "baja", 1, "2%", ["crypto"]),
    ("bitfinex", "Bitfinex", "exchange", 2, "baja", 1, "2%", ["kraken"]),
    ("woo", "WOO X", "exchange", 1, "media", 0.1, "0.6%", ["bybit_direct"]),
    ("okx_x", "OKX (amplio)", "exchange", 1, "media", 0.1, "0.8%", ["bybit_direct"]),
    ("htx_x", "HTX (Huobi)", "exchange", 2, "baja", 1, "2%", ["mexc"]),
    # ── Expansión: Wallets y tarjetas ──
    ("coinbase_w", "Coinbase Wallet", "wallet", 1, "alta", 0, "gas", ["trust"]),
    ("argent", "Argent (L2)", "wallet", 1, "media", 0, "gas", ["metamask"]),
    ("debank", "Debank Wallet", "wallet", 1, "media", 0, "gas", ["rabby"]),
    ("bitget_w", "Bitget Wallet", "wallet", 1, "media", 0, "gas", ["trust"]),
    ("tonkeeper", "Tonkeeper (TON)", "wallet", 1, "media", 0, "gas", ["trust"]),
    ("solflare", "Solflare (SOL)", "wallet", 1, "media", 0, "gas", ["phantom"]),
    ("ledger", "Ledger (hardware)", "wallet", 1, "alta", 0, "gas", ["trust"]),
    ("cardano", "Yoroi/AdaLite", "wallet", 1, "media", 0, "gas", ["trust"]),
    ("zcash", "Zcash Wallet", "wallet", 1, "media", 0, "gas", ["trust"]),
    ("monero", "Monero Wallet (priv)", "wallet", 1, "media", 0, "gas", ["trust"]),
    ("payt", "Payt / Tarjeta cripto", "card", 2, "media", 1, "2%", ["dolarapp"]),
    ("univisa", "Universal VISA cripto", "card", 2, "media", 1, "2%", ["dolarapp"]),
    ("genesis", "Genesis Card (crypto)", "card", 2, "baja", 2, "3%", ["dolarapp"]),
    ("bitstamp_card", "Bitstamp VISA", "card", 2, "baja", 2, "3%", ["crypto"]),
    ("crypo", "Crypto.com VISA", "card", 2, "media", 1, "2%", ["wirex"]),
    ("swan", "Swan Card (BTC)", "card", 2, "baja", 2, "3%", ["dolarapp"]),
    ("bitcoin_bear", "BitcoinBears (BTC card)", "card", 2, "baja", 3, "4%", ["dolarapp"]),
    # ── Expansión: Gift cards y vouchers ──
    ("amazon_ar", "Gift card Amazon US", "gift", 1, "media", 0.2, "3-6%", ["bitrefill"]),
    ("gift_crypto", "Crypto.com gift", "gift", 1, "media", 0.2, "3%", ["bitrefill"]),
    ("appstore", "App Store gift", "gift", 1, "media", 0.2, "4%", ["bitrefill"]),
    ("steam_gift", "Steam wallet", "gift", 1, "media", 0.2, "4%", ["bitrefill"]),
    ("psn", "PlayStation Store", "gift", 1, "media", 0.2, "4%", ["bitrefill"]),
    ("netflix", "Netflix gift", "gift", 1, "media", 0.2, "3%", ["bitrefill"]),
    ("uber", "Uber gift", "gift", 1, "media", 0.2, "3%", ["bitrefill"]),
    ("mercado_libre", "Mercado Libre gift", "gift", 1, "media", 0.1, "3%", ["bitrefill"]),
    ("google_play", "Google Play gift", "gift", 1, "media", 0.2, "4%", ["bitrefill"]),
    ("airbnb", "Airbnb gift", "gift", 1, "media", 0.2, "4%", ["bitrefill"]),
    ("spotify", "Spotify gift", "gift", 1, "media", 0.2, "3%", ["bitrefill"]),
    ("samsung", "Samsung gift", "gift", 1, "media", 0.2, "4%", ["bitrefill"]),
    # ── Expansión: bancos/e-wallet internacionales (KYC) ──
    ("wise_e", "Wise Business (USD/EUR)", "card", 2, "media", 1, "1%", ["wise"]),
    ("payoneer", "Payoneer (USD virtual)", "card", 2, "media", 1, "2%", ["skrill"]),
    ("skrill", "Skrill", "card", 2, "baja", 1, "3%", ["payoneer"]),
    ("neteller", "Neteller", "card", 2, "baja", 1, "3%", ["skrill"]),
    ("airtm", "AirTM (USDT salida)", "card", 2, "baja", 0.5, "3-5%", ["dolarapp"]),
    ("zeepay", "ZeePay (USDT)", "card", 2, "baja", 1, "3%", ["airtm"]),
    ("mifinity", "MiFinity", "card", 2, "baja", 1, "3%", ["skrill"]),
    ("eco", "eCore/ECOPAYZ", "card", 2, "baja", 1, "3%", ["skrill"]),
    ("rapyd", "Rapyd Wallet", "card", 2, "baja", 1, "3%", ["skrill"]),
    ("valutapay", "ValutaPay", "card", 2, "baja", 1, "3%", ["skrill"]),
    # ── Expansión: Cripto pasarelas de recepción ──
    ("nowpayments", "NOWPayments (receber)", "exchange", 1, "media", 0.5, "1-2%", ["coinbase_pay"]),
    ("cryptapi", "CryptAPI (gateway)", "exchange", 1, "media", 0.5, "1-2%", ["nowpayments"]),
    ("plisio", "Plisio", "exchange", 1, "media", 0.5, "1-2%", ["cryptapi"]),
    ("paypal", "PayPal (USD retención)", "card", 2, "baja", 1, "4%", ["payoneer"]),
    ("stripe_c", "Stripe (proceso card)", "exchange", 2, "baja", 2, "2.9%", ["paypal"]),
    ("square", "Square/Payssion", "exchange", 2, "baja", 2, "3%", ["stripe_c"]),
    ("wise_card", "Wise VISA (USD/EUR)", "card", 2, "media", 1, "1-2%", ["wise"]),
    ("bitgo", "BitGo (custodia)", "wallet", 1, "alta", 0, "gas", ["trust"]),
    ("coinbase_cust", "Coinbase Custody", "wallet", 1, "alta", 0, "gas", ["bitgo"]),
    ("fireblocks", "Fireblocks (institucional)", "wallet", 1, "alta", 0, "gas", ["bitgo"]),
    ("nexo", "Nexo (préstamos cripto)", "card", 2, "media", 1, "2%", ["crypto"]),
    ("blockfi", "BlockFi (ahorro)", "card", 2, "baja", 2, "3%", ["nexo"]),
    ("curve", "Curve (wraps cards)", "card", 2, "media", 1, "2%", ["wirex"]),
    ("uphold_c", "Uphold (multi)", "exchange", 2, "baja", 1, "2%", ["crypto"]),
    ("guardarian", "Guardarian (comprar)", "exchange", 1, "media", 0.5, "2%", ["mexc"]),
    ("changelly", "Changelly (swap)", "exchange", 1, "media", 0.5, "1-2%", ["guardarian"]),
    ("simplex", "Simplex (card compra)", "exchange", 1, "media", 0.5, "2%", ["moonpay"]),
    ("moonpay", "MoonPay", "exchange", 1, "media", 0.5, "2%", ["simplex"]),
    ("transak", "Transak (onramp)", "exchange", 1, "media", 0.5, "2%", ["moonpay"]),
    ("onramper", "Onramper (multi)", "exchange", 1, "media", 0.5, "2%", ["transak"]),
    ("ally", "Ally Invest", "card", 2, "baja", 3, "3%", ["wise"]),
    ("tastytrade", "Tastytrade", "card", 2, "baja", 3, "3%", ["ally"]),
    ("interactive", "Interactive Brokers (USD)", "card", 2, "baja", 3, "2%", ["wise"]),
    ("etoro", "eToro (USD)", "card", 2, "baja", 2, "2%", ["interactive"]),
    ("robinhood", "Robinhood (crypto)", "card", 2, "baja", 2, "3%", ["etoro"]),
    ("coinme", "Coinme (ATM BTC)", "exchange", 2, "baja", 1, "3%", ["moonpay"]),
    ("bitcoin_atm", "BTC ATM (retiro)", "gift", 2, "baja", 1, "4-8%", ["coinme"]),
    ("gift_balance", "Gift cards exchange AR", "gift", 1, "media", 0.2, "5%", ["bitrefill"]),
    ("payeer", "Payeer (e-wallet)", "card", 2, "baja", 1, "3%", ["skrill"]),
    ("advcash", "AdvCash", "card", 2, "baja", 1, "3%", ["payeer"]),
    ("perfect_money", "Perfect Money", "card", 2, "baja", 1, "3%", ["advcash"]),
    ("webmoney", "WebMoney", "card", 2, "baja", 1, "3%", ["perfect_money"]),
    ("epay", "EPay (UA)", "card", 2, "baja", 1, "3%", ["payeer"]),
    ("capitalist", "Capitalist", "card", 2, "baja", 1, "3%", ["epay"]),
    ("xoom", "Xoom (PayPal money)", "card", 2, "baja", 1, "4%", ["paypal"]),
    ("wise_local", "Wise local (pairs)", "card", 2, "media", 1, "1-2%", ["wise"]),
    ("western", "Western Union (cash)", "card", 2, "baja", 1, "3-6%", ["moneygram"]),
    ("moneygram", "MoneyGram (cash)", "card", 2, "baja", 1, "3-6%", ["western"]),
    ("saldo", "Saldo.com.ar (VAS)", "exchange", 2, "media", 0.5, "2%", ["lemon"]),
    ("naranja", "Naranja X (USD tarjeta)", "card", 2, "baja", 0.5, "3%", ["prex"]),
    ("uala", "Ualá (USD cuenta)", "card", 2, "baja", 0.5, "3%", ["prex"]),
    ("brubank", "Brubank (USD)", "card", 2, "baja", 0.5, "3%", ["prex"]),
    ("mercado_pago", "Mercado Pago (USD/ARS)", "card", 2, "baja", 0.2, "3%", ["prex"]),
    ("fiwind", "Fiwind (ARS cripto)", "exchange", 2, "media", 0.2, "1%", ["lemon"]),
    ("letsbit", "LetsBit (ARS cripto)", "exchange", 2, "media", 0.2, "1%", ["fiwind"]),
    ("tranfi", "Tranfi (BRL/ARS)", "exchange", 2, "baja", 0.5, "2%", ["fiwind"]),
    ("1para1", "1para1 (P2P LatAm)", "p2p", 2, "media", 0.2, "2%", ["binance_p2p"]),
    ("binance_gift", "Binance Gift Card", "gift", 1, "media", 0.1, "2%", ["bitrefill"]),
    ("bitget_gift", "Bitget Gift", "gift", 1, "media", 0.1, "2%", ["binance_gift"]),
]

# Resolución de problemas (general) + fija por reporte del operador
PROBLEM_FIXES = {
    "kyc_rest": "Resubí el documento con selfie en luz natural. Si falla, usá un método del mismo cat (p2p o card).",
    "p2p_reject": "La contraparte canceló. Intentá de nuevo eligiendo un vendedor con alta reputación o cambiá a P2P de otro exchange.",
    "card_block": "La tarjeta quedó bloqueada por verificación. Esperá 24h, revisá notificaciones de la app, o usá otro método del mismo cat.",
    "withdraw_hold": "Retiro demorado. Comprobá que la cuenta destino esté sin límite y registrada. La mayoría descongela en 24-72h.",
    "rate_bad": "Mal tipo de cambio en el método 1. Andá a P2P (Binance/Bybit) para la mejor cotización de la red.",
    "min_limit": "Montos menores al mínimo del método. Acumulá en un mismo wallet y usalo cuando supere el umbral.",
    "bank_risk": "CBU destino rechazado por el banco. Usá tarjeta digital (crypto) o sali en cripto para evitar el banco clásico.",
    "unsupported": "La plataforma no soporta AR como país de salida. Usá tarjeta USDT/gift como puente y después cripto.",
}

# Plataforma → orden de métodos
SOURCE_MAP = {
    "forge": ["binance_p2p", "bybit_p2p", "lemon"],
    "pulse": ["payt", "dolarapp", "prex"],
    "bounty": ["binance_direct", "sky", "lemon"],
    "freelance": ["dolarapp", "wallbit"],
    "web3": ["metamask", "trust", "binance_direct"],
    "prod": ["stripe_d", "dolarapp", "prex"],
}

_DEFAULT_STATE = {"created": None, "incidents": {}}


def _cat(id_: str) -> str:
    for m in METHODS:
        if m[0] == id_:
            return m[2]
    return ""


class PayoutNet:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/payout_net/")
        os.makedirs(self.data_dir, exist_ok=True)

    @property
    def state_path(self) -> str:
        return os.path.join(self.data_dir, "state.json")

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                s = json.load(f)
                for k, v in _DEFAULT_STATE.items():
                    s.setdefault(k, v)
                return s
        except Exception:
            return dict(_DEFAULT_STATE)

    def _save(self, s: dict[str, Any]) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)

    def _to_dict(self, m: tuple) -> dict[str, Any]:
        return {
            "id": m[0],
            "name": m[1],
            "cat": m[2],
            "kyc": "Solo documento" if m[3] == 1 else "KYC + selfie",
            "cotiz": m[4],
            "dias": m[5],
            "costo": m[6],
            "fallbacks": [self._ml(f) for f in m[7]],
        }

    def _ml(self, mid: str) -> str:
        for m in METHODS:
            if m[0] == mid:
                return m[1]
        return mid

    def get_catalog(self, cat: str = "") -> dict[str, Any]:
        items = [self._to_dict(m) for m in METHODS if not cat or m[2] == cat]
        cats = {}
        for m in METHODS:
            cats.setdefault(m[2], 0)
            cats[m[2]] += 1
        return {"success": True, "total": len(METHODS), "categories": cats, "methods": items}

    def recommend_for(self, source: str) -> dict[str, Any]:
        ids = SOURCE_MAP.get(source, ["binance_p2p", "lemon"])
        recs = []
        for mid in ids:
            m = next((x for x in METHODS if x[0] == mid), None)
            if m:
                recs.append(self._to_dict(m))
        return {"success": True, "source": source, "recommended": recs}

    def resolve(self, method_id: str, problem: str) -> dict[str, Any]:
        m = next((x for x in METHODS if x[0] == method_id), None)
        key = self._problem_key(problem)
        fix = PROBLEM_FIXES.get(key, "Reintentá normalizar y registrá el síntoma en OWNEX para que lo aprenda.")
        if not m:
            return {"success": False, "message": "Método no encontrado.", "key": key, "fix": fix}
        fallbacks = [self._ml(f) for f in m[7]]
        state = self._load()
        inc = state.setdefault("incidents", {})
        inc.setdefault(method_id, []).append(
            {"problem": problem, "fix": fix, "created_at": datetime.now(UTC).isoformat()}
        )
        self._save(state)
        return {
            "success": True,
            "method": m[1],
            "problem": problem,
            "fix": fix,
            "fallbacks": fallbacks,
            "key": key,
        }

    def _problem_key(self, problem: str) -> str:
        p = problem.lower()
        if "kyc" in p or "docu" in p or "selfie" in p:
            return "kyc_rest"
        if "p2p" in p or "contra" in p or "usdt" in p:
            return "p2p_reject"
        if "tarj" in p or "card" in p or "banco" in p or "cbu" in p:
            return "bank_risk"
        if "retir" in p or "demora" in p or "hold" in p:
            return "withdraw_hold"
        if "cotiz" in p or "precio" in p or "rate" in p:
            return "rate_bad"
        if "mín" in p or "minim" in p or "faltan" in p:
            return "min_limit"
        if "país" in p or "country" in p:
            return "unsupported"
        return "p2p_reject"

    def get_status(self) -> dict[str, Any]:
        s = self._load()
        return {
            "success": True,
            "total_methods": len(METHODS),
            "created": s.get("created"),
            "incidents": len(s.get("incidents", {})),
        }


Net: PayoutNet | None = None


def get_payout_net() -> PayoutNet:
    global Net
    if Net is None:
        Net = PayoutNet()
    return Net
