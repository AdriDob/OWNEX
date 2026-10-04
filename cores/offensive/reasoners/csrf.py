"""CSRF Reasoner — Cross-Site Request Forgery.

Detecta endpoints mutantes sin protección CSRF (token, SameSite, doble envío,
header personalizado).

Seguridad por construcción: análisis estático de patrones. Solo objetivos
autorizados o laboratorio propio.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import CSRF_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.csrf")

# Fragmentos de path que suelen ser mutaciones de estado sensibles
CSRF_PATHS: dict[str, float] = {
    "/account": 0.9,
    "/profile": 0.85,
    "/settings": 0.9,
    "/password": 0.95,
    "/email": 0.95,
    "/phone": 0.85,
    "/address": 0.8,
    "/payment": 0.95,
    "/billing": 0.9,
    "/subscription": 0.85,
    "/delete": 0.9,
    "/remove": 0.85,
    "/transfer": 0.9,
    "/withdraw": 0.9,
    "/send": 0.8,
    "/invite": 0.7,
    "/admin/": 0.8,
    "/api/user": 0.8,
    "/api/account": 0.85,
    "/api/profile": 0.8,
    "/api/settings": 0.85,
}

# Claves que indican operaciones sensibles
CSRF_KEYS: dict[str, float] = {
    "password": 0.95,
    "new_password": 0.95,
    "current_password": 0.9,
    "email": 0.95,
    "phone": 0.85,
    "address": 0.8,
    "currency": 0.7,
    "timezone": 0.6,
    "language": 0.5,
    "theme": 0.4,
    "notification": 0.5,
    "2fa": 0.9,
    "mfa": 0.9,
    "totp": 0.85,
}

# Métodos que mutan estado
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Patrones de token CSRF comunes en body/headers
CSRF_TOKEN_PATTERNS = (
    "csrf",
    "xsrf",
    "_token",
    "authenticity_token",
    "form_token",
    "nonce",
    "anti_forgery",
)


class CSRFReasoner(BaseReasoner):
    """Analiza endpoints para falta de protección CSRF."""

    @property
    def vulnerability_type(self) -> str:
        return "csrf"

    def supported_methods(self) -> list[str]:
        return ["POST", "PUT", "PATCH", "DELETE"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        if endpoint.method.upper() not in MUTATING_METHODS:
            return []

        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        path_lower = (endpoint.path or "").lower()
        for frag, score in CSRF_PATHS.items():
            if frag in path_lower:
                signals.append(f"CSRF-sensitive path: {frag}")
                confidence += score * 0.4

        blob_keys = [str(k) for k in (endpoint.body or {})]
        lowered = {k.lower(): k for k in blob_keys}

        # Verificar si ya hay token CSRF en el body
        has_csrf_token = any(any(pat in k.lower() for pat in CSRF_TOKEN_PATTERNS) for k in blob_keys)
        if has_csrf_token:
            signals.append("CSRF token present in request body")
            confidence *= 0.3  # baja confianza pero no descarta (token puede ser weak)
        else:
            signals.append("No CSRF token detected in request body")
            confidence += 0.35

        # Claves sensibles aumentan el riesgo
        for low, orig in lowered.items():
            if low in CSRF_KEYS:
                signals.append(f"Sensitive field: {orig}")
                params_of_interest.append(orig)
                confidence += CSRF_KEYS[low] * 0.25

        # Headers que podrían mitigar (se verifica en probe real)
        # Aquí solo estático: ausencia de token + método mutante + datos sensibles = señal

        if confidence < 0.2 or not signals:
            return []

        confidence = min(confidence, 1.0)
        severity = "high" if confidence >= 0.6 else ("medium" if confidence >= 0.35 else "low")

        return [
            Hypothesis(
                vulnerability_type="csrf",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential CSRF on {endpoint.method} {endpoint.path} — no token detected",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} performs a state-changing operation "
                    f"({', '.join(params_of_interest[:4])}) without a detectable CSRF token in the request. "
                    f"Missing CSRF protection allows attackers to forge requests from victim's browser."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} changes sensitive state (password, email, payment) "
                    f"and pays $500-10k+. Often trivial to exploit with auto-submit form."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Confirm scope covers CSRF testing before proceeding.",
                    "Check if the endpoint uses SameSite cookies (Lax/Strict = mitigated).",
                    "Look for CSRF token in: body params, custom header (X-CSRF-Token), or cookie double-submit.",
                    "Build a minimal HTML form that auto-submits the target request from a different origin.",
                    "Test with a victim session (different browser/profile). Observe if state changes.",
                    "If SameSite=Lax: test with top-level navigation (link click) not iframe.",
                    "Do NOT test password reset / account takeover flows on live accounts.",
                    "Stop at first proof of forged request acceptance. Test ONLY authorized targets or your own lab.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in CSRF_ALTERNATIVES.get("csrf", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope and CSRF testing is allowed. "
                    f"Auto-submit forms are low-impact. Test ONLY authorized targets or your own lab."
                ),
                reproducibility_notes=("Same forged form, same victim session. State change twice = reproducible."),
            )
        ]
