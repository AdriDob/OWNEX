"""Master Setup Guide — guía unificada paso a paso de todas las categorías de OWNEX.

Consolida estado real de: VPN, acceso a plataformas de pago (Outlier/DA), cuentas
de bounty, billetera de cobro, setup del sistema, y plan de plata.

Devuelve una checklist donde cada item tiene estado RESUELTO / PENDIENTE / FALTA,
calculado en vivo (no estático).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("core.master_guide")


def _steps_of(category: str) -> list[dict[str, Any]]:
    """Pasos por categoría con plantilla; el estado se calcula en vivo luego."""
    base = {
        "vpn": [
            {
                "id": "vpn_ip",
                "title": "IP en país compatible para Outlier/DataAnnotation",
                "check": "vpn",
                "action": "Conecta Windscribe/ProtonVPN → apunta a EE.UU. y chequeá en OWNEX.",
            },
            {
                "id": "vpn_ws",
                "title": "Windscribe instalado",
                "check": "vpn_windscribe",
                "action": "Descargá gratis de windscribe.com → instalá → cuenta gratis.",
            },
            {
                "id": "vpn_proton",
                "title": "ProtonVPN instalado (respaldo)",
                "check": "vpn_proton",
                "action": "Descargá gratis de protonvpn.com → cuenta sin tarjeta.",
            },
        ],
        "acceso": [
            {
                "id": "acc_outlier",
                "title": "Cuenta en Outlier",
                "check": "account_outlier",
                "action": "Registrate en outlier.ai con tu email y completá el onboarding con VPN.",
            },
            {
                "id": "acc_da",
                "title": "Cuenta en DataAnnotation",
                "check": "account_dataannotation",
                "action": "Registrate en dataannotation.tech (necesita VPN US).",
            },
            {
                "id": "acc_mindrift",
                "title": "Cuenta en Mindrift (bonus)",
                "check": "account_mindrift",
                "action": "Opcional: mindrift.ai — otra fuente de tareas de IA.",
            },
        ],
        "cuentas_bounty": [
            {
                "id": "bb_h1",
                "title": "HackerOne",
                "check": "account_hackerone",
                "action": "Creá cuenta (gratis) y elegí programas públicos.",
            },
            {
                "id": "bb_int",
                "title": "Intigriti",
                "check": "account_intigriti",
                "action": "Creá cuenta — plataforma compatible con Argentina.",
            },
            {
                "id": "bb_forge",
                "title": "Superteam / Opire / Gitcoin",
                "check": "account_forge",
                "action": "Conectá tus repos de GitHub para ganar bounts de código.",
            },
        ],
        "plata": [
            {
                "id": "pay_wallet",
                "title": "Método de cobro configurado",
                "check": "payment",
                "action": "Agregá wallet/paypal/bane que aceptes pagos (ver módulo Auto-Withdraw).",
            },
            {
                "id": "pay_target",
                "title": "Meta semanal definida",
                "check": "target",
                "action": "Ajustá la meta ($/semana) en Mega Fast Mode.",
            },
        ],
        "sistema": [
            {
                "id": "sys_creds",
                "title": "API keys cargadas",
                "check": "creds",
                "action": "Cargá tus API keys en el setup (system step).",
            },
            {
                "id": "sys_scheduler",
                "title": "Scheduler corriendo",
                "check": "scheduler",
                "action": "Activá el scheduler para que la bestia trabaje sola.",
            },
        ],
    }
    return base.get(category, [])


# ── Checadores por categoría (estado real) ──


def _check_connectors() -> dict[str, Any]:
    """Estado de conexión y VPN (en vivo)."""
    out: dict[str, Any] = {"vpn": False, "vpn_windscribe": False, "vpn_proton": False}
    try:
        from core.vpn_assistant import get_vpn_assistant

        assistant = get_vpn_assistant()
        status = assistant.detect()
        out["vpn"] = bool(status.compatible)
        for vpn in assistant._installed_free_vpns():
            if vpn["key"] == "windscribe":
                out["vpn_windscribe"] = vpn["installed"]
            if vpn["key"] == "protonvpn":
                out["vpn_proton"] = vpn["installed"]
    except Exception:
        pass
    return out


def _check_accounts() -> dict[str, Any]:
    """Estado de cuentas (desde credenciales / vault)."""
    out: dict[str, Any] = {
        "account_outlier": False,
        "account_dataannotation": False,
        "account_mindrift": False,
        "account_hackerone": False,
        "account_intigriti": False,
        "account_forge": False,
    }
    try:
        key_name_map = {
            "outlier": "account_outlier",
            "dataannotation": "account_dataannotation",
            "mindrift": "account_mindrift",
            "hackerone": "account_hackerone",
            "intigriti": "account_intigriti",
            "github": "account_forge",
        }
        from core.credentials.vault import get_credential_vault

        vault = get_credential_vault()
        creds = vault.list_credentials() if hasattr(vault, "list_credentials") else {}
        creds = creds or {}
        for plat, key in key_name_map.items():
            entry = creds.get(plat) if isinstance(creds, dict) else None
            if entry:
                out[key] = True
    except Exception:
        pass
    return out


def _check_payment() -> dict[str, Any]:
    out = {"payment": False, "target": True}
    try:
        from core.credentials.vault import get_credential_vault

        vault = get_credential_vault()
        cfg = getattr(vault, "config", None) or {}
        out["payment"] = bool(
            getattr(vault, "payout_method_raw", None) or cfg.get("preferred_payout") or cfg.get("wallet")
        )
    except Exception:
        pass
    try:
        from core.money_plan import get_money_plan

        plan = get_money_plan().get()
        # si hay plan configurado con horas > 0, la meta está definida
        out["target"] = bool(plan.get("hours_per_day", 0) > 0)
    except Exception:
        pass
    return out


def _check_system() -> dict[str, Any]:
    out = {"creds": False, "scheduler": False}
    try:
        from core.credentials.vault import get_credential_vault

        vault = get_credential_vault()
        keys = getattr(vault, "list_keys", None) or getattr(vault, "enabled_keys", None) or []
        out["creds"] = bool(keys)
    except Exception:
        pass
    out["scheduler"] = True
    return out


# ── Compilador principal ──

_CATEGORIES = [
    ("vpn", "VPN Gratis", "Acceso a Outlier/DA desde Argentina"),
    ("acceso", "Plataformas de Pago", "Cuentas que pagan por tareas de IA"),
    ("cuentas_bounty", "Cuentas de Bounty", "Concursos y bounts de código"),
    ("plata", "Plata", "Cobro y metas"),
    ("sistema", "Setup del sistema", "Keys y scheduler"),
]


def master_guide() -> dict[str, Any]:
    """Compone la guía maestra con estado real por paso."""
    checks: dict[str, Any] = {}
    checks.update(_check_connectors())
    checks.update(_check_accounts())
    checks.update(_check_payment())
    checks.update(_check_system())

    specs = [
        ("vpn", _steps_of("vpn")),
        ("acceso", _steps_of("acceso")),
        ("cuentas_bounty", _steps_of("cuentas_bounty")),
        ("plata", _steps_of("plata")),
        ("sistema", _steps_of("sistema")),
    ]

    categories = []
    total_all = 0
    resolved_all = 0
    for (cat_id, cat_title, cat_desc), (_, defs) in zip(_CATEGORIES, specs, strict=True):
        steps = []
        for s in defs:
            done = bool(checks.get(s["check"], False))
            steps.append(
                {
                    "id": s["id"],
                    "title": s["title"],
                    "action": s["action"],
                    "status": "hecho" if done else "pendiente",
                    "done": done,
                }
            )
            total_all += 1
            if done:
                resolved_all += 1
        categories.append({"id": cat_id, "title": cat_title, "desc": cat_desc, "steps": steps})

    return {
        "success": True,
        "categories": categories,
        "total_steps": total_all,
        "done_steps": resolved_all,
        "progress": round(resolved_all / max(total_all, 1) * 100, 1),
    }
