"""CORS Reasoner — Cross-Origin Resource Sharing misconfiguration.

Detecta endpoints con políticas CORS permisivas que permiten orígenes
arbitrarios, credenciales, o métodos/headers peligrosos.

Seguridad por construcción: análisis pasivo de headers. Solo objetivos
autorizados o laboratorio propio.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import CORS_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.cors")

# Fragmentos de path que suelen exponer APIs con CORS
CORS_PATHS: dict[str, float] = {
    "/api/": 0.5,
    "/v1/": 0.4,
    "/v2/": 0.4,
    "/graphql": 0.6,
    "/webhook": 0.5,
    "/callback": 0.5,
    "/oauth": 0.5,
    "/auth": 0.5,
    "/login": 0.4,
    "/register": 0.4,
    "/user": 0.5,
    "/account": 0.5,
    "/profile": 0.5,
}

# Headers que delatan configuración CORS (se analizan en respuesta real, no estático)
CORS_RESPONSE_HEADERS = (
    "access-control-allow-origin",
    "access-control-allow-credentials",
    "access-control-allow-methods",
    "access-control-allow-headers",
    "access-control-expose-headers",
    "access-control-max-age",
)


class CORSReasoner(BaseReasoner):
    """Analiza endpoints para misconfiguración CORS (estático)."""

    @property
    def vulnerability_type(self) -> str:
        return "cors"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        # Este reasoner estático solo genera hipótesis; la confirmación real
        # requiere petición OPTIONS/GET real (ProbeEngine / hunt_endpoint)
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        path_lower = (endpoint.path or "").lower()
        for frag, score in CORS_PATHS.items():
            if frag in path_lower:
                signals.append(f"CORS-sensitive API path: {frag}")
                confidence += score * 0.3

        # Endpoints que devuelven datos sensibles son candidatos prioritarios
        sensitive_indicators = (
            "user",
            "account",
            "profile",
            "email",
            "token",
            "key",
            "secret",
            "password",
            "credit",
            "payment",
            "wallet",
            "balance",
        )
        for bk, bv in (endpoint.body or {}).items():
            if isinstance(bv, str) and any(si in bk.lower() for si in sensitive_indicators):
                signals.append(f"Sensitive data indicator in {bk}")
                confidence += 0.15
                if bk not in params_of_interest:
                    params_of_interest.append(bk)

        # Métodos que mutan + CORS permisivo = mayor riesgo
        if endpoint.method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            signals.append(f"Mutating method {endpoint.method} with potential CORS exposure")
            confidence += 0.2

        if confidence < 0.2 or not signals:
            return []

        confidence = min(confidence, 1.0)
        severity = "medium" if confidence >= 0.4 else "low"

        return [
            Hypothesis(
                vulnerability_type="cors",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential CORS misconfiguration on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} may have a permissive CORS policy "
                    f"allowing arbitrary origins to read responses or send credentialed requests. "
                    f"This enables cross-origin data theft and CSRF-like attacks."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} handles sensitive data and CORS misconfig pays $500-5k. "
                    f"Often missed by automated scanners."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Confirm scope covers CORS testing before sending any request.",
                    "Send an OPTIONS request with Origin: https://evil.com and check Access-Control-Allow-Origin.",
                    "Test with Origin: null and Origin: https://subdomain.target.com.",
                    "Verify Access-Control-Allow-Credentials: true with a reflecting origin.",
                    "Check Access-Control-Allow-Methods for dangerous methods (PUT, DELETE, PATCH).",
                    "Test preflight bypass: send actual request (not OPTIONS) with custom headers.",
                    "If any arbitrary origin is reflected with credentials — save as PoC.",
                    "Test ONLY authorized targets or your own lab.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in CORS_ALTERNATIVES.get("cors", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope and CORS testing is allowed. "
                    f"OPTIONS requests are low-impact. Test ONLY authorized targets or your own lab."
                ),
                reproducibility_notes=("Same Origin header, same response. Consistent reflection = reproducible."),
            )
        ]
