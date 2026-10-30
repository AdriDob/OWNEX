"""Race Condition Reasoner — TOCTOU / Concurrency flaws.

Detecta endpoints donde operaciones no atómicas permiten condiciones de carrera:
check-then-act, double-spend, limit bypass, reward duplication, etc.

Seguridad por construcción: pruebas conceptuales, sin DoS. Solo objetivos
autorizados o laboratorio propio.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import RACE_CONDITION_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.race_condition")

# Fragmentos de path que sugieren operaciones de estado mutables
RACE_PATHS: dict[str, float] = {
    "/checkout": 0.85,
    "/purchase": 0.9,
    "/buy": 0.85,
    "/order": 0.8,
    "/payment": 0.85,
    "/transfer": 0.8,
    "/withdraw": 0.9,
    "/deposit": 0.75,
    "/reward": 0.8,
    "/claim": 0.85,
    "/redeem": 0.8,
    "/coupon": 0.75,
    "/voucher": 0.75,
    "/gift": 0.7,
    "/promo": 0.7,
    "/invite": 0.7,
    "/signup": 0.6,
    "/register": 0.6,
    "/vote": 0.7,
    "/like": 0.6,
    "/follow": 0.6,
    "/rate": 0.6,
    "/review": 0.6,
    "/comment": 0.5,
    "/submit": 0.6,
    "/apply": 0.65,
}

# Claves que indican operaciones de estado / límites
RACE_KEYS: dict[str, float] = {
    "quantity": 0.7,
    "amount": 0.8,
    "coupon": 0.85,
    "voucher": 0.85,
    "promo_code": 0.85,
    "referral": 0.7,
    "invite_code": 0.7,
    "user_id": 0.5,
    "account_id": 0.5,
    "wallet_id": 0.6,
    "balance": 0.6,
    "limit": 0.6,
    "max": 0.5,
    "count": 0.5,
}

# Métodos que mutan estado (candidatos a race)
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class RaceConditionReasoner(BaseReasoner):
    """Analiza endpoints para condiciones de carrera (TOCTOU)."""

    @property
    def vulnerability_type(self) -> str:
        return "race_condition"

    def supported_methods(self) -> list[str]:
        return ["POST", "PUT", "PATCH"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        if endpoint.method.upper() not in MUTATING_METHODS:
            return []

        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        path_lower = (endpoint.path or "").lower()
        for frag, score in RACE_PATHS.items():
            if frag in path_lower:
                signals.append(f"Race condition target path: {frag}")
                confidence += score * 0.45

        blob_keys = [str(k) for k in (endpoint.body or {})]
        blob_keys += list(endpoint.query_params)
        lowered = {k.lower(): k for k in blob_keys}
        for low, orig in lowered.items():
            if low in RACE_KEYS:
                signals.append(f"Race-sensitive key: {orig}")
                params_of_interest.append(orig)
                confidence += RACE_KEYS[low] * 0.3

        # Heurística: endpoints que devuelven balances, contadores, o estados
        for bk, bv in (endpoint.body or {}).items():
            if isinstance(bv, (int, float)) and bk.lower() in ("balance", "amount", "quantity", "count", "limit"):
                signals.append(f"Mutable numeric state in {bk}")
                confidence += 0.15

        if confidence < 0.15 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = "high" if confidence >= 0.5 else ("medium" if confidence >= 0.3 else "low")

        return [
            Hypothesis(
                vulnerability_type="race_condition",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential race condition via {', '.join(params_of_interest[:3])} on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} performs a state-mutating operation "
                    f"({', '.join(params_of_interest[:4])}) that may be vulnerable to concurrent request "
                    f"exploitation. Race conditions enable double-spend, limit bypass, reward duplication."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} is a financial/state-changing endpoint with {len(signals)} race indicators. "
                    f"Race conditions pay $1k-20k+ and are often missed by scanners."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Confirm scope covers race condition testing (many programs exclude it).",
                    "Use Turbo Intruder (single-packet attack) or equivalent to send 10-20 concurrent requests.",
                    "Target a coupon/claim/reward endpoint with a known valid code.",
                    "Observe if multiple requests succeed (should be 1). Compare response codes and returned balances.",
                    "For transfer/withdraw: send concurrent identical requests; check if balance decreases multiple times.",
                    "Do NOT target payment processing endpoints (high risk of real charges).",
                    "Stop at first proof of duplicate effect. Test ONLY authorized targets or your own lab.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in RACE_CONDITION_ALTERNATIVES.get("race_condition", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope and race condition testing is explicitly allowed. "
                    f"Many programs prohibit it. Use minimal concurrency. Test ONLY "
                    f"authorized targets or your own lab."
                ),
                reproducibility_notes=(
                    "Same coupon/code, same session, 10-20 concurrent requests. Duplicate success twice = reproducible."
                ),
            )
        ]
