"""Setup Checklist — plan de configuración progresiva presentado como tarea diaria.

OWNEX presenta UNA tarea de configuración por día hasta llegar al 100% de
configuración para su óptimo uso diario. Los ítems con detección automática se
completan solos cuando el estado real del sistema los confirma (nunca se marca
done por decreto); los ítems de onboarding externo (assessments, perfiles en
plataformas de terceros) se marcan manual y persisten en ``data/setup_checklist.json``.

Reutiliza detectores existentes — cero duplicación (Regla de Oro):
- ProfileKitEngine.has_profile()            → perfil del usuario guardado
- PaymentCompatibilityEngine                → cuentas de pago configuradas
- core.credentials.vault.get_credentials()  → API keys de plataformas
- database SessionLocal(Target)             → al menos un target agregado
- VaultManager (Knowledge Bridge)           → vault de Obsidian conectado
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("core.setup.checklist")

STORE_FILENAME = "setup_checklist.json"

PHASE_ESSENTIALS = "essentials"
PHASE_PLATFORMS = "platforms"
PHASE_OPTIONAL = "optional"

PHASE_LABELS = {
    PHASE_ESSENTIALS: "Esencial para ingreso",
    PHASE_PLATFORMS: "Onboarding de plataformas",
    PHASE_OPTIONAL: "Opcional",
}

_AUTO = True
_MANUAL = False


def _default_store_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / STORE_FILENAME


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ── Detectores (introspeccionan estado real; nunca inventan) ──


def _detect_profile_kit() -> bool:
    try:
        from cores.direct_work_engine.profile_kit import ProfileKitEngine

        return bool(ProfileKitEngine().has_profile())
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector profile_kit falló: %s", exc)
        return False


def _detect_payment_accounts() -> bool:
    try:
        from cores.payment_compat.engine import PaymentCompatibilityEngine

        return len(PaymentCompatibilityEngine().get_configured_accounts()) > 0
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector payment_accounts falló: %s", exc)
        return False


def _detect_bounty_api_key() -> bool:
    try:
        from core.credentials.vault import get_credentials

        creds = get_credentials()
        return any(
            [
                getattr(creds, "hackerone_api_key", ""),
                getattr(creds, "bugcrowd_api_key", ""),
                getattr(creds, "intigriti_api_key", ""),
                getattr(creds, "yeswehack_api_key", ""),
                getattr(creds, "immunefi_api_key", ""),
            ]
        )
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector bounty_api_key falló: %s", exc)
        return False


def _detect_first_target() -> bool:
    try:
        from database.db import SessionLocal
        from database.models import Target

        with SessionLocal() as session:
            return session.query(Target.id).first() is not None
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector first_target falló: %s", exc)
        return False


def _detect_obsidian_vault() -> bool:
    try:
        from cores.knowledge import VaultManager, load_config

        info = VaultManager(load_config()).verify()
        return bool(info.connected)
    except Exception as exc:  # pragma: no cover - defensivo
        logger.warning("detector obsidian_vault falló: %s", exc)
        return False


def _detect_smtp_mail() -> bool:
    try:
        return bool(os.environ.get("OWNNEX_MAIL_SMTP_HOST"))
    except Exception:  # pragma: no cover - trivial
        return False


def _catalog() -> list[dict[str, Any]]:
    """Checklist curado, ordenado por prioridad dentro de cada fase."""
    return [
        {
            "id": "profile_kit",
            "phase": PHASE_ESSENTIALS,
            "priority": 1,
            "title": "Completar tu Profile Kit",
            "why": "Alimenta el autofill de TODAS las postulaciones y propuestas.",
            "est_minutes": 10,
            "how_to": "Panel Profile Kit → guardar nombre, skills, experiencia y links.",
            "auto": _AUTO,
        },
        {
            "id": "payment_accounts",
            "phase": PHASE_ESSENTIALS,
            "priority": 2,
            "title": "Marcar tus cuentas de cobro",
            "why": "El Payment Compatibility Engine verifica cobrabilidad ANTES de invertir tiempo.",
            "est_minutes": 15,
            "how_to": "Payment Network → marcar cuáles de las cuentas curadas ya tenés activas.",
            "auto": _AUTO,
        },
        {
            "id": "bounty_api_key",
            "phase": PHASE_ESSENTIALS,
            "priority": 3,
            "title": "Configurar al menos 1 API key de bug bounty",
            "why": "Habilita envío de reportes y sync de earnings (HackerOne/Bugcrowd/Intigriti/YesWeHack/Immunefi).",
            "est_minutes": 5,
            "how_to": "~/.config/ownex/opportunity.env → HACKERONE_API_KEY=<token> (Settings → API de la plataforma).",
            "auto": _AUTO,
        },
        {
            "id": "first_target",
            "phase": PHASE_ESSENTIALS,
            "priority": 4,
            "title": "Agregar tu primer target",
            "why": "Sin target no hay pipeline: recon → hipótesis → finding → reporte.",
            "est_minutes": 3,
            "how_to": "Botón 'Add Target' o `python run.py --add-target <nombre> --domain <dominio>`.",
            "auto": _AUTO,
        },
        {
            "id": "outlier_onboarding",
            "phase": PHASE_PLATFORMS,
            "priority": 1,
            "title": "Completar assessment inicial de Outlier",
            "why": "Plataforma AI-training #1 acepta Argentina directo; coding tier paga $8–18/h.",
            "est_minutes": 45,
            "how_to": "outlier.ai → registrarte con email real + completar prueba técnica. Argentina sin VPN.",
            "auto": _MANUAL,
        },
        {
            "id": "mindrift_onboarding",
            "phase": PHASE_PLATFORMS,
            "priority": 2,
            "title": "Crear cuenta y onboarding de Mindrift",
            "why": "Tareas de español nativo pagan mejor ($15–40/h); tu inglés técnico es un activo acá.",
            "est_minutes": 30,
            "how_to": "mindrift.ai → registro + perfil de escritura técnica es/en.",
            "auto": _MANUAL,
        },
        {
            "id": "freelance_profile",
            "phase": PHASE_PLATFORMS,
            "priority": 3,
            "title": "Perfil freelance verificado (Upwork/Fiverr)",
            "why": "Los textos ya los genera tu Profile Kit — solo pegarlos y verificar método de pago.",
            "est_minutes": 40,
            "how_to": "Copiar textos del Profile Kit → crear perfil → verificar payout (Payoneer/Airtm).",
            "auto": _MANUAL,
        },
        {
            "id": "obsidian_vault",
            "phase": PHASE_OPTIONAL,
            "priority": 1,
            "title": "Conectar vault de Obsidian",
            "why": "Tu conocimiento personal entra al pipeline: búsqueda híbrida + contexto para OWNEX.",
            "est_minutes": 5,
            "how_to": "POST /api/knowledge/connect con el path absoluto de tu vault.",
            "auto": _AUTO,
        },
        {
            "id": "smtp_mail",
            "phase": PHASE_OPTIONAL,
            "priority": 2,
            "title": "Configurar SMTP (verificación de email opcional)",
            "why": "Solo si querés verificación de email por usuario. Sin esto nada se rompe.",
            "est_minutes": 5,
            "how_to": ".env → OWNNEX_MAIL_SMTP_HOST/USER/PASSWORD (app password de Gmail).",
            "auto": _AUTO,
        },
        {
            "id": "trading_live",
            "phase": PHASE_OPTIONAL,
            "priority": 3,
            "title": "Habilitar trading LIVE (opcional, requiere decisión)",
            "why": "Hoy todo corre en DRY_RUN. Pasar a live mueve plata REAL — solo si lo decidís conscientemente.",
            "est_minutes": 30,
            "how_to": "API key de exchange + modo live explícito en TradingStore. Revisar drawdown settings primero.",
            "auto": _MANUAL,
        },
    ]


class SetupChecklist:
    """Plan guiado de configuración total, presentado como tarea diaria única."""

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = Path(store_path) if store_path else _default_store_path()

    # ── Persistencia (solo ítems manuales) ──

    def _load_state(self) -> dict[str, Any]:
        try:
            if self.store_path.exists():
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                if isinstance(data.get("manual_done"), dict):
                    return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("setup store corrupto, se reinicia: %s", exc)
        return {"manual_done": {}}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Estado ──

    def status(self) -> dict[str, Any]:
        state = self._load_state()
        manual_done: set[str] = set(state["manual_done"].keys())
        done: list[str] = []
        pending: list[dict[str, Any]] = []
        phases: dict[str, dict[str, int]] = {}
        for item in _catalog():
            phase_stats = phases.setdefault(item["phase"], {"total": 0, "done": 0})
            phase_stats["total"] += 1
            is_done = self._is_done(item, manual_done)
            if is_done:
                done.append(item["id"])
                phase_stats["done"] += 1
            else:
                pending.append(item)
        total = len(_catalog())
        pct = round(len(done) / total * 100) if total else 0
        next_task = self.next_daily_task(pending=pending)
        return {
            "generated_at": _now_iso(),
            "complete_pct": pct,
            "total_items": total,
            "done_items": len(done),
            "done": done,
            "pending": pending,
            "phases": {k: {"label": PHASE_LABELS[k], **v} for k, v in phases.items()},
            "next_task": next_task,
            "complete": not pending,
        }

    def _is_done(self, item: dict[str, Any], manual_done: set[str]) -> bool:
        detector: Callable[[], bool] | None = _DETECTORS.get(item["id"]) if item["auto"] else None
        if detector is not None:
            return detector()
        return item["id"] in manual_done

    def next_daily_task(self, pending: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
        """UNA tarea de config por día: fase esencial > plataformas > opcional,
        luego menor número de prioridad y menor esfuerzo."""
        pending = _catalog() if pending is None else pending
        if not pending:
            return None
        phase_rank = {PHASE_ESSENTIALS: 0, PHASE_PLATFORMS: 1, PHASE_OPTIONAL: 2}
        ordered = sorted(pending, key=lambda i: (phase_rank.get(i["phase"], 9), i["priority"], i["est_minutes"]))
        task = ordered[0]
        return {
            "id": task["id"],
            "phase": task["phase"],
            "phase_label": PHASE_LABELS[task["phase"]],
            "title": task["title"],
            "why": task["why"],
            "est_minutes": task["est_minutes"],
            "how_to": task["how_to"],
        }

    # ── Mutaciones ──

    def mark_done(self, item_id: str) -> dict[str, Any]:
        item = self._find_item(item_id)
        if item["auto"]:
            raise ValueError(f"'{item_id}' se completa solo por detección automática — no se puede marcar a mano")
        state = self._load_state()
        state["manual_done"].setdefault(item_id, {"done_at": _now_iso()})
        self._save_state(state)
        return {"success": True, "item": item_id}

    def mark_undone(self, item_id: str) -> dict[str, Any]:
        self._find_item(item_id)
        state = self._load_state()
        state["manual_done"].pop(item_id, None)
        self._save_state(state)
        return {"success": True, "item": item_id}

    def _find_item(self, item_id: str) -> dict[str, Any]:
        for item in _catalog():
            if item["id"] == item_id:
                return item
        raise KeyError(f"ítem desconocido: {item_id}")


_DETECTORS: dict[str, Callable[[], bool]] = {
    "profile_kit": _detect_profile_kit,
    "payment_accounts": _detect_payment_accounts,
    "bounty_api_key": _detect_bounty_api_key,
    "first_target": _detect_first_target,
    "obsidian_vault": _detect_obsidian_vault,
    "smtp_mail": _detect_smtp_mail,
}

_singleton: SetupChecklist | None = None


def get_setup_checklist() -> SetupChecklist:
    global _singleton
    if _singleton is None:
        _singleton = SetupChecklist()
    return _singleton
