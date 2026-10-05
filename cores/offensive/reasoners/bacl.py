"""BACL + Business-Flow Reasoners — autorización por rol y lógica de negocio.

Dos reasoners complementarios sobre la misma superficie:

- BaclMatrixReasoner ("bacl"): el mismo objeto visto por N roles. Detecta
  referencias a objetos combinadas con indicadores de rol (params, headers,
  paths duales /user vs /admin). La prueba es comparar respuestas por rol.
- BusinessFlowReasoner ("business_logic"): flujos multi-paso con dinero o
  estado (checkout, cupones, créditos, reembolsos). Detecta montos y
  transiciones controlables por el cliente en métodos con efecto.

Scope honesty: solo objetivos autorizados; las pruebas de matriz exigen
dos cuentas propias del programa (o del laboratorio local).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.reasoners.idor import OBJECT_REFERENCE_KEYWORDS
from cores.offensive.templates import BACL_ALTERNATIVES, BUSINESS_FLOW_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.bacl")

# Indicadores de rol en params/headers — el eje de la matriz
ROLE_KEYWORDS: dict[str, float] = {
    "role": 0.9,
    "user_role": 0.9,
    "user_type": 0.85,
    "is_admin": 0.95,
    "isadmin": 0.9,
    "admin": 0.8,
    "tier": 0.7,
    "plan": 0.7,
    "scope": 0.75,
    "group": 0.6,
    "tenant": 0.75,
    "organization_id": 0.8,
    "org_id": 0.8,
    "team_id": 0.7,
    "privilege": 0.85,
    "access_level": 0.8,
}

AUTH_MARKERS = ("authorization", "cookie", "session", "x-auth", "bearer", "token")

# Flujos con dinero/estado + params que nunca debería fijar el cliente
FLOW_KEYWORDS: dict[str, float] = {
    "checkout": 0.85,
    "payment": 0.9,
    "order": 0.7,
    "coupon": 0.9,
    "discount": 0.85,
    "credit": 0.8,
    "wallet": 0.85,
    "transfer": 0.9,
    "withdraw": 0.95,
    "refund": 0.9,
    "cart": 0.7,
    "invoice": 0.75,
    "subscription": 0.8,
    "upgrade": 0.75,
    "trial": 0.7,
    "balance": 0.8,
    "redeem": 0.85,
}

MONEY_PARAMS: dict[str, float] = {
    "price": 0.95,
    "amount": 0.95,
    "total": 0.9,
    "quantity": 0.8,
    "qty": 0.75,
    "discount": 0.85,
    "balance": 0.8,
    "fee": 0.7,
    "currency": 0.6,
}

STATE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Matriz guiada: roles a comparar (cuentas propias del programa o lab).
MATRIX_ROLES = ("low", "owner", "admin")
MAX_MATRIX_CASES = 50


def _resource_of(path: str) -> str:
    """Normaliza /api/users/42 → /api/users/{}. Agrupa el mismo objeto."""
    parts = []
    for p in path.split("/"):
        if not p:
            continue
        if p.startswith("{") and p.endswith("}") or re.fullmatch(r"\d+", p) or re.fullmatch(r"[0-9a-fA-F-]{8,}", p):
            parts.append("{}")
        else:
            parts.append(p.lower())
    return "/" + "/".join(parts)


def build_bacl_test_matrix(endpoints: list[EndpointInfo]) -> list[dict[str, Any]]:
    """Matriz rol×objeto×método por recurso. Pura, determinista, capada.

    Agrupa endpoints por recurso normalizado y emite casos testeables:
    replay cross-rol del mismo objeto, tamper de role-param y cruce de
    paths duales user/admin. Solo endpoints con refs de objeto o roles.
    P1 = admin+objeto, P2 = objeto, P3 = solo rol. Nunca ejecuta nada.
    """
    groups: dict[str, list[EndpointInfo]] = {}
    for ep in endpoints or []:
        if not isinstance(ep, EndpointInfo):
            continue
        groups.setdefault(_resource_of(ep.path), []).append(ep)

    cases: list[dict[str, Any]] = []
    for resource, eps in sorted(groups.items()):
        obj_params: list[str] = []
        role_params: list[str] = []
        has_admin_path = False
        has_user_path = False
        for ep in eps:
            for n in _names(ep):
                low = n.lower()
                if low in OBJECT_REFERENCE_KEYWORDS and n not in obj_params:
                    obj_params.append(n)
                if low in ROLE_KEYWORDS and n not in role_params:
                    role_params.append(n)
            parts = [p.lower() for p in ep.path.split("/") if p]
            has_admin_path = has_admin_path or any(p in parts for p in ("admin", "internal", "manage"))
            has_user_path = has_user_path or any(p in parts for p in ("user", "users", "account"))
        if not obj_params and not role_params:
            continue
        methods = sorted({e.method.upper() for e in eps})
        priority = "P1" if (has_admin_path and obj_params) else ("P2" if obj_params else "P3")
        for method in methods:
            if obj_params:
                cases.append(
                    {
                        "resource": resource,
                        "method": method,
                        "kind": "cross_role_replay",
                        "object_param": obj_params[0],
                        "roles": [MATRIX_ROLES[0], MATRIX_ROLES[1]],
                        "action": f"Replay {method} {resource} with the other role's object id; diff field by field.",
                        "priority": priority,
                    }
                )
            for rp in role_params:
                cases.append(
                    {
                        "resource": resource,
                        "method": method,
                        "kind": "role_param_tamper",
                        "object_param": obj_params[0] if obj_params else "",
                        "roles": [MATRIX_ROLES[0]],
                        "action": f"Tamper param '{rp}' upward on {method} {resource}; repeat headerless.",
                        "priority": priority,
                    }
                )
        if has_admin_path and has_user_path:
            cases.append(
                {
                    "resource": resource,
                    "method": methods[0],
                    "kind": "dual_path_cross",
                    "object_param": obj_params[0] if obj_params else "",
                    "roles": [MATRIX_ROLES[0], MATRIX_ROLES[2]],
                    "action": f"Request the user-path object via the admin-path twin on {resource} as low role.",
                    "priority": "P1",
                }
            )
        if len(cases) >= MAX_MATRIX_CASES:
            break
    return cases[:MAX_MATRIX_CASES]


def _names(endpoint: EndpointInfo) -> list[str]:
    out: list[str] = list(endpoint.query_params) + list(endpoint.path_params)
    if endpoint.body:
        out.extend(str(k) for k in endpoint.body)
    out.extend(str(k) for k in (endpoint.headers or {}))
    return out


def _has_auth(endpoint: EndpointInfo) -> bool:
    blob = " ".join([endpoint.path] + list((endpoint.headers or {}).keys())).lower()
    return any(m in blob for m in AUTH_MARKERS)


class BaclMatrixReasoner(BaseReasoner):
    """Compara el mismo objeto entre roles: BACL/IDOR complejo."""

    @property
    def vulnerability_type(self) -> str:
        return "bacl"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH", "DELETE"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        names = _names(endpoint)
        lowered = {n.lower(): n for n in names}

        # ── Signal 1: referencia a objeto (reusa keywords IDOR) ──
        obj_refs = [n for n in names if n.lower() in OBJECT_REFERENCE_KEYWORDS]
        for ref in obj_refs:
            signals.append(f"Object reference testable per-role: {ref}")
            params_of_interest.append(ref)
            confidence += OBJECT_REFERENCE_KEYWORDS[ref.lower()] * 0.3

        # ── Signal 2: indicadores de rol ─────────────────────────
        for low, orig in lowered.items():
            if low in ROLE_KEYWORDS:
                signals.append(f"Role indicator caller-visible: {orig}")
                params_of_interest.append(orig)
                confidence += ROLE_KEYWORDS[low] * 0.35

        # ── Signal 3: paths duales (mismo recurso, distinto prefijo) ──
        parts = [p.lower() for p in endpoint.path.split("/") if p]
        if "admin" in parts and any(k in OBJECT_REFERENCE_KEYWORDS for k in parts):
            signals.append("Admin path over object reference: role split surface")
            confidence += 0.3
        if any(p in parts for p in ("user", "users", "account")) and any(
            p in parts for p in ("admin", "internal", "manage")
        ):
            signals.append("User/admin path split on one endpoint tree")
            confidence += 0.2

        # ── Signal 4: auth + objeto = matriz testeable ───────────
        if _has_auth(endpoint) and obj_refs:
            signals.append("Authenticated endpoint over object reference: matrix testable")
            confidence += 0.2

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        is_admin = "admin" in parts
        severity = "high" if (is_admin and obj_refs) else ("medium" if confidence >= 0.4 else "low")

        return [
            Hypothesis(
                vulnerability_type="bacl",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential BACL gap via {', '.join(params_of_interest[:3])} "
                f"on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} combines object "
                    f"references ({', '.join(params_of_interest[:4])}) with role-visible "
                    f"surface. If authorization is checked per-endpoint instead of "
                    f"per-object-per-role, a lower-privilege caller may reach data or "
                    f"actions reserved for another role."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} exposes {params_of_interest[0] if params_of_interest else 'object refs'} "
                    f"across a role split ({len(signals)} BACL indicators). Role-matrix "
                    f"bugs pay as High and duplicate far less than scanner findings."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Create two accounts with different roles (e.g., member + admin, or A + B tenants).",
                    "Request the same object identifier as each role and diff the responses field by field.",
                    "Tamper any role indicator param; repeat with the header/cookie removed.",
                    "If a lower role sees cross-role data or executes the action — document both transcripts as PoC.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in BACL_ALTERNATIVES.get("bacl", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope and that two test accounts are "
                    f"allowed. Test ONLY authorized targets or your own lab."
                ),
                reproducibility_notes=(
                    "Same identifier, two roles, same timestamp window. Re-run twice: "
                    "stable diff across runs = reproducible."
                ),
            )
        ]


class BusinessFlowReasoner(BaseReasoner):
    """Flujos con dinero/estado fijados por el cliente."""

    @property
    def vulnerability_type(self) -> str:
        return "business_logic"

    def supported_methods(self) -> list[str]:
        return ["POST", "PUT", "PATCH", "DELETE"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        if endpoint.method.upper() not in STATE_METHODS:
            return []
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        path_lower = endpoint.path.lower()
        for frag, score in FLOW_KEYWORDS.items():
            if frag in path_lower:
                signals.append(f"Money/state flow in path: {frag}")
                confidence += score * 0.35

        for name in _names(endpoint):
            low = name.lower()
            if low in FLOW_KEYWORDS:
                signals.append(f"Flow keyword in parameter: {name}")
                params_of_interest.append(name)
                confidence += FLOW_KEYWORDS[low] * 0.3
            if low in MONEY_PARAMS:
                signals.append(f"Client-controlled money param: {name}")
                params_of_interest.append(name)
                confidence += MONEY_PARAMS[low] * 0.35

        money_hit = any(p.lower() in MONEY_PARAMS for p in params_of_interest)
        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = "high" if money_hit else ("medium" if confidence >= 0.4 else "low")

        return [
            Hypothesis(
                vulnerability_type="business_logic",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential business-logic flaw via {', '.join(params_of_interest[:3])} "
                f"on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} advances a money/state "
                    f"flow with caller-controlled values ({', '.join(params_of_interest[:4])}). "
                    f"If the server trusts them instead of recomputing, an attacker may alter "
                    f"price, quantity, discount or skip flow steps."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} lets the caller set {params_of_interest[0] if params_of_interest else 'flow values'} "
                    f"({len(signals)} flow indicators). Scanners cannot reason about "
                    f"business rules, so these duplicate the least and pay as High."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Map the full flow first (all steps in order) before touching anything.",
                    "Tamper the money param (price/amount/quantity/discount) up and down; observe server recomputation.",
                    "Replay steps out of order and skip steps (e.g., pay step) to test the state machine.",
                    "Reuse single-use values (coupons, tokens) twice; double-submit to probe idempotency.",
                    "If the server honors the tampered value — record request/response pair as PoC.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in BUSINESS_FLOW_ALTERNATIVES.get("business_logic", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope. Never complete real payments with "
                    f"tampered values beyond a reversible test amount; prefer staging/test cards."
                ),
                reproducibility_notes=(
                    "Fixed tampered value, fresh session per run. Same server-side effect "
                    "twice in a row = reproducible."
                ),
            )
        ]
