"""Chain Analyzer — análisis de impacto combinado, NUNCA ejecución (P1).

Toma findings confirmados + contexto y produce HIPÓTESIS de cadena:
qué combinaciones (A+B) podrían elevar impacto, con prerrequisitos,
confianza explícita, riesgo de novedad y pasos de validación humana.

- Puro y determinista: dicts in, sin DB, sin red, sin requests.
- NO ejecuta nada, NO genera payloads, NO prueba exploits. El output
  termina SIEMPRE en validación humana (Human Gate).
- La confianza tiene techo 0.85: esto es análisis, no prueba.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.offensive.chain_analyzer")

MAX_CONFIDENCE = 0.85


@dataclass(slots=True)
class ChainRule:
    """Un patrón de combinación conocido: qué necesita y qué promete."""

    rule_id: str
    needs: frozenset[str]  # tipos de vuln requeridos (al menos uno de cada grupo llega por receta)
    needs_groups: tuple[frozenset[str], ...] = ()  # grupos: un finding de CADA grupo
    same_target: bool = True  # la cadena exige mismo target (si no, penaliza)
    impact: str = ""
    severity: str = "high"  # severidad RESULTANTE estimada
    evidence_required: tuple[str, ...] = ()
    validation_steps: tuple[str, ...] = ()
    base_confidence: float = 0.6
    novelty_risk: str = "medium"  # low | medium | high (prob. de que ya sea conocido/duplicado)


@dataclass(slots=True)
class ChainHypothesis:
    rule_id: str
    finding_ids: list[str]
    prerequisites: list[str]
    relationship: str
    expected_impact: str
    severity: str
    confidence: float
    novelty_risk: str
    evidence_required: list[str]
    human_validation_steps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": f"{self.rule_id}:{'+'.join(sorted(self.finding_ids))}",
            "rule_id": self.rule_id,
            "finding_ids": list(self.finding_ids),
            "prerequisites": list(self.prerequisites),
            "relationship": self.relationship,
            "expected_impact": self.expected_impact,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "novelty_risk": self.novelty_risk,
            "evidence_required": list(self.evidence_required),
            "human_validation_steps": list(self.human_validation_steps),
        }


def _norm(vuln_type: object) -> str:
    return str(vuln_type or "unknown").strip().lower()


def list_rules() -> list[ChainRule]:
    """10 patrones de combinación. Tabla explícita, cero magia."""
    return [
        ChainRule(
            rule_id="cors_plus_session",
            needs=frozenset({"cors_misconfiguration", "session_exposure", "token_exposure"}),
            needs_groups=(frozenset({"cors_misconfiguration"}), frozenset({"session_exposure", "token_exposure"})),
            impact="Account Takeover vía sesión/token leído cross-origin",
            severity="critical",
            evidence_required=("origen permitido responde con credenciales", "token/sesión válido capturado"),
            validation_steps=(
                "confirmar Access-Control-Allow-Credentials real",
                "probar lectura de sesión desde origen atacante",
                "demostrar uso de la sesión (NO automatizar daño)",
            ),
            base_confidence=0.6,
            novelty_risk="medium",
        ),
        ChainRule(
            rule_id="open_redirect_plus_token",
            needs=frozenset({"open_redirect", "token_in_url", "session_in_url"}),
            needs_groups=(frozenset({"open_redirect"}), frozenset({"token_in_url", "session_in_url"})),
            impact="Robo de token/sesión vía redirect (phishing + ATO)",
            severity="high",
            evidence_required=("redirect abierto confirmado", "token/sesión presente en URL redirigida"),
            validation_steps=(
                "confirmar redirect a dominio externo",
                "verificar parámetro con token en la URL",
                "evaluar exploitabilidad sin enviar a terceros",
            ),
            base_confidence=0.6,
            novelty_risk="medium",
        ),
        ChainRule(
            rule_id="ssrf_to_cloud",
            needs=frozenset({"ssrf", "ssrf_blind", "cloud_metadata", "internal_access"}),
            needs_groups=(frozenset({"ssrf", "ssrf_blind"}), frozenset({"cloud_metadata", "internal_access"})),
            impact="Credenciales cloud internas / pivote a red interna (camino a RCE)",
            severity="critical",
            evidence_required=("SSRF confirmado (callback/DNS)", "alcance a metadata o servicio interno"),
            validation_steps=(
                "confirmar SSRF ciego con collaborator propio",
                "probar metadata cloud SOLO en scope autorizado",
                "documentar credenciales alcanzables sin exfiltrar de más",
            ),
            base_confidence=0.55,
            novelty_risk="medium",
        ),
        ChainRule(
            rule_id="idor_mass_extraction",
            needs=frozenset({"idor"}),
            needs_groups=(frozenset({"idor"}), frozenset({"collection_endpoint", "user_enumeration"})),
            impact="Extracción masiva de PII vía iteración de IDs",
            severity="high",
            evidence_required=("IDOR en 1 objeto", "colección enumerable o IDs predecibles"),
            validation_steps=(
                "confirmar IDOR en 2 objetos propios",
                "medir enumerabilidad (NO extraer datos ajenos)",
                "estimar volumen expuesto por diseño",
            ),
            base_confidence=0.65,
            novelty_risk="high",
        ),
        ChainRule(
            rule_id="auth_bypass_to_privileged",
            needs=frozenset({"auth_bypass", "privileged_api", "admin_endpoint"}),
            needs_groups=(frozenset({"auth_bypass"}), frozenset({"privileged_api", "admin_endpoint"})),
            impact="Escalada a funciones privilegiadas/admin",
            severity="critical",
            evidence_required=("bypass de auth confirmado", "endpoint privilegiado alcanzado"),
            validation_steps=(
                "confirmar bypass sin credenciales",
                "mapear acciones privilegiadas expuestas",
                "demostrar 1 acción de impacto mínimo",
            ),
            base_confidence=0.6,
            novelty_risk="medium",
        ),
        ChainRule(
            rule_id="stored_xss_to_admin",
            needs=frozenset({"xss_stored", "admin_panel", "session_exposure"}),
            needs_groups=(frozenset({"xss_stored"}), frozenset({"admin_panel", "session_exposure"})),
            impact="Takeover de cuenta admin vía XSS almacenado",
            severity="critical",
            evidence_required=("XSS almacenado que persiste", "vista por rol privilegiado"),
            validation_steps=(
                "confirmar persistencia del payload",
                "verificar quién lo renderiza (rol)",
                "PoC benigno: NO robar sesiones reales",
            ),
            base_confidence=0.55,
            novelty_risk="medium",
        ),
        ChainRule(
            rule_id="sqli_to_rce_path",
            needs=frozenset({"sqli", "sqli_stacked", "file_read", "file_write"}),
            needs_groups=(frozenset({"sqli", "sqli_stacked"}), frozenset({"file_read", "file_write"})),
            impact="Camino SQLi → lectura/escritura de archivos → posible RCE",
            severity="critical",
            evidence_required=("inyección confirmada", "primitiva de archivo vía SQL"),
            validation_steps=(
                "confirmar inyección ciega/basada en tiempo",
                "probar lectura de archivo inocuo permitido",
                "detenerse antes de escritura: proponer Human Gate",
            ),
            base_confidence=0.5,
            novelty_risk="low",
        ),
        ChainRule(
            rule_id="leaked_key_to_api_abuse",
            needs=frozenset({"secret_in_js", "api_key_exposure", "authenticated_api"}),
            needs_groups=(frozenset({"secret_in_js", "api_key_exposure"}), frozenset({"authenticated_api"})),
            impact="Abuso de API autenticada con clave filtrada",
            severity="high",
            evidence_required=("clave/secreto en bundle público", "API que la acepta con acciones sensibles"),
            validation_steps=(
                "extraer clave del bundle",
                "probar 1 llamada de solo lectura",
                "medir alcance de escritura sin ejecutar",
            ),
            base_confidence=0.65,
            novelty_risk="high",
        ),
        ChainRule(
            rule_id="prompt_injection_to_tool_abuse",
            needs=frozenset({"prompt_injection", "tool_execution", "mcp_tool"}),
            needs_groups=(frozenset({"prompt_injection"}), frozenset({"tool_execution", "mcp_tool"})),
            impact="Acción no autorizada / exfiltración vía tool del agente",
            severity="high",
            evidence_required=("inyección obedecida (transcript)", "tool ejecutada por instrucción inyectada"),
            validation_steps=(
                "practicar primero en ai_lab",
                "medir tasa con repro harness (≥50%)",
                "transcript completo como evidencia",
            ),
            base_confidence=0.6,
            novelty_risk="low",
        ),
        ChainRule(
            rule_id="rate_limit_missing_to_takeover",
            needs=frozenset({"no_rate_limit", "credential_stuffing", "login_endpoint"}),
            needs_groups=(frozenset({"no_rate_limit"}), frozenset({"credential_stuffing", "login_endpoint"})),
            impact="Takeover a escala vía credential stuffing sin freno",
            severity="high",
            evidence_required=("ausencia de rate limit medida", "endpoint de login con sesiones reales"),
            validation_steps=(
                "medir rate limit con pocas requests propias",
                "NO lanzar stuffing masivo",
                "demostrar con 1 cuenta propia + cálculo de escala",
            ),
            base_confidence=0.55,
            novelty_risk="high",
        ),
        ChainRule(
            rule_id="bacl_to_privilege",
            needs=frozenset({"bacl", "admin_endpoint", "privileged_api"}),
            needs_groups=(frozenset({"bacl"}), frozenset({"admin_endpoint", "privileged_api"})),
            impact="Escalada de rol vía objeto + endpoint privilegiado alcanzado",
            severity="critical",
            evidence_required=("BACL confirmada en 1 objeto", "endpoint admin/privilegiado resuelto"),
            validation_steps=(
                "confirmar BACL con 2 cuentas propias",
                "resolver el endpoint privilegiado sin ejecutar acciones",
                "demostrar 1 lectura mínima o proponer Human Gate",
            ),
            base_confidence=0.6,
            novelty_risk="medium",
        ),
        ChainRule(
            rule_id="flow_value_on_foreign_object",
            needs=frozenset({"business_logic", "bacl", "idor"}),
            needs_groups=(frozenset({"business_logic"}), frozenset({"bacl", "idor"})),
            impact="Manipulación de precio/cantidad/estado sobre objeto ajeno",
            severity="high",
            evidence_required=("parámetro de valor controlado por cliente", "objeto ajeno direccionable"),
            validation_steps=(
                "mapear el flujo completo antes de tocar nada",
                "tamper de valor solo sobre objetos propios",
                "nunca completar pagos reales con valores alterados",
            ),
            base_confidence=0.55,
            novelty_risk="high",
        ),
    ]


def analyze(
    findings: list[dict[str, Any]],
    target_context: dict[str, Any] | None = None,
) -> list[ChainHypothesis]:
    """Evalúa combinaciones y retorna hipótesis ordenadas por confianza.

    findings: [{id, vulnerability_type, target?, severity?}]. target por defecto
    es el de target_context o "default" (mismo target asumido si ausente).
    Puro: sin DB, sin red. Nunca ejecuta nada.
    """
    cleaned: list[dict[str, str]] = []
    for f in findings or []:
        fid = str(f.get("id", "")).strip()
        if not fid:
            continue
        target = str(f.get("target") or (target_context or {}).get("target") or "default")
        cleaned.append({"id": fid, "type": _norm(f.get("vulnerability_type")), "target": target})

    out: list[ChainHypothesis] = []
    for rule in list_rules():
        groups = rule.needs_groups or (rule.needs,)
        picked: list[dict[str, str]] = []
        ok = True
        for group in groups:
            match = next((c for c in cleaned if c["type"] in group and c["id"] not in {p["id"] for p in picked}), None)
            if match is None:
                ok = False
                break
            picked.append(match)
        if not ok:
            continue
        targets = {p["target"] for p in picked}
        cross_target = len(targets) > 1
        confidence = rule.base_confidence
        notes: list[str] = []
        if rule.same_target and cross_target:
            confidence -= 0.15
            notes.append("cross-target: la cadena exige mismo target (penaliza)")
        if len(picked) < 2 and rule.needs_groups:
            confidence -= 0.1
            notes.append("cobertura parcial de grupos")
        confidence = max(0.05, min(MAX_CONFIDENCE, confidence))
        types = "+".join(sorted({p["type"] for p in picked}))
        out.append(
            ChainHypothesis(
                rule_id=rule.rule_id,
                finding_ids=[p["id"] for p in picked],
                prerequisites=[f"finding {p['id']} ({p['type']}) confirmado" for p in picked]
                + ([f"mismo target verificado (hoy: {'|'.join(sorted(targets))})"] if rule.same_target else []),
                relationship=f"{types} en target {sorted(targets)[0]}"
                + (" [CROSS-TARGET: verificar]" if cross_target else ""),
                expected_impact=rule.impact + (" " + " ".join(f"({n})" for n in notes) if notes else ""),
                severity=rule.severity,
                confidence=confidence,
                novelty_risk=rule.novelty_risk,
                evidence_required=list(rule.evidence_required),
                human_validation_steps=list(rule.validation_steps),
            )
        )
    out.sort(key=lambda h: h.confidence, reverse=True)
    return out


def analyze_chains_for_finding(
    session: Any,
    finding_id: int,
    min_confidence: float = 0.5,
    max_others: int = 50,
) -> list[dict[str, Any]]:
    """Busca cadenas que involucren un finding contra sus vecinos de target.

    Lee otros findings del mismo target (status open/confirmed), corre
    ``analyze()`` y retorna solo hipótesis que incluyen al finding nuevo con
    confianza >= min_confidence, como dicts listos para persistir/mostrar.

    Best-effort: cualquier error (DB, modelos) retorna []. Nunca raisea,
    nunca ejecuta nada, nunca muta nada — solo lee y analiza.
    """
    try:
        from database import models

        row = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if row is None:
            return []
        target_key = str(getattr(row, "target_id", "") or "")
        if not target_key:
            return []
        others = (
            session.query(models.Finding)
            .filter(models.Finding.target_id == row.target_id)
            .filter(models.Finding.id != finding_id)
            .filter(models.Finding.status.in_(["open", "confirmed"]))
            .limit(max_others)
            .all()
        )
        feed: list[dict[str, Any]] = [
            {
                "id": str(finding_id),
                "vulnerability_type": getattr(row, "vulnerability_type", "unknown"),
                "target": target_key,
            }
        ]
        for other in others or []:
            oid = getattr(other, "id", None)
            if oid is None or int(oid) == int(finding_id):
                continue
            feed.append(
                {
                    "id": str(oid),
                    "vulnerability_type": getattr(other, "vulnerability_type", "unknown"),
                    "target": target_key,
                }
            )
        mine = str(finding_id)
        return [h.to_dict() for h in analyze(feed) if mine in h.finding_ids and h.confidence >= min_confidence]
    except Exception as exc:
        logger.warning("chain_analyzer: no se pudo analizar cadenas para finding %s: %s", finding_id, exc)
        return []
