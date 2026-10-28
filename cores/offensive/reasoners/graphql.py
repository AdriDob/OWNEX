"""GraphQL Reasoner — endpoints GraphQL con impacto alto.

Detecta superficie GraphQL (path, query/mutation/variables) y genera
hipótesis sobre: introspección expuesta, límites de profundidad/complejidad,
batching, y autorización a nivel de campo (cruce con IDOR/BACL).

Seguridad por construcción: las instrucciones de prueba usan introspección
mínima, profundidad acotada (sin DoS) y batching pequeño. Solo objetivos
autorizados o laboratorio propio.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import GRAPHQL_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.graphql")

# Fragmentos de path que delatan endpoint GraphQL
GRAPHQL_PATHS: dict[str, float] = {
    "/graphql": 0.95,
    "/gql": 0.9,
    "/graph": 0.6,
    "/query": 0.55,
    "/api/graphql": 0.95,
    "/v1/graphql": 0.9,
    "/graphql/console": 0.85,
    "/graphiql": 0.9,
    "/playground": 0.75,
}

# Claves de body/query que llevan operaciones GraphQL
GRAPHQL_KEYS: dict[str, float] = {
    "query": 0.9,
    "mutation": 0.9,
    "operationname": 0.7,
    "operation_name": 0.7,
    "variables": 0.8,
}

# Variables con pinta de referencia a objeto (cruce IDOR/BACL a nivel campo)
IDISH_VARIABLES = ("id", "ids", "user_id", "userid", "account_id", "order_id", "node_id")

MAX_SAFE_DEPTH = 7
MAX_SAFE_BATCH = 5


class GraphQLReasoner(BaseReasoner):
    """Analiza endpoints GraphQL: introspección, costo, batching, authz."""

    @property
    def vulnerability_type(self) -> str:
        return "graphql"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        path_lower = (endpoint.path or "").lower()
        for frag, score in GRAPHQL_PATHS.items():
            if frag in path_lower:
                signals.append(f"GraphQL endpoint path: {frag}")
                confidence += score * 0.4

        blob_keys = [str(k) for k in (endpoint.body or {})]
        blob_keys += list(endpoint.query_params)
        lowered = {k.lower(): k for k in blob_keys}
        has_operation = False
        for low, orig in lowered.items():
            if low in GRAPHQL_KEYS:
                signals.append(f"GraphQL operation key: {orig}")
                params_of_interest.append(orig)
                confidence += GRAPHQL_KEYS[low] * 0.35
                if low in ("query", "mutation"):
                    has_operation = True

        # Un nivel adentro (ej. variables: {user_id}): ahí viven los IDs
        try:
            nested: dict[str, str] = {}
            for bk, bv in (endpoint.body or {}).items():
                if isinstance(bv, dict):
                    for sk in bv:
                        nested[str(sk).lower()] = f"{bk}.{sk}"
        except (AttributeError, TypeError):
            nested = {}

        id_vars = [orig for low, orig in lowered.items() if low in IDISH_VARIABLES]
        id_vars += [dotted for low, dotted in nested.items() if low in IDISH_VARIABLES]
        if id_vars and has_operation:
            signals.append(f"Object-id variables inside operation: {', '.join(id_vars[:3])}")
            params_of_interest.extend(v for v in id_vars if v not in params_of_interest)
            confidence += 0.25

        if endpoint.method.upper() not in ("GET", "POST"):
            return []
        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        is_write = "mutation" in lowered
        severity = "high" if (is_write and id_vars) else ("medium" if confidence >= 0.4 else "low")

        return [
            Hypothesis(
                vulnerability_type="graphql",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential GraphQL flaws via {', '.join(params_of_interest[:3])} "
                f"on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} accepts GraphQL "
                    f"operations ({', '.join(params_of_interest[:4])}). Misconfigured "
                    f"GraphQL APIs expose introspection, ignore query cost/depth limits, "
                    f"allow batched abuse, or skip field-level authorization — each of "
                    f"which pays as High/Critical in public programs."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} is a GraphQL surface ({len(signals)} indicators) "
                    f"where scanners only check the front door. Schema + cost + authz "
                    f"bugs duplicate the least and pay the most."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Confirm scope covers GraphQL testing before sending any query.",
                    "Send the minimal introspection query {__schema{queryType{name}}} and "
                    "record whether the full schema leaks.",
                    f"Probe depth limits with nesting capped at {MAX_SAFE_DEPTH} levels (never DoS the endpoint).",
                    f"Test batching with at most {MAX_SAFE_BATCH} aliases in one request; watch for rate-limit bypass.",
                    "Replay a field query as two roles and diff object-level fields (field-level IDOR/BACL).",
                    "If schema leaks, cost is unenforced, batching bypasses limits, or "
                    "cross-role fields differ — save request/response as PoC.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in GRAPHQL_ALTERNATIVES.get("graphql", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope and GraphQL testing is allowed. "
                    f"Keep queries cheap and few; stop at first proof. Test ONLY "
                    f"authorized targets or your own lab."
                ),
                reproducibility_notes=(
                    "Fixed minimal query, fresh session per run. Same leak/bypass twice in a row = reproducible."
                ),
            )
        ]
