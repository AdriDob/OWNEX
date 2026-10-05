"""Owned Financial Autopilot — cierra el loop "OWNEX decide sola dónde poner tu hora".

Lee 3 fuentes de verdad (nunca inventa):
- ``economic_feedback.engine.compute_channel_economics()`` → net/h real, P(CASH),
  verdict SCALE/KEEP/PAUSE por canal (de outcomes verificados).
- ``ecommerce.EcommerceEngine.portfolio_funnel()`` → MATAR/ESCALAR por producto.
- ``workspaces.economics/economics_for()`` → $/h del workspace.

Acciones AUTOMÁTICAS (solo con evidencia dura):
- PAUSE: pausa el workspace (state override) cuando un canal con `attempted >= 5`
  tiene `0 PAID` (kill 40h/$0 día 60 codificado). Reversible con /mission-hub/workspaces/{id}/activate.
- MATAR producto: marca DISCONTINUED un producto con 0 ventas ≥ 60d.
- Nunca toca trading (CAPITAL_ONLY) ni backup (LAST_RESORT).

Solo-lectura, best-effort: un error en una fuente jamás rompe el job.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.autopilot_kill_scale")

# Kill rule codificada: 40h invertidas sin PAID → pausa (PERSONAL_CONTEXT §7 foco).
KILL_MIN_HUMAN_HOURS = 40.0
KILL_MIN_ATTEMPTS = 5
KILL_MIN_ATTEMPTS_NOHOURS = 8  # sin horas medidas, 8 intentos con 0 PAID basta
MATAR_MIN_DAYS_LIVE = 60  # 0 ventas ≥60d → MATAR (pineado por tests ecommerce)

_PAUSE_KEYWORDS = ("pause", "0 PAID", "degenera", "pausar")


@dataclass
class AutopilotDecision:
    workspace: str
    action: str  # SCALE | PAUSE | KEEP | MATAR | ESCALAR
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    reversible: bool = True


@dataclass
class AutopilotResult:
    generated_at: str
    decisions: list[AutopilotDecision] = field(default_factory=list)
    auto_applied: int = 0
    skipped: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "auto_applied": self.auto_applied,
            "note": self.note,
            "skipped": self.skipped,
            "decisions": [asdict(d) for d in self.decisions],
        }


def _workspace_for_channel(channel: str) -> str | None:
    """channel (plataforma) → workspace id. Best-effort, sin inventar."""
    p = (channel or "").lower()
    bug = ("hackerone", "bugcrowd", "intigriti", "yeswehack", "immunefi", "hackenproof", "huntr")
    dev = (
        "algora",
        "opire",
        "issuehunt",
        "bountyboard",
        "polar",
        "gitpay",
        "github",
        "dework",
        "superteam",
        "gitcoin",
        "fiverr",
    )
    aiw = ("outlier", "mindrift", "alignerr", "mercor", "dataannotation", "kaggle", "prolific")
    if any(k in p for k in bug):
        return "bug_bounty"
    if any(k in p for k in dev):
        return "dev_bounty"
    if any(k in p for k in aiw):
        return "ai_training"
    if "shopify" in p or "mercado" in p or "meli" in p or "m_mercado" in p:
        return "mercado_libre"
    if "instagram" in p or "facebook" in p or "whatsapp" in p:
        return "droppinglabel"
    if "webs" in p or "client" in p or "web_services" in p:
        return "adriel_webs"
    return None


def _protected_workspaces(registry) -> set[str]:
    """Trading (CAPITAL_ONLY) + backup (LAST_RESORT) jamás se auto-pausan."""
    protected: set[str] = set()
    try:
        from cores.workspaces.policies import income_role
        from cores.workspaces.registry import WorkspaceType

        for wt in WorkspaceType:
            try:
                role = income_role(wt)
                if role.value in ("capital_only", "last_resort"):
                    protected.add(wt.value)
            except Exception:
                continue
    except Exception as exc:
        logger.warning("autopilot: policies no disponible, protejo por nombre: %s", exc)
        protected = {"trading", "backup_income", "ownex"}
    return protected


def decide_channel_actions(channels: list[Any]) -> list[AutopilotDecision]:
    """Decisión por canal desde channel_economics (verdict ya calculado)."""
    decisions: list[AutopilotDecision] = []
    for ch in channels:
        ws = _workspace_for_channel(ch.channel)
        if not ws:
            continue
        verdict = str(getattr(ch, "verdict", "UNKNOWN") or "UNKNOWN")
        attempted = int(getattr(ch, "attempted", 0) or 0)
        paid = int(getattr(ch, "paid", 0) or 0)
        hours = float(getattr(ch, "human_hours", 0) or 0)
        net_h = getattr(ch, "net_per_hour", None)
        reason = str(getattr(ch, "note", "") or "")
        rev = True  # toda acción autopilot reversible
        # REGLA KILL (40h/$0 ó 8 intentos/$0): pausa con evidencia
        if (
            paid == 0
            and attempted >= KILL_MIN_ATTEMPTS
            and (hours >= KILL_MIN_HUMAN_HOURS or attempted >= KILL_MIN_ATTEMPTS_NOHOURS)
        ):
            decisions.append(
                AutopilotDecision(
                    workspace=ws,
                    action="PAUSE",
                    reason=f"Kill rule: {attempted} intentos / {hours:.0f}h / 0 PAID → pausar, horas a canal con net/h mayor",
                    evidence={"attempted": attempted, "paid": paid, "human_hours": round(hours, 1)},
                    reversible=rev,
                )
            )
            continue
        # PAUSE explícito del feedback (net/h < umbral)
        if verdict == "PAUSE" and paid == 0:
            decisions.append(
                AutopilotDecision(
                    workspace=ws,
                    action="PAUSE",
                    reason=reason or f"{attempted} intentos sin PAID → pausar",
                    evidence={"verdict": verdict, "attempted": attempted},
                    reversible=rev,
                )
            )
            continue
        # SCALE con evidencia
        if verdict == "SCALE" and net_h is not None:
            decisions.append(
                AutopilotDecision(
                    workspace=ws,
                    action="SCALE",
                    reason=f"${net_h:.0f}/h realizado → escalar (es tu canal que más paga por hora)",
                    evidence={"net_per_hour": net_h, "paid": paid},
                    reversible=rev,
                )
            )
            continue
        if paid > 0 and verdict == "KEEP":
            decisions.append(
                AutopilotDecision(
                    workspace=ws,
                    action="KEEP",
                    reason=reason or f"{paid} PAID → mantener",
                    evidence={"paid": paid},
                    reversible=rev,
                )
            )
    return decisions


def _apply_pause(workspace: str) -> bool:
    """Deactiva un workspace vía mission_hub state (reversible)."""
    from api.routers.mission_hub import _load_state, _save_state

    try:
        state = _load_state()
        state.setdefault("workspace_active", {})
        state["workspace_active"][workspace] = False
        _save_state(state)
        return True
    except Exception as exc:
        logger.warning("autopilot: no pude pausar %s: %s", workspace, exc)
        return False


def _apply_matars(products: list[dict]) -> int:
    """Marca DISCONTINUED los productos MATAR del funnel (reversible)."""
    applied = 0
    try:
        from cores.ecommerce.engine import get_ecommerce_engine

        engine = get_ecommerce_engine()
        from cores.ecommerce.models import ProductStatus

        for p in products or []:
            pid = p.get("product_id") or p.get("id")
            status = str(p.get("verdict", ""))
            if pid and status == "MATAR":
                # ya oculto por el clasificador si DISCONTINUED; solo aplicamos si aún ACTIVE
                prod = engine.get_product(pid)
                if prod and prod.status != ProductStatus.DISCONTINUED:
                    engine.update_product(pid, status=ProductStatus.DISCONTINUED)
                    applied += 1
                    logger.info("[AUTOPILOT] MATAR producto %s (0 ventas ≥60d)", pid)
    except Exception as exc:
        logger.warning("autopilot: productos MATAR falló: %s", exc)
    return applied


def run_autopilot(apply: bool = True) -> AutopilotResult:
    """Corre el autopilot: decide + aplica PAUSE (workspace) y MATAR (producto).

    Con ``apply=False`` devuelve las decisiones sin tocar nada (dry-run).
    Nunca raisea: un error de fuente → esa parte se omite.
    """
    res = AutopilotResult(generated_at=datetime.now(UTC).isoformat())
    decisions: list[AutopilotDecision] = []

    # 1. Channels: feedback (net/h real, P(CASH), verdict)
    with contextlib.suppress(Exception):
        from cores.economic_feedback.engine import compute_channel_economics

        decisions += decide_channel_actions(compute_channel_economics())

    # 2. Productos: ecommerce funnel (MATAR/ESCALAR)
    matars: list[dict] = []
    with contextlib.suppress(Exception):
        from cores.ecommerce.engine import get_ecommerce_engine

        engine = get_ecommerce_engine()
        perf = engine.product_performance(platform_fee_pct=0.0)
        funnel = engine.portfolio_funnel(platform_fee_pct=0.0)
        for row in perf or []:
            v = str(row.get("verdict", "") or "")
            if v == "MATAR":
                matars.append(row)
                decisions.append(
                    AutopilotDecision(
                        workspace="mercado_libre",
                        action="MATAR",
                        reason=row.get("note", f"0 ventas ≥{MATAR_MIN_DAYS_LIVE}d → discontinuar producto"),
                        evidence={"product_id": row.get("product_id"), "sales_30d": row.get("sales_30d")},
                        reversible=True,
                    )
                )
        # funnel también puede traer lista
        for row in funnel.get("to_kill", []) or []:
            if isinstance(row, dict) and row.get("verdict") == "MATAR":
                matars.append(row)
                decisions.append(
                    AutopilotDecision(
                        workspace="mercado_libre",
                        action="MATAR",
                        reason="portfolio_funnel → MATAR",
                        evidence={"product_id": row.get("product_id")},
                        reversible=True,
                    )
                )

    # 3. Proteger trading/backup/ownex de auto-pausa
    protected: set[str] = set()
    with contextlib.suppress(Exception):
        from cores.workspaces.registry import get_workspace_registry

        protected = _protected_workspaces(get_workspace_registry())
    protected |= {"trading", "backup_income", "ownex"}

    # 4. Aplicar PAUSE a workspaces (solo los no protegidos) + MATAR a productos
    applied = 0
    _paused_set: set[str] = set()
    for d in decisions:
        if d.action == "PAUSE":
            if d.workspace in protected:
                res.skipped.append(f"{d.workspace}: protegido (no se auto-pausa)")
                continue
            if d.workspace in _paused_set:
                continue  # ya pausado previamente, no duplicar
            if apply and _apply_pause(d.workspace):
                _paused_set.add(d.workspace)
                applied += 1
                d.evidence["applied"] = True
            d.evidence["would_apply"] = apply
        elif d.action == "MATAR":
            if apply:
                count = _apply_matars([{"product_id": d.evidence.get("product_id"), "verdict": "MATAR"}])
                applied += count
                if count:
                    d.evidence["applied"] = True

    res.decisions = decisions
    res.auto_applied = applied
    if not decisions:
        res.note = "Sin decisiones con evidencia dura. P(CASH) UNKNOWN hasta 1er PAID — el autopilot no inventa."
    elif res.auto_applied > 0:
        res.note = f"{res.auto_applied} acciones aplicadas (pausa de canales muertos + productos MATAR). Reversible desde /mission-hub/workspaces."
    else:
        res.note = "Decisiones calculadas; nada que aplicar todavía (o requires apply=False dry-run)."
    return res


def run_autopilot_scheduler() -> dict[str, Any]:
    """Entry para scheduler — nunca raisea."""
    try:
        return run_autopilot(apply=True).to_dict()
    except Exception as exc:
        logger.error("[AUTOPILOT] run_autopilot_scheduler falló: %s", exc)
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "auto_applied": 0,
            "note": f"error: {exc}",
            "decisions": [],
            "skipped": [],
        }
