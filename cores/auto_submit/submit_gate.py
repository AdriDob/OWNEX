"""Submit Gate — choke point único antes de enviar un reporte (P-accept máxima).

Corre DESPUÉS del elite gate (severidad/confianza/evidencia ya validadas) y
agrega los 3 checks de aceptación que el elite gate no cubre:

1. scope verificado (OUT_OF_SCOPE y UNKNOWN bloquean: fail-closed)
2. reproducibilidad MEDIDA (IA: tasa ≥50% exigida; web: texto repro + nota si sin medir)
3. no-duplicado (ya enviado antes → aparca, no reenvía)

Nada se descarta: lo bloqueado va a la cola de revisión con el motivo.
Aprobación manual humana siempre hace bypass (el humano manda).
Puro en el núcleo (`submit_gate`); el adaptador DB (`submit_gate_for_finding`)
resuelve scope/dedupe best-effort y nunca raisea.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ownex.auto_submit.gate")

# Tipos de vuln que exigen tasa de reproducción MEDIDA (no basta texto).
# Hoy solo existe el reasoner prompt_injection; ampliar cuando aterricen
# nuevos reasoners IA (jailbreak, mcp_attack, ...).
AI_VULN_TYPES = frozenset({"prompt_injection"})

# Umbral OpenAI Safety para prompt injection (requisito documentado).
AI_REPRO_THRESHOLD = 0.5


@dataclass(slots=True)
class SubmitGateInput:
    """Entradas ya resueltas (sin DB, sin red)."""

    scope: str = "unknown"  # in_scope | unknown | out_of_scope
    vulnerability_type: str = "unknown"
    measured_rate: float | None = None  # tasa medida 0-1 o None si sin medir
    has_repro_text: bool = False  # pasos de reproducción escritos
    already_submitted: bool = False  # este finding ya se envió antes


@dataclass(slots=True)
class GateCheck:
    check: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"check": self.check, "passed": self.passed, "detail": self.detail}


@dataclass(slots=True)
class SubmitGateResult:
    allow_submit: bool
    parked_reason: str | None = None
    checks: list[GateCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow_submit": self.allow_submit,
            "parked_reason": self.parked_reason,
            "checks": [c.to_dict() for c in self.checks],
        }


def submit_gate(inp: SubmitGateInput) -> SubmitGateResult:
    """Aplica los 3 checks. Puro: sin DB, sin red, sin side effects."""
    checks: list[GateCheck] = []

    scope = (inp.scope or "unknown").strip().lower()
    if scope == "out_of_scope":
        checks.append(GateCheck("scope", False, "OUT_OF_SCOPE: envío bloqueado"))
        return SubmitGateResult(False, "out_of_scope", checks)
    if scope != "in_scope":
        # Fail-closed (spec §1/§22/§79: NO SCOPE -> NO ACTION). Antes pasaba con
        # nota "no inventa bloqueo"; pero "no sé si está en scope" NO es
        # autorización para enviar un reporte a un tercero. El bloqueo dice
        # exactamente qué falta para desbloquear.
        checks.append(
            GateCheck(
                "scope",
                False,
                f"scope sin verificar ({scope}): envío bloqueado. Registrá la "
                "ProgramScopePolicy del programa para habilitarlo.",
            )
        )
        return SubmitGateResult(False, "scope_not_verified", checks)
    checks.append(GateCheck("scope", True, "in_scope verificado"))

    vuln = (inp.vulnerability_type or "unknown").strip().lower()
    rate = inp.measured_rate
    if vuln in AI_VULN_TYPES:
        if rate is None:
            checks.append(GateCheck("measured_repro", False, "IA sin tasa medida: correr repro harness (≥50%)"))
            return SubmitGateResult(False, "needs_measured_repro", checks)
        if rate < AI_REPRO_THRESHOLD:
            checks.append(GateCheck("measured_repro", False, f"tasa {rate:.0%} bajo umbral 50%"))
            return SubmitGateResult(False, "repro_below_threshold", checks)
        checks.append(GateCheck("measured_repro", True, f"tasa medida {rate:.0%} ≥ 50%"))
    else:
        if not inp.has_repro_text:
            checks.append(GateCheck("measured_repro", False, "sin pasos de reproducción escritos"))
            return SubmitGateResult(False, "missing_repro_steps", checks)
        checks.append(
            GateCheck(
                "measured_repro",
                True,
                "pasos escritos presentes" + ("" if rate is None else f" + tasa medida {rate:.0%}"),
            )
        )

    if inp.already_submitted:
        checks.append(GateCheck("dedupe", False, "ya enviado antes: no reenviar"))
        return SubmitGateResult(False, "duplicate", checks)
    checks.append(GateCheck("dedupe", True, "sin envío previo registrado"))

    return SubmitGateResult(True, None, checks)


def submit_gate_for_finding(finding_id: int, measured_rate: float | None = None) -> SubmitGateResult:
    """Adaptador DB: resuelve scope/dedupe/repro-texto y corre el gate.

    Nunca raisea. Scope sin verificar (UNKNOWN) y finding inexistente →
    bloquea (fail-closed): no se envía a un tercero sin evidencia de scope.
    Un error de DB también bloquea: sin verificación no hay autorización.
    """
    try:
        from database import db, models
    except Exception as exc:
        logger.warning("submit_gate: sin DB: %s", exc)
        return SubmitGateResult(False, "no_db", [GateCheck("scope", False, "sin acceso a DB")])

    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding:
            return SubmitGateResult(False, "finding_not_found", [GateCheck("scope", False, "finding inexistente")])

        vuln_type = (finding.vulnerability_type or "unknown").lower()
        desc = (finding.description or "") + " " + (finding.notes or "")
        has_repro_text = any(
            k in desc.lower() for k in ("steps to reproduce", "reproduction", "steps:", "to reproduce")
        )

        scope = _resolve_scope(session, models, finding)
        already = _was_submitted(session, models, finding_id)
        return submit_gate(
            SubmitGateInput(
                scope=scope,
                vulnerability_type=vuln_type,
                measured_rate=measured_rate,
                has_repro_text=has_repro_text,
                already_submitted=already,
            )
        )
    except Exception as exc:
        logger.warning("submit_gate: error resolviendo finding %s: %s", finding_id, exc)
        # Sin DB no hay forma de verificar scope => no hay autorización (fail-closed).
        return SubmitGateResult(
            False,
            "scope_not_verified",
            [GateCheck("scope", False, f"error resolviendo scope: {exc}: envío bloqueado")],
        )
    finally:
        session.close()


def _resolve_scope(session: Any, models: Any, finding: Any) -> str:
    """in_scope | unknown | out_of_scope. Sin policy registrada → unknown."""
    try:
        from cores.scope_enforcement import get_scope_enforcer

        target = session.query(models.Target).filter(models.Target.id == finding.target_id).first()
        if not target:
            return "unknown"
        endpoint_url = ""
        if finding.endpoint_id:
            ep = session.query(models.Endpoint).filter(models.Endpoint.id == finding.endpoint_id).first()
            base = (target.domain or "").strip()
            if ep is not None and base:
                path = (ep.path or "/").strip() or "/"
                endpoint_url = f"https://{base}{path if path.startswith('/') else '/' + path}"
        program_id = (target.name or "").split("_", 1)[0] if "_" in (target.name or "") else (target.name or "")
        enforcer = get_scope_enforcer()
        if endpoint_url:
            decision = enforcer.check_endpoint(program_id, endpoint_url)
        else:
            from cores.scope_enforcement import AssetType

            domain = target.domain or ""
            decision = enforcer.check_asset(program_id, AssetType.DOMAIN, domain)
        value = str(getattr(decision, "value", decision)).lower()
        if "out" in value:
            return "out_of_scope"
        if "in" in value:
            return "in_scope"
        return "unknown"
    except Exception as exc:
        logger.warning("submit_gate: scope no resoluble: %s", exc)
        return "unknown"


def _was_submitted(session: Any, models: Any, finding_id: int) -> bool:
    """True si algún report que incluye este finding ya se envió."""
    try:
        import json as _json

        reports = session.query(models.Report).all()
        report_ids: list[int] = []
        for rep in reports:
            try:
                ids = _json.loads(rep.finding_ids or "[]")
            except (TypeError, ValueError):
                continue
            if finding_id in ids:
                report_ids.append(rep.id)
        if not report_ids:
            return False
        return (
            session.query(models.SubmissionRecord)
            .filter(models.SubmissionRecord.report_id.in_(report_ids))
            .filter(models.SubmissionRecord.status.in_(["submitted", "accepted", "paid"]))
            .count()
            > 0
        )
    except Exception as exc:
        logger.warning("submit_gate: dedupe no resoluble: %s", exc)
        return False
