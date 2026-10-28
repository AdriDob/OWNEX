"""OAuth/SSO Reasoner — flujos de autorización con impacto ATO.

Detecta superficie OAuth 2.0 / OpenID Connect: redirect_uri controlable,
códigos o tokens en URL (fuga por historial/referer), flujo implícito,
state ausente y PKCE ausente/degradado. Un bypass acá es Account Takeover,
que paga $3-15k en programas públicos.

Seguridad por construcción: análisis estático de parámetros, sin enviar
credenciales reales ni completar logins ajenos. Solo objetivos autorizados.
"""

from __future__ import annotations

import logging

from cores.offensive.models import EndpointInfo, Hypothesis
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.templates import OAUTH_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.oauth")

# Fragmentos de path de flujos OAuth/SSO
OAUTH_PATHS: dict[str, float] = {
    "/oauth": 0.9,
    "/authorize": 0.9,
    "/callback": 0.85,
    "/login": 0.5,
    "/sso": 0.85,
    "/connect": 0.6,
    "/token": 0.55,
    "/userinfo": 0.7,
    "/.well-known": 0.6,
}

# Parámetros del protocolo y sus riesgos
OAUTH_PARAMS: dict[str, float] = {
    "redirect_uri": 0.95,
    "redirect_url": 0.9,
    "callback": 0.8,
    "code": 0.85,
    "access_token": 0.95,
    "id_token": 0.9,
    "refresh_token": 0.9,
    "response_type": 0.75,
    "client_id": 0.6,
    "scope": 0.6,
    "state": 0.7,
    "code_challenge": 0.7,
    "code_verifier": 0.75,
    "nonce": 0.65,
}

TOKEN_IN_URL = ("code", "access_token", "id_token", "refresh_token")


class OAuthReasoner(BaseReasoner):
    """Analiza flujos OAuth/SSO: redirect abierto, fuga de tokens, PKCE, state."""

    @property
    def vulnerability_type(self) -> str:
        return "oauth"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        if endpoint.method.upper() not in ("GET", "POST"):
            return []
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        path_lower = (endpoint.path or "").lower()
        for frag, score in OAUTH_PATHS.items():
            if frag in path_lower:
                signals.append(f"OAuth/SSO flow path: {frag}")
                confidence += score * 0.4

        names = list(endpoint.query_params) + list(endpoint.path_params)
        if endpoint.body:
            names.extend(str(k) for k in endpoint.body)
        lowered = {n.lower(): n for n in names}
        for low, orig in lowered.items():
            if low in OAUTH_PARAMS:
                signals.append(f"OAuth protocol parameter: {orig}")
                if orig not in params_of_interest:
                    params_of_interest.append(orig)
                confidence += OAUTH_PARAMS[low] * 0.3

        leak = [lowered[name] for name in TOKEN_IN_URL if name in lowered]
        has_state = "state" in lowered
        has_pkce = "code_challenge" in lowered or "code_verifier" in lowered
        if leak:
            signals.append(f"Token/code transported in URL: {', '.join(leak)} (history/referer leak)")
            confidence += 0.25
        if ("redirect_uri" in lowered or "redirect_url" in lowered) and not has_state:
            signals.append("Redirect parameter without state: CSRF/login-forgery surface")
            confidence += 0.2
        if "code" in lowered and not has_pkce:
            signals.append("Authorization code without PKCE: interception surface")
            confidence += 0.15

        if confidence < 0.1 or not params_of_interest:
            return []

        confidence = min(confidence, 1.0)
        severity = (
            "high"
            if (leak or ("redirect_uri" in lowered and not has_state))
            else ("medium" if confidence >= 0.4 else "low")
        )

        return [
            Hypothesis(
                vulnerability_type="oauth",
                endpoint=endpoint.path,
                method=endpoint.method,
                confidence=confidence,
                severity=severity,
                summary=f"Potential OAuth/SSO flaw via {', '.join(params_of_interest[:3])} "
                f"on {endpoint.method} {endpoint.path}",
                description=(
                    f"The endpoint {endpoint.method} {endpoint.path} runs an OAuth/SSO "
                    f"flow with caller-visible parameters ({', '.join(params_of_interest[:4])}). "
                    f"Open redirects, token-in-URL leaks, missing state or degraded PKCE "
                    f"lead to Account Takeover — a High/Critical class in public programs."
                ),
                why_human_would_investigate=(
                    f"A human triager would investigate because {endpoint.method} "
                    f"{endpoint.path} moves authorization data through "
                    f"{params_of_interest[0] if params_of_interest else 'protocol params'} "
                    f"({len(signals)} OAuth indicators). ATO findings duplicate little "
                    f"and pay $3-15k."
                ),
                parameters_of_interest=params_of_interest,
                signals=signals,
                test_instructions=[
                    "Confirm the OAuth flow is in scope; use only your own test accounts.",
                    "Tamper redirect_uri with an attacker domain and observe where the "
                    "code/token lands (do not harvest other users' codes).",
                    "Drop the state parameter and replay the flow to test login CSRF.",
                    "Remove code_challenge (or downgrade to plain) to test PKCE enforcement.",
                    "Check response/history: if a code or token is replayable by another "
                    "session — save both transcripts as PoC.",
                ],
                alternative_explanations=[
                    {"label": a["label"], "description": a["description"], "how_to_rule_out": a["how_to_rule_out"]}
                    for a in OAUTH_ALTERNATIVES.get("oauth", [])
                ],
                scope_check=(
                    f"Verify {endpoint.path} is in scope and OAuth testing is allowed. "
                    f"Never use real victim accounts or harvest live tokens. Test ONLY "
                    f"authorized targets or your own lab."
                ),
                reproducibility_notes=(
                    "Fixed tampered redirect_uri, fresh sessions per run. Same code "
                    "landing on attacker domain twice = reproducible."
                ),
            )
        ]
