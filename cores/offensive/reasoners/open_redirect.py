"""Open Redirect Reasoner — Unvalidated redirects and forwards.

Detecta endpoints que redirigen a URLs controladas por el usuario sin
validar el destino (phishing, robo de tokens OAuth, bypass de SSO).

Seguridad por construcción: análisis estático de parámetros. Solo objetivos
autorizados o laboratorio propio.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import OPEN_REDIRECT_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.open_redirect")

# Fragmentos de path que suelen implementar redirección
REDIRECT_PATHS: dict[str, float] = {
    "/redirect": 0.95,
    "/login": 0.8,
    "/logout": 0.6,
    "/callback": 0.7,
    "/oauth": 0.8,
    "/auth": 0.7,
    "/sso": 0.75,
    "/saml": 0.7,
    "/continue": 0.85,
    "/next": 0.85,
    "/return": 0.8,
    "/goto": 0.9,
    "/forward": 0.8,
    "/r/": 0.7,
    "/url/": 0.7,
    "/link/": 0.6,
}

# Claves de query/body que llevan URLs de redirección
REDIRECT_KEYS: dict[str, float] = {
    "redirect": 0.95,
    "redirect_url": 0.95,
    "redirect_uri": 0.95,
    "next": 0.9,
    "return_url": 0.9,
    "return_to": 0.9,
    "continue": 0.85,
    "goto": 0.9,
    "url": 0.8,
    "link": 0.7,
    "target": 0.7,
    "destination": 0.75,
    "callback": 0.7,
    "callback_url": 0.8,
    "success_url": 0.8,
    "failure_url": 0.7,
    "logout_url": 0.6,
    "post_logout_redirect_uri": 0.7,
}

# Dominios de confianza conocidos (heurística para bajar confianza)
TRUSTED_TLDS = (".gov", ".edu", ".mil")


class OpenRedirectReasoner(BaseReasoner):
    """Analiza endpoints para redirecciones abiertas no validadas."""

    @property
    def vulnerability_type(self) -> str:
        return "open_redirect"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        path_lower = (endpoint.path or "").lower()
        for frag, score in REDIRECT_PATHS.items():
            if frag in path_lower:
                signals.append(f"Redirect endpoint path: {frag}")
                confidence += score * 0.45

        blob_keys = [str(k) for k in (endpoint.body or {})]
        blob_keys += list(endpoint.query_params)
        lowered = {k.lower(): k for k in blob_keys}

        for low, orig in lowered.items():
            if low in REDIRECT_KEYS:
                signals.append(f"Redirect parameter: {orig}")
                params_of_interest.append(orig)
                confidence += REDIRECT_KEYS[low] * 0.35

                # Verificar si el valor actual parece una URL absoluta externa
                bv = (endpoint.body or {}).get(orig) or next(
                    (v for k, v in endpoint.query_params if k.lower() == low), ""
                )
                if isinstance(bv, str) and bv.startswith(("http://", "https://")):
                    # Comprobar si es dominio externo (heurística simple)
                    signals.append(f"Absolute external URL in {orig}: {bv[:50]}")
                    confidence += 0.2

        # Login/logout/callback con redirect = mayor riesgo (phishing, token theft)
        if any(frag in path_lower for frag in ("/login", "/logout", "/callback", "/oauth", "/auth", "/sso", "/saml")):
            signals.append("Auth-related redirect endpoint")
            confidence += 0.25

        if confidence < 0.2 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = "medium" if confidence >= 0.5 else "low"

        return [
            Hypothesis(
                vulnerability_type="open_redirect",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential open redirect via {', '.join(params_of_interest[:3])} on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} accepts redirect parameters "
                    f"({', '.join(params_of_interest[:4])}) that may not validate the destination. "
                    f"Open redirects enable phishing, OAuth token theft, and SSO bypass."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} is an auth-related redirect with {len(signals)} indicators. "
                    f"Open redirect pays $200-5k and chains to account takeover."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Confirm scope covers open redirect testing.",
                    "Test with an external URL you control: https://yourdomain.com/callback?test=1",
                    "Verify the browser redirects to your domain (check network tab for 302/301).",
                    "Test protocol-relative: //evil.com — some validators miss this.",
                    "Test data: URI scheme: data:text/html,<script>alert(1)</script> — bypasses some filters.",
                    "Test javascript: URI: javascript:alert(1) — executes in victim context.",
                    "Test with OAuth flow: redirect_uri=https://evil.com — check if auth code leaks.",
                    "Do NOT test on live user accounts. Use your own test accounts.",
                    "Stop at first successful external redirect. Test ONLY authorized targets or your own lab.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in OPEN_REDIRECT_ALTERNATIVES.get("open_redirect", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope and redirect testing is allowed. "
                    f"Redirects are low-impact. Test ONLY authorized targets or your own lab."
                ),
                reproducibility_notes=("Same redirect URL, same response. Consistent 302 to external = reproducible."),
            )
        ]
