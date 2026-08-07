"""Finance Guru — consultas y resolución de cobro y cuentas bancarias
internacionales/USA desde Argentina (solo KYC).

El operador le pregunta a OWNEX en lenguaje natural, ej:
  "me retuvieron un pago en Payoneer"
  "cómo abro cuenta bancaria en USA desde Argentina"
  "qué banco internacional acepta solo KYC sin residencia"
OWNEX matchea el intent, devuelve el procedimiento + fallbacks y registra
el incidente para aprender.

Persistencia: ~/.config/ownex/finance_guru/state.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.finance_guru")

# ── Cuentas internacionales/USA abribles desde AR (solo KYC o +LLC) ──

ACCOUNTS: list[dict[str, Any]] = [
    {
        "id": "wise",
        "name": "Wise (multi-divisa USD/EUR/GBP)",
        "region": "Global",
        "kyc": "Documento + selfie. Sin residencia verificable.",
        "llc_needed": False,
        "dias": "1-3",
        "costo": "1-2% conversión",
        "para": ["recibir USD de freelance", "guardar USD", "pagar servicios internacionales"],
        "pasos": [
            "Crear cuenta web/app → región Global",
            "KYC: documento + selfie",
            "Recibí datos bancarios USD/EUR",
            "Retirá a tu tarjeta local o saldo",
        ],
        "problemas": {
            "verificacion": "KYC de Wise suele pedir comprobante de residencia. Si no tenés, usá el comprobante del monotributo o factura E a tu nombre.",
            "retencion": "Si retienen un pago: subí el mail de la plataforma emisora + screenshot del estado del pago. Se libera en 24-72h.",
            "cuenta_suspendida": "Llamá/soporte en 24h con documentación de origen de fondos (contratos, facturas, pantallas).",
        },
        "fallbacks": ["payoneer", "wallbit"],
    },
    {
        "id": "payoneer",
        "name": "Payoneer (cuenta USD virtual)",
        "region": "USA",
        "kyc": "Documento + verificación de identidad. Muy simple para freelance.",
        "llc_needed": False,
        "dias": "2-5",
        "costo": "2-3% retiro",
        "para": ["HackerOne/Bugcrowd/Upwork pagos", "recibir ACH/USD", "tarjeta Mastercard para gastar"],
        "pasos": [
            "Registrar cuenta personal",
            "KYC: documento + datos de negocio",
            "Activar receiving account USD (ABA)",
            "Esperar depósito de verificación o directo",
        ],
        "problemas": {
            "kyc_rechazado": "Resubí documento con selfie en luz natural y datos coherentes (nombre exacto).",
            "retencion": "Retiros retenidos: revisá 'documentos pendientes' en dashboard; subí factura/contrato.",
            "cuenta_cerrada": "Soporte 48h con evidencia de origen de fondos (bounty pages, contratos).",
        },
        "fallbacks": ["wise", "skrill"],
    },
    {
        "id": "wallbit",
        "name": "Wallbit (cuenta digital global)",
        "region": "USA/EU",
        "kyc": "KYC remoto con documento. Sin residencia.",
        "llc_needed": False,
        "dias": "1-2",
        "costo": "1-2%",
        "para": ["recibir USD", "tarjeta virtual", "P2P directo a ARS"],
        "pasos": ["Registro web", "KYC remoto", "Recibí datos USD", "Usá la tarjeta o P2P"],
        "problemas": {
            "verificacion": "Verificación remota suele fallar en cámara; probá desde celular con buena luz.",
            "p2p": "Si el P2P rechaza: usá saldo directo a la tarjeta o mové a Binance.",
        },
        "fallbacks": ["dolarapp", "wise"],
    },
    {
        "id": "dolarapp",
        "name": "DolarApp (USDC → ARS + tarjeta)",
        "region": "Global",
        "kyc": "KYC remoto simple.",
        "llc_needed": False,
        "dias": "0.2",
        "costo": "1%",
        "para": ["convertir USD a ARS con tarjeta", "pagos locales", "saldo estable"],
        "pasos": ["Descargar app", "KYC con documento", "Recibir USDC", "Gastar tarjeta o enviar a ARS"],
        "problemas": {
            "card_bloqueada": "Tarjeta virtual bloqueada por prueba de vida: esperá 24h o recargá $1.",
            "kyc": "Si falla, probá desde la app en vez de web.",
        },
        "fallbacks": ["wallbit", "prex"],
    },
    {
        "id": "grabrfi",
        "name": "GrabrFi (cuenta USA online)",
        "region": "USA",
        "kyc": "KYC remoto para LatAm.",
        "llc_needed": False,
        "dias": "3-7",
        "costo": "bajo",
        "para": ["cuenta de banco virtual USA sin residencia", "recibir ACH/wire"],
        "pasos": ["Registrar", "KYC remoto", "Obtener datos ABA/USD"],
        "problemas": {
            "disponibilidad": "Disponibilidad por país puede cambiar; verificá en su web.",
            "verificacion": "Puede pedir comprobante de dirección: usá una factura de servicio a tu nombre.",
        },
        "fallbacks": ["payoneer", "wise"],
    },
    {
        "id": "skrill",
        "name": "Skrill (e-wallet multi-divisa)",
        "region": "EU",
        "kyc": "KYC remoto.",
        "llc_needed": False,
        "dias": "1-2",
        "costo": "2-4%",
        "para": ["recibir de marketplaces", "tarjeta prepaga", "P2P"],
        "pasos": ["Registrar", "KYC", "Recibir fondos", "Tarjeta o retiro"],
        "problemas": {
            "retencion": "Retiros retenidos por anti-fraude: subí evidencia del pago y esperá 48-72h.",
            "kyc": "Revisá que el nombre coincida exacto con el documento.",
        },
        "fallbacks": ["payoneer", "neteller"],
    },
    {
        "id": "airwallex",
        "name": "Airwallex (empresa, USD/EUR)",
        "region": "Global",
        "kyc": "Requiere entidad/LLC (no solo KYC personal).",
        "llc_needed": True,
        "dias": "3-10",
        "costo": "bajo",
        "para": ["cuentas empresariales multi-divisa", "facturación internacional"],
        "pasos": ["Constituir LLC/entidad", "Registrar en Airwallex", "KYC empresa", "Datos bancarios globales"],
        "problemas": {
            "kyc_empresa": "Necesitás LLC: usá Stripe Atlas o Doola (~$500), luego Airwallex.",
            "documentacion": "Subir EIN y estatutos.",
        },
        "fallbacks": ["mercury"],
    },
    {
        "id": "mercury",
        "name": "Mercury (banco USA para startups)",
        "region": "USA",
        "kyc": "Solo con LLC/entidad USA (no personal).",
        "llc_needed": True,
        "dias": "5-15",
        "costo": "gratis",
        "para": ["banco USA real con ACH/wire", "compañía propia"],
        "pasos": ["Constituir LLC (Stripe Atlas/Doola)", "Registrar Mercury", "KYC + EIN", "Cuenta operativa"],
        "problemas": {
            "llc": "Sin LLC no se puede. Es el camino para cuenta USA real.",
            "verificacion": "Presentá los docs de la LLC y el EIN.",
        },
        "fallbacks": ["airwallex", "relay"],
    },
    {
        "id": "relay",
        "name": "Relay (banco USA empresas)",
        "region": "USA",
        "kyc": "Con LLC.",
        "llc_needed": True,
        "dias": "3-7",
        "costo": "gratis",
        "para": ["banco USA con tarjetas", "equipos"],
        "pasos": ["LLC primero", "Registrar Relay", "KYC", "Cuenta + tarjetas"],
        "problemas": {"llc": "Igual que Mercury: LLC requerida."},
        "fallbacks": ["mercury"],
    },
    {
        "id": "stellar",
        "name": "Stellar Development (pagos)",
        "region": "Global",
        "kyc": "N/A (red)",
        "llc_needed": False,
        "dias": "0",
        "costo": "gas bajo",
        "para": ["recibir stablecoins USDC", "P2P"],
        "pasos": ["Wallet Stellar", "Recibir USDC", "P2P a ARS"],
        "problemas": {"k": "No aplica KYC en la red; usá exchange para cambio."},
        "fallbacks": ["binance_p2p"],
    },
    {
        "id": "binance_pay",
        "name": "Binance Pay (stable → ARS)",
        "region": "Global",
        "kyc": "KYC Binance simple.",
        "llc_needed": False,
        "dias": "0.02",
        "costo": "1-2%",
        "para": ["recibir USDT/USDC", "P2P a ARS"],
        "pasos": ["KYC Binance", "Recibir crypto", "P2P"],
        "problemas": {"p2p": "P2P: verificar reputación del vendedor; nunca liberar sin confirmar ARS."},
        "fallbacks": ["stellar"],
    },
]

# Intents por keywords
INTENTS: list[tuple[str, list[str]]] = [
    ("abrir_cuenta_usa", ["cuenta", "banco", "usa", "estados unidos", "abrir", "abrirlo", "routing", "aba", "ach"]),
    ("recibir_pago", ["recibir", "pago", "cobrar", "retiro", "fondos", "wire", "deposito"]),
    ("retener", ["reten", "hold", "suspend", "congel", "espera", "bloqueo"]),
    ("kyc", ["kyc", "verific", "documento", "selfie", "rechazo"]),
    ("convertir", ["convertir", "cambio", "cotiz", "usd", "ars", "cambiar"]),
    ("llc", ["llc", "empresa", "compañia", "stripe atlas", "doola", "ein"]),
]

INTENT_ANSWERS: dict[str, str] = {
    "abrir_cuenta_usa": "Para abrir cuenta bancaria en USA desde Argentina SIN residencia: (1) Payoneer/Wise/Wallbit = solo KYC, te dan datos USD (ABA). (2) Si querés un banco USA real (Mercury/Relay) necesitás una LLC (~$500 vía Stripe Atlas/Doola). Elegí el nivel que necesitás y usá el catálogo.",
    "recibir_pago": "Para recibir pagos de plataformas: Payoneer (bounty/freelance), Wise (USD/EUR), Wallbit/DolarApp (stable→ARS). Detalle: esperá el depósito de verificación, revisá la sección 'Documentos pendientes' y confirmá los datos ABA/CBU exactos.",
    "retener": "Pago retenido: (1) Revisá 'documentos/verificación' en la plataforma. (2) Subí factura/contrato/screenshot del pago. (3) Contactá soporte con evidencia. La mayoría libera en 24-72h. Mientras tanto, usá un fallback del mismo tipo.",
    "kyc": "KYC rechazado: resubí documento con selfie en luz natural y datos idénticos al documento (nombre exacto, sin abreviaturas). Si falla 2 veces, probá otro proveedor de la misma categoría (Wise→Payoneer, DolarApp→Wallbit).",
    "convertir": "Mejor conversión USD→ARS: Binance P2P (cotización más alta, 1-2%). Alternativas: DolarApp (tarjeta, 1%), Wallbit. Evitá el banco clásico (cotización oficial).",
    "llc": "Para LLC desde Argentina: Stripe Atlas o Doola (~$500, EIN incluido). Con eso abrís Mercury/Relay/Airwallex (bancos USA reales). Alternativa sin LLC: Payoneer/Wise.",
}

_DEFAULT_STATE = {"created": None, "qa": [], "resolved": 0}


class FinanceGuru:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/finance_guru/")
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

    def _match_intent(self, query: str) -> str:
        q = query.lower()
        scores: dict[str, int] = {}
        for intent, kws in INTENTS:
            scores[intent] = sum(1 for k in kws if k in q)
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "recibir_pago"

    def ask(self, query: str) -> dict[str, Any]:
        if not query.strip():
            return {"success": False, "message": "Escribí tu consulta."}
        intent = self._match_intent(query)
        answer = INTENT_ANSWERS.get(intent, INTENT_ANSWERS["recibir_pago"])

        # Recomendar cuentas según keywords
        q = query.lower()
        recs = []
        if any(k in q for k in ["usa", "banco", "cuenta"]):
            for a in ACCOUNTS:
                if not a["llc_needed"] and a["region"] in ("USA", "Global"):
                    recs.append({"id": a["id"], "name": a["name"], "dias": a["dias"]})
        if any(k in q for k in ["pago", "cobrar", "retiro", "payoneer", "wise"]):
            for a in ACCOUNTS:
                if a["id"] in ("payoneer", "wise", "wallbit"):
                    recs.append({"id": a["id"], "name": a["name"], "dias": a["dias"]})

        state = self._load()
        state["qa"].append({"q": query, "intent": intent, "created_at": datetime.now(UTC).isoformat()})
        self._save(state)

        return {
            "success": True,
            "intent": intent,
            "answer": answer,
            "recommended": recs[:4],
            "acccounts_total": len(ACCOUNTS),
        }

    def resolve_account(self, account_id: str, problem: str) -> dict[str, Any]:
        acc = next((a for a in ACCOUNTS if a["id"] == account_id), None)
        if not acc:
            return {"success": False, "message": "Cuenta no encontrada."}
        key = self._problem_key(problem)
        fix = acc.get("problemas", {}).get(key) or (
            "Reintentá con documentación clara. Si persiste, usá un fallback: "
            + ", ".join(self._resolve_name(f) for f in acc.get("fallbacks", []))
        )
        state = self._load()
        state["qa"].append(
            {
                "q": f"[resolve] {account_id} - {problem}",
                "intent": "resolve",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        state["resolved"] = state.get("resolved", 0) + 1
        self._save(state)
        return {
            "success": True,
            "account": acc["name"],
            "problem": problem,
            "fix": fix,
            "fallbacks": [self._resolve_name(f) for f in acc.get("fallbacks", [])],
            "pasos": acc.get("pasos", []),
        }

    def _resolve_name(self, mid: str) -> str:
        for a in ACCOUNTS:
            if a["id"] == mid:
                return a["name"]
        return mid

    def _problem_key(self, problem: str) -> str:
        p = problem.lower()
        if "kyc" in p or "docu" in p or "selfie" in p or "verific" in p:
            return "verificacion" if "verific" in p else "kyc_rechazado"
        if any(
            k in p for k in ["reten", "retuv", "retuvo", "hold", "congel", "suspend", "cerrada", "demora", "espera"]
        ):
            if any(k in p for k in ["cerrada", "suspend"]):
                return "cuenta_cerrada"
            return "retencion"
        if "bloque" in p or "card" in p or "tarjeta" in p:
            return "card_bloqueada"
        if "llc" in p or "empresa" in p:
            return "llc"
        return "kyc_rechazado"

    def get_status(self) -> dict[str, Any]:
        s = self._load()
        return {
            "success": True,
            "accounts_total": len(ACCOUNTS),
            "qa_count": len(s.get("qa", [])),
            "resolved": s.get("resolved", 0),
            "last": (s.get("qa") or [])[-1],
        }

    def get_accounts(self) -> dict[str, Any]:
        return {"success": True, "total": len(ACCOUNTS), "accounts": ACCOUNTS}

    def recommend_accounts(self, purpose: str) -> list[dict[str, Any]]:
        """Recomendar cuentas según propósito."""
        return [a for a in ACCOUNTS if not a["llc_needed"] or purpose == "llc"]


_guru: FinanceGuru | None = None


def get_finance_guru() -> FinanceGuru:
    global _guru
    if _guru is None:
        _guru = FinanceGuru()
    return _guru
